import argparse
import csv
import json
import os
import statistics
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent
os.environ.setdefault("SMARTOFFICE_DISABLE_LLM", "1")
os.environ.setdefault("HF_HOME", str(PROJECT_ROOT / ".cache" / "huggingface"))

from smart_office_rag.config import DEFAULT_CONFIG
from smart_office_rag.documents import PolicyDocumentLoader
from smart_office_rag.generator import AnswerGenerator
from smart_office_rag.indexing import VectorIndex
from smart_office_rag.pipeline import EnterpriseKnowledgeRAG
from smart_office_rag.retrieval import BM25TextRetriever, HybridRetriever, KeywordRetriever
from smart_office_rag.types import Document

CONFIG_DIR = PROJECT_ROOT / "experiments" / "configs"
OUTPUT_DIR = PROJECT_ROOT / "experiments" / "results"
DOC_REPORT_PATH = PROJECT_ROOT / "docs" / "EXPERIMENT_REPORT.md"
JSON_REPORT_PATH = OUTPUT_DIR / "experiment_report.json"
CSV_REPORT_PATH = OUTPUT_DIR / "experiment_report.csv"
EVAL_DIR = PROJECT_ROOT / "data" / "eval"
EVAL_PATH = EVAL_DIR / "eval_cases.jsonl"
TOP_K = 5
REFUSAL_MARKERS = ("没有检索到明确依据", "没有明确依据", "无法回答", "建议联系", "未检索到")


@dataclass
class ExperimentConfig:
    id: str
    name: str
    stage: str
    description: str
    chunk_strategy: str
    retriever: str
    embedding_model: str
    vector_backend: str
    query_rewrite: bool
    metadata_filter: bool
    refusal_gate: bool
    next_step: str
    final_candidate: bool = False
    fixed_chunk_size: int = 900
    fixed_chunk_overlap: int = 120
    semantic_embedding_model: str = "BAAI/bge-small-zh-v1.5"
    semantic_similarity_threshold: float = 0.72
    semantic_max_chunk_size: int = 1200
    sentence_window_size: int = 0
    sentence_max_chars: int = 180
    sentence_min_chars: int = 12
    structured_boost: bool = False
    embedding_trust_remote_code: bool = False
    query_instruction: str = ""
    document_instruction: str = ""
    normalize_embeddings: bool = True
    max_seq_length: Optional[int] = None
    require_real_embedding: bool = False
    dataset_layers: Any = "all"
    eval_dataset_layers: Any = "all"
    selection_profile: str = "standard"
    query_construction: bool = False
    query_construction_mode: str = "rules"
    require_llm_query_construction: bool = False

    @classmethod
    def from_path(cls, path: Path) -> "ExperimentConfig":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(**data)


class ExperimentSkipped(Exception):
    pass


class ExperimentFailed(Exception):
    pass


def normalize_layers(value: Any) -> set[str]:
    if not value or value == "all":
        return {"all"}
    if isinstance(value, str):
        return {value.lower()}
    return {str(item).lower() for item in value}


def case_layer(case: Dict[str, Any]) -> str:
    return str(case.get("dataset_layer") or case.get("difficulty_level") or "baseline").lower()


def load_cases(dataset_layers: Any = "all") -> List[Dict[str, Any]]:
    allowed_layers = normalize_layers(dataset_layers)
    cases = []
    for path in sorted(EVAL_DIR.glob("*.jsonl")):
        with path.open("r", encoding="utf-8-sig") as handle:
            for line in handle:
                if line.strip():
                    case = json.loads(line)
                    case.setdefault("eval_file", path.name)
                    case.setdefault("dataset_layer", "hard" if path.name == "hard_eval_cases.jsonl" else "baseline")
                    if "all" in allowed_layers or case_layer(case) in allowed_layers:
                        cases.append(case)
    return cases


def hit_at_k(retrieved_doc_ids: List[str], expected_doc_ids: List[str], k: int) -> float:
    if not expected_doc_ids:
        return 0.0
    return float(bool(set(retrieved_doc_ids[:k]) & set(expected_doc_ids)))


def recall_at_k(retrieved_doc_ids: List[str], expected_doc_ids: List[str], k: int) -> float:
    if not expected_doc_ids:
        return 0.0
    return len(set(retrieved_doc_ids[:k]) & set(expected_doc_ids)) / len(set(expected_doc_ids))


def precision_at_k(retrieved_doc_ids: List[str], expected_doc_ids: List[str], k: int) -> float:
    if not expected_doc_ids:
        return 0.0
    window = retrieved_doc_ids[:k]
    if not window:
        return 0.0
    return sum(1 for doc_id in window if doc_id in expected_doc_ids) / len(window)


def mrr_at_k(retrieved_doc_ids: List[str], expected_doc_ids: List[str], k: int) -> float:
    expected = set(expected_doc_ids)
    for index, doc_id in enumerate(retrieved_doc_ids[:k], 1):
        if doc_id in expected:
            return 1.0 / index
    return 0.0


def ndcg_at_k(retrieved_doc_ids: List[str], expected_doc_ids: List[str], k: int) -> float:
    import math

    expected = set(expected_doc_ids)
    seen_relevant = set()
    gains = []
    for doc_id in retrieved_doc_ids[:k]:
        if doc_id in expected and doc_id not in seen_relevant:
            gains.append(1.0)
            seen_relevant.add(doc_id)
        else:
            gains.append(0.0)
    dcg = sum(gain / math.log2(index + 2) for index, gain in enumerate(gains))
    ideal_len = min(len(expected), k)
    if ideal_len == 0:
        return 0.0
    ideal_dcg = sum(1.0 / math.log2(index + 2) for index in range(ideal_len))
    return dcg / ideal_dcg


def citation_accuracy(source_doc_ids: Iterable[str], expected_doc_ids: List[str], should_refuse: bool) -> float:
    source_doc_ids = [doc_id for doc_id in source_doc_ids if doc_id]
    if should_refuse:
        return 1.0 if not source_doc_ids else 0.0
    if not expected_doc_ids or not source_doc_ids:
        return 0.0
    return sum(1 for doc_id in source_doc_ids if doc_id in expected_doc_ids) / len(source_doc_ids)


def contains_refusal(answer: str) -> bool:
    return any(marker in answer for marker in REFUSAL_MARKERS)


def text_overlap_score(answer: str, reference_answer: str) -> float:
    answer_terms = set(KeywordRetriever.tokens(answer))
    reference_terms = set(KeywordRetriever.tokens(reference_answer))
    if not reference_terms:
        return 0.0
    return len(answer_terms & reference_terms) / len(reference_terms)


def conflict_resolution_accuracy(retrieved_doc_ids: List[str], case: Dict[str, Any]) -> float:
    conflict_doc_ids = set(case.get("conflict_doc_ids") or [])
    priority_doc_ids = set(case.get("expected_policy_priority") or case.get("expected_doc_ids") or [])
    if not conflict_doc_ids and "版本" not in str(case.get("question_type", "")) and "冲突" not in str(case.get("required_reasoning", "")):
        return 0.0
    retrieved = retrieved_doc_ids[:TOP_K]
    if not retrieved:
        return 0.0
    first_relevant_rank = None
    first_conflict_rank = None
    for index, doc_id in enumerate(retrieved, 1):
        if first_relevant_rank is None and doc_id in priority_doc_ids:
            first_relevant_rank = index
        if first_conflict_rank is None and doc_id in conflict_doc_ids and doc_id not in priority_doc_ids:
            first_conflict_rank = index
    if first_relevant_rank is None:
        return 0.0
    if first_conflict_rank is None:
        return 1.0
    return float(first_relevant_rank < first_conflict_rank)


def multi_hop_coverage(retrieved_doc_ids: List[str], case: Dict[str, Any]) -> float:
    expected = set(case.get("expected_doc_ids") or [])
    if len(expected) < 2 and "跨文档" not in str(case.get("question_type", "")) and "multi_hop" not in str(case.get("required_reasoning", "")):
        return 0.0
    if not expected:
        return 0.0
    return len(set(retrieved_doc_ids[:TOP_K]) & expected) / len(expected)


def table_evidence_accuracy(retrieved_doc_ids: List[str], case: Dict[str, Any]) -> float:
    is_table_case = (
        "表格" in str(case.get("question_type", ""))
        or "金额" in str(case.get("question_type", ""))
        or "table" in str(case.get("required_reasoning", ""))
    )
    if not is_table_case:
        return 0.0
    return hit_at_k(retrieved_doc_ids, case.get("expected_doc_ids") or [], TOP_K)


def priority_compliance(retrieved_doc_ids: List[str], case: Dict[str, Any]) -> float:
    priority_doc_ids = set(case.get("expected_policy_priority") or [])
    if not priority_doc_ids:
        return 0.0
    for doc_id in retrieved_doc_ids[:TOP_K]:
        if doc_id in priority_doc_ids:
            return 1.0
        if doc_id in set(case.get("conflict_doc_ids") or []):
            return 0.0
    return 0.0


def percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((pct / 100) * (len(ordered) - 1)))
    return ordered[index]


def average(values: List[float]) -> float:
    return statistics.mean(values) if values else 0.0


def build_sources(chunks: List[Document]) -> List[Dict[str, str]]:
    return EnterpriseKnowledgeRAG._build_sources(chunks)


def summarize_cases(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    retrieval_cases = [case for case in cases if not case["should_refuse"]]
    refusal_cases = [case for case in cases if case["should_refuse"]]
    latencies = [case["metrics"]["latency_ms"] for case in cases]
    conflict_cases = [case for case in cases if case["metrics"].get("conflict_resolution_accuracy_applicable")]
    multi_hop_cases = [case for case in cases if case["metrics"].get("multi_hop_coverage_applicable")]
    table_cases = [case for case in cases if case["metrics"].get("table_evidence_accuracy_applicable")]
    priority_cases = [case for case in cases if case["metrics"].get("priority_compliance_applicable")]
    return {
        "total": len(cases),
        "retrieval_cases": len(retrieval_cases),
        "refusal_cases": len(refusal_cases),
        "answer_accuracy_proxy": average([case["metrics"]["answer_correctness_proxy"] for case in retrieval_cases]),
        "hit_at_5": average([case["metrics"]["hit_at_5"] for case in retrieval_cases]),
        "mrr_at_5": average([case["metrics"]["mrr_at_5"] for case in retrieval_cases]),
        "citation_accuracy": average([case["metrics"]["citation_accuracy"] for case in cases]),
        "refusal_accuracy": average([case["metrics"]["refusal_accuracy"] for case in refusal_cases]),
        "faithfulness_proxy": average([case["metrics"]["faithfulness_proxy"] for case in cases]),
        "latency_p50_ms": percentile(latencies, 50),
        "latency_p95_ms": percentile(latencies, 95),
        "latency_avg_ms": average(latencies),
        "conflict_resolution_accuracy": average([case["metrics"]["conflict_resolution_accuracy"] for case in conflict_cases]),
        "multi_hop_coverage": average([case["metrics"]["multi_hop_coverage"] for case in multi_hop_cases]),
        "table_evidence_accuracy": average([case["metrics"]["table_evidence_accuracy"] for case in table_cases]),
        "priority_compliance": average([case["metrics"]["priority_compliance"] for case in priority_cases]),
        "conflict_cases": len(conflict_cases),
        "multi_hop_cases": len(multi_hop_cases),
        "table_cases": len(table_cases),
        "priority_cases": len(priority_cases),
    }


def query_rewrite(question: str) -> str:
    hints = []
    synonym_hints = {
        "邮箱": "IT 系统权限 VPN IT 服务",
        "VPN": "IT 服务 权限申请",
        "生产系统": "生产系统 变更申请 权限申请 高风险",
        "客户数据": "数据安全 客户信息 数据合规 信息安全",
        "报销": "差旅 费用 报销 财务",
        "付款": "供应商付款 对账 三单校验 财务",
        "合同": "合同评审 法务 归档",
        "盖章": "印章 公章 合同章",
        "供应商": "供应商准入 采购 复评",
        "审计": "内审 整改 监管报送",
        "材料不齐": "申请被退回 补充材料 重新提交",
        "线下先办": "不得绕过系统审批 例外流程",
    }
    for term, hint in synonym_hints.items():
        if term in question:
            hints.append(hint)
    if not hints:
        return question
    return question + " " + " ".join(hints)


def construct_query(question: str) -> Dict[str, Any]:
    rewritten_terms = []
    boost_terms = []
    soft_filters: Dict[str, str] = {}
    intents = []

    rules = [
        {
            "terms": ("2025", "2026", "版本", "新版", "旧版", "补充通知", "优先", "冲突", "现在", "当前"),
            "intent": "version_conflict",
            "boost": ("版本", "生效日期", "effective_from", "supersedes", "priority", "补充通知", "新版", "旧版"),
        },
        {
            "terms": ("报销", "发票", "票据", "付款", "经费", "预算"),
            "intent": "finance_policy",
            "department": "Finance",
            "boost": ("财务", "报销", "票据", "付款", "预算", "经费", "补充通知"),
        },
        {
            "terms": ("出差", "差旅", "住宿", "交通", "城市"),
            "intent": "travel_policy",
            "department": "Admin",
            "boost": ("差旅", "住宿", "城市等级", "报销标准", "2026"),
        },
        {
            "terms": ("采购", "供应商", "合同", "比价", "招标", "验收"),
            "intent": "procurement_policy",
            "department": "Procurement",
            "boost": ("采购", "合同", "供应商", "比价", "验收", "交叉审批"),
        },
        {
            "terms": ("客户数据", "导出", "外发", "数据", "安全", "权限"),
            "intent": "security_policy",
            "department": "Security",
            "boost": ("客户数据", "导出", "外发", "安全", "审批", "留痕", "风险评估"),
        },
        {
            "terms": ("远程", "VPN", "电脑", "连不上", "账号", "在家办公"),
            "intent": "remote_it_policy",
            "department": "IT",
            "boost": ("远程办公", "VPN", "账号权限", "安全例外", "IT"),
        },
        {
            "terms": ("超过", "金额", "额度", "阈值", "30000", "三万", "表格", "标准"),
            "intent": "threshold_table",
            "boost": ("金额", "阈值", "审批权限", "附表", "超过", "标准事项"),
            "section_type": "appendix",
        },
        {
            "terms": ("同时", "还要", "涉及", "一起", "哪个先", "哪些制度"),
            "intent": "multi_hop",
            "boost": ("关联制度", "related_doc_ids", "跨部门", "会签", "主责部门"),
        },
        {
            "terms": ("紧急", "先", "后补", "补审批", "例外"),
            "intent": "exception",
            "boost": ("紧急事项", "例外事项", "三个工作日", "补齐", "复盘", "留痕"),
        },
    ]

    for rule in rules:
        if any(term in question for term in rule["terms"]):
            intents.append(rule["intent"])
            rewritten_terms.extend(rule.get("boost", ()))
            boost_terms.extend(rule.get("boost", ()))
            if "department" in rule and "department" not in soft_filters:
                soft_filters["department"] = rule["department"]
            if "section_type" in rule:
                soft_filters["section_type"] = rule["section_type"]

    if "version_conflict" in intents:
        soft_filters["version_sensitive"] = "true"
    if "multi_hop" in intents:
        soft_filters["multi_hop"] = "true"

    deduped_terms = list(dict.fromkeys(term for term in rewritten_terms if term))
    rewritten_query = question if not deduped_terms else question + " " + " ".join(deduped_terms)
    return {
        "original_query": question,
        "rewritten_query": rewritten_query,
        "intent": "+".join(dict.fromkeys(intents)) or "general",
        "soft_filters": soft_filters,
        "boost_terms": list(dict.fromkeys(boost_terms)),
        "construction_mode": "rules",
    }


def llm_construct_query(question: str) -> Dict[str, Any]:
    api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ExperimentSkipped("LLM query construction requires DEEPSEEK_API_KEY or OPENAI_API_KEY.")

    from openai import OpenAI

    base_url = DEFAULT_CONFIG.llm_base_url if os.getenv("DEEPSEEK_API_KEY") else os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    client = OpenAI(api_key=api_key, base_url=base_url)
    prompt = f"""你是企业制度 RAG 的查询构建器。请把员工口语化问题转换成检索用 JSON。

要求：
- 只输出 JSON，不要解释。
- 不要编造制度名。
- rewritten_query 应保留用户原意，并补充检索关键词。
- intent 只能从 general/version_conflict/priority/multi_hop/threshold_table/exception/security_policy/procurement_policy/travel_policy/finance_policy/remote_it_policy/refusal_candidate 中选择。
- soft_filters 只放弱提示，不做强过滤。可包含 department、section_type、version_sensitive、multi_hop。
- boost_terms 是检索增强词列表。

用户问题：{question}

JSON schema:
{{
  "rewritten_query": "...",
  "intent": "...",
  "soft_filters": {{}},
  "boost_terms": ["..."]
}}
"""
    try:
        response = client.chat.completions.create(
            model=DEFAULT_CONFIG.llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=500,
        )
    except Exception as exc:
        raise ExperimentSkipped(f"LLM query construction call failed: {exc}") from exc
    content = response.choices[0].message.content or ""
    content = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ExperimentSkipped(f"LLM query construction returned invalid JSON: {content[:120]}") from exc

    rewritten_query = str(payload.get("rewritten_query") or question).strip()
    boost_terms = [str(term) for term in payload.get("boost_terms", []) if str(term).strip()]
    if not rewritten_query:
        rewritten_query = question
    if boost_terms and " ".join(boost_terms) not in rewritten_query:
        rewritten_query = rewritten_query + " " + " ".join(boost_terms)
    return {
        "original_query": question,
        "rewritten_query": rewritten_query,
        "intent": str(payload.get("intent") or "general"),
        "soft_filters": payload.get("soft_filters") if isinstance(payload.get("soft_filters"), dict) else {},
        "boost_terms": boost_terms,
        "construction_mode": "llm",
    }


def infer_filters(question: str, chunks: List[Document]) -> Dict[str, str]:
    departments = {
        "HR": ("请假", "绩效", "培训", "入职", "离职", "转岗"),
        "Finance": ("报销", "发票", "付款", "预算", "备用金", "借款"),
        "IT": ("邮箱", "VPN", "生产系统", "电脑", "故障", "权限"),
        "Security": ("客户数据", "钓鱼", "日志", "账号复核", "信息分级"),
        "Legal": ("合同", "NDA", "保密"),
        "Procurement": ("供应商", "采购", "招标"),
        "Audit": ("内审", "审计", "监管"),
        "Admin": ("会议室", "访客", "盖章", "印章", "出差"),
    }
    filters: Dict[str, str] = {}
    for department, terms in departments.items():
        if any(term in question for term in terms):
            filters["department"] = department
            break
    return filters


class ExperimentRunner:
    def __init__(self, config: ExperimentConfig):
        self.config = config
        self.generator = AnswerGenerator(
            model_name=DEFAULT_CONFIG.llm_model,
            base_url=DEFAULT_CONFIG.llm_base_url,
            temperature=DEFAULT_CONFIG.temperature,
            max_tokens=DEFAULT_CONFIG.max_tokens,
        )
        self.parents: List[Document] = []
        self.chunks: List[Document] = []
        self.retriever = None
        self.index_build_ms = 0.0
        self.vector_backend_used = config.vector_backend
        self.model_load_ms = 0.0
        self.embedding_dimension = 0
        self.embedding_load_mode = "none"
        self.embedding_used_fallback = False

    def initialize(self) -> None:
        if self.config.retriever == "llm_direct":
            return
        if self.config.query_construction and self.config.query_construction_mode == "llm":
            api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
            if self.config.require_llm_query_construction and not api_key:
                raise ExperimentSkipped("LLM query construction requires DEEPSEEK_API_KEY or OPENAI_API_KEY.")
        loader = PolicyDocumentLoader(
            DEFAULT_CONFIG.data_path,
            pdf_path=DEFAULT_CONFIG.pdf_data_path,
            pdf_mode=DEFAULT_CONFIG.pdf_loader_mode,
            chunk_strategy=self.config.chunk_strategy,
            fixed_chunk_size=self.config.fixed_chunk_size,
            fixed_chunk_overlap=self.config.fixed_chunk_overlap,
            semantic_embedding_model=self.config.semantic_embedding_model,
            semantic_similarity_threshold=self.config.semantic_similarity_threshold,
            semantic_max_chunk_size=self.config.semantic_max_chunk_size,
            sentence_window_size=self.config.sentence_window_size,
            sentence_max_chars=self.config.sentence_max_chars,
            sentence_min_chars=self.config.sentence_min_chars,
            dataset_layers=self.config.dataset_layers,
        )
        self.parents = loader.load_parent_documents()
        self.chunks = loader.split_documents(self.parents)

        started = time.perf_counter()
        if self.config.retriever == "keyword_only":
            self.retriever = KeywordRetriever(self.chunks, k=max(TOP_K * 4, 20))
        elif self.config.retriever == "bm25_only":
            self.retriever = BM25TextRetriever(self.chunks, k=max(TOP_K * 4, 20))
        elif self.config.retriever in {"vector_only", "hybrid_rrf", "structured_hybrid_rrf"}:
            index_path = OUTPUT_DIR / "index_cache" / self.config.name
            try:
                vector_index = VectorIndex(
                    self.config.embedding_model,
                    index_path,
                    trust_remote_code=self.config.embedding_trust_remote_code,
                    query_instruction=self.config.query_instruction,
                    document_instruction=self.config.document_instruction,
                    normalize_embeddings=self.config.normalize_embeddings,
                    max_seq_length=self.config.max_seq_length,
                    require_real_embedding=self.config.require_real_embedding,
                )
            except Exception as exc:
                raise ExperimentSkipped(f"Embedding model unavailable: {self.config.embedding_model}; {exc}") from exc
            try:
                vectorstore = vector_index.build(self.chunks)
            except Exception as exc:
                raise ExperimentSkipped(f"Embedding build failed: {self.config.embedding_model}; {exc}") from exc
            self.model_load_ms = vectorstore.embeddings.model_load_ms
            self.embedding_dimension = vectorstore.embeddings.embedding_dimension
            self.embedding_load_mode = vectorstore.embeddings.load_mode
            self.embedding_used_fallback = vectorstore.embeddings.used_fallback
            if self.config.embedding_model != "local-hashing" and vectorstore.embeddings.used_fallback:
                raise ExperimentSkipped(f"Embedding model unavailable: {self.config.embedding_model}")
            if self.config.vector_backend == "numpy":
                vectorstore.index = None
                self.vector_backend_used = "numpy"
            elif self.config.vector_backend == "faiss" and vectorstore.index is None:
                raise ExperimentSkipped("FAISS backend requested but faiss-cpu is unavailable.")

            self.retriever = (
                vectorstore.as_retriever(search_kwargs={"k": max(TOP_K * 4, 20)})
                if self.config.retriever == "vector_only"
                else HybridRetriever(
                    vectorstore,
                    self.chunks,
                    default_k=TOP_K,
                    sentence_window_size=self.config.sentence_window_size if self.config.chunk_strategy == "sentence_window" else 0,
                    structured_boost=self.config.structured_boost or self.config.retriever == "structured_hybrid_rrf",
                )
            )
        else:
            raise ValueError(f"Unsupported retriever: {self.config.retriever}")
        self.index_build_ms = (time.perf_counter() - started) * 1000

    def retrieve(self, question: str) -> List[Document]:
        if self.retriever is None:
            return []
        constructed = None
        if self.config.query_construction:
            if self.config.query_construction_mode == "llm":
                try:
                    constructed = llm_construct_query(question)
                except ExperimentSkipped:
                    if self.config.require_llm_query_construction:
                        raise
                    constructed = construct_query(question)
            else:
                constructed = construct_query(question)
        rewritten = constructed["rewritten_query"] if constructed else query_rewrite(question) if self.config.query_rewrite else question
        filters = infer_filters(question, self.chunks) if self.config.metadata_filter else None
        if isinstance(self.retriever, HybridRetriever):
            return self.retriever.search(rewritten, top_k=TOP_K, filters=filters)
        docs = self.retriever.invoke(rewritten)
        if filters:
            docs = [doc for doc in docs if all(str(doc.metadata.get(key)) == value for key, value in filters.items())]
        return docs[:TOP_K]

    def answer(self, question: str) -> Dict[str, Any]:
        started = time.perf_counter()
        if self.config.retriever == "llm_direct":
            answer = "结论：\n无检索增强直答基线，不读取知识库，无法提供可验证引用。\n\n引用来源：\n- 无。"
            return {"answer": answer, "chunks": [], "sources": [], "latency_ms": (time.perf_counter() - started) * 1000, "refused": False}

        if self.config.refusal_gate and EnterpriseKnowledgeRAG._is_out_of_scope(question):
            answer = self.generator.generate_no_evidence(question, [], reason="out_of_scope")
            return {"answer": answer, "chunks": [], "sources": [], "latency_ms": (time.perf_counter() - started) * 1000, "refused": True}

        docs = self.retrieve(question)
        if self.config.refusal_gate and EnterpriseKnowledgeRAG._is_low_confidence(question, docs):
            answer = self.generator.generate_no_evidence(question, docs[:3], reason="low_confidence")
            return {
                "answer": answer,
                "chunks": docs,
                "sources": build_sources(docs[:3]),
                "latency_ms": (time.perf_counter() - started) * 1000,
                "refused": True,
            }

        answer = self.generator.generate(question, docs)
        return {
            "answer": answer,
            "chunks": docs,
            "sources": build_sources(docs),
            "latency_ms": (time.perf_counter() - started) * 1000,
            "refused": False,
        }


def evaluate_experiment(config: ExperimentConfig, cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    runner = ExperimentRunner(config)
    try:
        runner.initialize()
    except ExperimentSkipped as exc:
        return {
            "config": config.__dict__,
            "status": "skipped",
            "skip_reason": str(exc),
            "summary": {},
            "failure_cases": [],
            "cases": [],
        }

    evaluated = []
    for case in cases:
        try:
            response = runner.answer(case["question"])
        except ExperimentSkipped as exc:
            return {
                "config": config.__dict__,
                "status": "skipped",
                "skip_reason": str(exc),
                "summary": {},
                "failure_cases": [],
                "cases": [],
            }
        retrieved_doc_ids = [str(doc.metadata.get("doc_id")) for doc in response["chunks"]]
        source_doc_ids = [str(source.get("doc_id", "")) for source in response["sources"]]
        should_refuse = bool(case["should_refuse"])
        refused = bool(response["refused"]) or contains_refusal(response["answer"])
        expected_doc_ids = case["expected_doc_ids"]
        metrics = {
            "hit_at_5": hit_at_k(retrieved_doc_ids, expected_doc_ids, TOP_K),
            "recall_at_5": recall_at_k(retrieved_doc_ids, expected_doc_ids, TOP_K),
            "context_precision_at_5": precision_at_k(retrieved_doc_ids, expected_doc_ids, TOP_K),
            "mrr_at_5": mrr_at_k(retrieved_doc_ids, expected_doc_ids, TOP_K),
            "ndcg_at_5": ndcg_at_k(retrieved_doc_ids, expected_doc_ids, TOP_K),
            "citation_accuracy": citation_accuracy(source_doc_ids, expected_doc_ids, should_refuse),
            "refusal_accuracy": float(refused == should_refuse) if should_refuse else 0.0,
            "answer_correctness_proxy": text_overlap_score(response["answer"], case["reference_answer"]) if not should_refuse else 0.0,
            "faithfulness_proxy": 1.0 if (should_refuse and refused) else citation_accuracy(source_doc_ids, expected_doc_ids, should_refuse),
            "latency_ms": response["latency_ms"],
        }
        conflict_metric = conflict_resolution_accuracy(retrieved_doc_ids, case)
        multi_hop_metric = multi_hop_coverage(retrieved_doc_ids, case)
        table_metric = table_evidence_accuracy(retrieved_doc_ids, case)
        priority_metric = priority_compliance(retrieved_doc_ids, case)
        metrics.update(
            {
                "conflict_resolution_accuracy": conflict_metric,
                "conflict_resolution_accuracy_applicable": bool(case.get("conflict_doc_ids"))
                or "版本" in str(case.get("question_type", ""))
                or "冲突" in str(case.get("required_reasoning", "")),
                "multi_hop_coverage": multi_hop_metric,
                "multi_hop_coverage_applicable": len(case.get("expected_doc_ids") or []) >= 2
                or "跨文档" in str(case.get("question_type", ""))
                or "multi_hop" in str(case.get("required_reasoning", "")),
                "table_evidence_accuracy": table_metric,
                "table_evidence_accuracy_applicable": "表格" in str(case.get("question_type", ""))
                or "金额" in str(case.get("question_type", ""))
                or "table" in str(case.get("required_reasoning", "")),
                "priority_compliance": priority_metric,
                "priority_compliance_applicable": bool(case.get("expected_policy_priority")),
            }
        )
        evaluated.append(
            {
                **case,
                "retrieved_doc_ids": retrieved_doc_ids,
                "sources": response["sources"],
                "refused": refused,
                "metrics": metrics,
            }
        )

    summary = summarize_cases(evaluated)
    summary.update(
        {
            "id": config.id,
            "name": config.name,
            "status": "completed",
            "chunk_strategy": config.chunk_strategy,
            "retriever": config.retriever,
            "embedding_model": config.embedding_model,
            "vector_backend": runner.vector_backend_used,
            "query_rewrite": config.query_rewrite,
            "metadata_filter": config.metadata_filter,
            "refusal_gate": config.refusal_gate,
            "sentence_window_size": config.sentence_window_size,
            "structured_boost": config.structured_boost or config.retriever == "structured_hybrid_rrf",
            "dataset_layers": config.dataset_layers,
            "eval_dataset_layers": config.eval_dataset_layers,
            "selection_profile": config.selection_profile,
            "query_construction": config.query_construction,
            "query_construction_mode": config.query_construction_mode,
            "require_llm_query_construction": config.require_llm_query_construction,
            "index_build_ms": runner.index_build_ms,
            "model_load_ms": runner.model_load_ms,
            "embedding_dimension": runner.embedding_dimension,
            "embedding_load_mode": runner.embedding_load_mode,
            "embedding_used_fallback": runner.embedding_used_fallback,
            "embedding_trust_remote_code": config.embedding_trust_remote_code,
            "chunks": len(runner.chunks),
        }
    )
    failure_cases = [
        case
        for case in evaluated
        if (
            (not case["should_refuse"] and case["metrics"]["hit_at_5"] < 1.0)
            or (case["should_refuse"] and case["metrics"]["refusal_accuracy"] < 1.0)
            or case["metrics"]["citation_accuracy"] < 0.5
        )
    ]
    return {
        "config": config.__dict__,
        "status": "completed",
        "summary": summary,
        "failure_cases": failure_cases[:10],
        "cases": evaluated,
    }


def load_configs(mode: str, config_pattern: str = "*.json") -> List[ExperimentConfig]:
    paths = []
    for pattern in [item.strip() for item in config_pattern.split(",") if item.strip()]:
        paths.extend(CONFIG_DIR.glob(pattern))
    configs = [ExperimentConfig.from_path(path) for path in sorted(set(paths))]
    if mode == "quick":
        configs = [config for config in configs if config.stage == "quick"]
    return configs


def write_csv(results: List[Dict[str, Any]]) -> None:
    fields = [
        "id",
        "name",
        "status",
        "answer_accuracy_proxy",
        "hit_at_5",
        "mrr_at_5",
        "citation_accuracy",
        "refusal_accuracy",
        "faithfulness_proxy",
        "conflict_resolution_accuracy",
        "multi_hop_coverage",
        "table_evidence_accuracy",
        "priority_compliance",
        "latency_p50_ms",
        "latency_p95_ms",
        "index_build_ms",
        "model_load_ms",
        "embedding_dimension",
        "embedding_load_mode",
        "embedding_used_fallback",
        "embedding_trust_remote_code",
        "chunks",
        "chunk_strategy",
        "retriever",
        "embedding_model",
        "vector_backend",
        "query_rewrite",
        "metadata_filter",
        "refusal_gate",
        "sentence_window_size",
        "structured_boost",
        "dataset_layers",
        "eval_dataset_layers",
        "selection_profile",
        "query_construction",
        "query_construction_mode",
        "require_llm_query_construction",
    ]
    with CSV_REPORT_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for result in results:
            row = {field: "" for field in fields}
            if result["status"] == "skipped":
                config = result["config"]
                row.update(
                    {
                        "id": config["id"],
                        "name": config["name"],
                        "chunk_strategy": config["chunk_strategy"],
                        "retriever": config["retriever"],
                        "embedding_model": config["embedding_model"],
                        "vector_backend": config["vector_backend"],
                        "embedding_trust_remote_code": config.get("embedding_trust_remote_code", False),
                        "query_rewrite": config["query_rewrite"],
                        "metadata_filter": config["metadata_filter"],
                        "refusal_gate": config["refusal_gate"],
                        "sentence_window_size": config.get("sentence_window_size", 0),
                        "structured_boost": config.get("structured_boost", False) or config.get("retriever") == "structured_hybrid_rrf",
                        "dataset_layers": json.dumps(config.get("dataset_layers", "all"), ensure_ascii=False),
                        "eval_dataset_layers": json.dumps(config.get("eval_dataset_layers", "all"), ensure_ascii=False),
                        "selection_profile": config.get("selection_profile", "standard"),
                        "query_construction": config.get("query_construction", False),
                        "query_construction_mode": config.get("query_construction_mode", "rules"),
                        "require_llm_query_construction": config.get("require_llm_query_construction", False),
                    }
                )
            else:
                row.update(result.get("summary", {}))
                row["dataset_layers"] = json.dumps(row.get("dataset_layers", "all"), ensure_ascii=False)
                row["eval_dataset_layers"] = json.dumps(row.get("eval_dataset_layers", "all"), ensure_ascii=False)
            row["status"] = result["status"]
            writer.writerow({field: row.get(field, "") for field in fields})


def compact_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    compacted = []
    for result in results:
        compacted.append(
            {
                "config": result.get("config", {}),
                "status": result.get("status"),
                "skip_reason": result.get("skip_reason", ""),
                "summary": result.get("summary", {}),
                "failure_cases": result.get("failure_cases", []),
            }
        )
    return compacted


def metric_delta(first: Dict[str, Any], last: Dict[str, Any], key: str) -> str:
    if not first or not last:
        return "N/A"
    return f"{first.get(key, 0):.3f} -> {last.get(key, 0):.3f}"


def selection_score(summary: Dict[str, Any]) -> float:
    latency_penalty = min(summary.get("latency_p95_ms", 0.0) / 1000.0, 1.0)
    if summary.get("selection_profile") == "hard":
        return (
            summary.get("citation_accuracy", 0.0) * 0.25
            + summary.get("conflict_resolution_accuracy", 0.0) * 0.20
            + summary.get("multi_hop_coverage", 0.0) * 0.15
            + summary.get("answer_accuracy_proxy", 0.0) * 0.20
            + summary.get("refusal_accuracy", 0.0) * 0.15
            + (1.0 - latency_penalty) * 0.05
        )
    return (
        summary.get("answer_accuracy_proxy", 0.0) * 0.30
        + ((summary.get("hit_at_5", 0.0) + summary.get("mrr_at_5", 0.0)) / 2.0) * 0.20
        + summary.get("citation_accuracy", 0.0) * 0.30
        + summary.get("refusal_accuracy", 0.0) * 0.15
        + (1.0 - latency_penalty) * 0.05
    )


def case_quality_score(case: Dict[str, Any]) -> float:
    metrics = case.get("metrics", {})
    return (
        metrics.get("citation_accuracy", 0.0) * 0.25
        + metrics.get("conflict_resolution_accuracy", 0.0) * 0.20
        + metrics.get("multi_hop_coverage", 0.0) * 0.15
        + metrics.get("answer_correctness_proxy", 0.0) * 0.20
        + metrics.get("refusal_accuracy", 0.0) * 0.15
        + metrics.get("faithfulness_proxy", 0.0) * 0.05
    )


def select_final_result(results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    completed = [result for result in results if result["status"] == "completed"]
    final_candidates = [result for result in completed if result["config"].get("final_candidate")]
    candidate_pool = final_candidates or completed
    if not candidate_pool:
        return None
    quality_leader = max(candidate_pool, key=lambda result: selection_score(result["summary"]))
    leader_score = selection_score(quality_leader["summary"])
    near_ties = [
        result
        for result in candidate_pool
        if leader_score - selection_score(result["summary"]) <= 0.005
    ]
    return min(near_ties, key=lambda result: result["summary"].get("latency_p95_ms", float("inf")))


def build_markdown(results: List[Dict[str, Any]]) -> str:
    completed = [result for result in results if result["status"] == "completed"]
    first = completed[0]["summary"] if completed else {}
    selected_result = select_final_result(results)
    selected = selected_result["summary"] if selected_result else {}
    final_candidates = [result for result in completed if result["config"].get("final_candidate")]
    quality_leader = max(final_candidates, key=lambda result: selection_score(result["summary"]))["summary"] if final_candidates else selected
    has_full = any(result["config"].get("stage") == "full" for result in results)
    selected_label = "Selected full-candidate version" if has_full else "Selected quick-regression version"
    leader_label = "Quality leader in full candidate pool" if final_candidates else "Quality leader in completed candidate pool"
    story_prefix = "真实 embedding full 实验" if has_full else "当前 quick 回归"
    embedding_note = (
        "本次 full 实验已完成真实 embedding 配置；如有模型 skipped，应先修复模型缓存或网络后再引用结论。"
        if has_full
        else "quick runs validate the chain, while final embedding selection requires successful `--full` experiments."
    )
    lines = [
        "# SmartOfficeRAG Experiment Report",
        "",
        "## Iteration Summary",
        "",
        f"- {selected_label}: {selected.get('id', 'N/A')} `{selected.get('name', 'N/A')}`",
        f"- {leader_label}: {quality_leader.get('id', 'N/A')} `{quality_leader.get('name', 'N/A')}`",
        f"- Answer Accuracy Proxy: {metric_delta(first, selected, 'answer_accuracy_proxy')}",
        f"- Hit@5: {metric_delta(first, selected, 'hit_at_5')}",
        f"- Citation Accuracy: {metric_delta(first, selected, 'citation_accuracy')}",
        f"- Refusal Accuracy: {metric_delta(first, selected, 'refusal_accuracy')}",
        f"- Selection rule: compare completed configs with a weighted quality score; {embedding_note}",
        "",
        "## Experiment Matrix",
        "",
        "| Version | Strategy | Chunk | Embedding | Retriever | Answer Acc. | Hit@5 | Citation | Refusal | p95 ms | Notes |",
        "| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for result in results:
        config = result["config"]
        if result["status"] == "skipped":
            lines.append(
                f"| {config['id']} | {config['name']} | {config['chunk_strategy']} | {config['embedding_model']} | "
                f"{config['retriever']} | - | - | - | - | - | skipped: {result.get('skip_reason', '')} |"
            )
            continue
        summary = result["summary"]
        lines.append(
            f"| {summary['id']} | {summary['name']} | {summary['chunk_strategy']} | {summary['embedding_model']} | "
            f"{summary['retriever']} | {summary['answer_accuracy_proxy']:.3f} | {summary['hit_at_5']:.3f} | "
            f"{summary['citation_accuracy']:.3f} | {summary['refusal_accuracy']:.3f} | {summary['latency_p95_ms']:.1f} | "
            f"{config['description']} |"
        )

    layer_rows = []
    for result in completed:
        summary = result["summary"]
        config = result["config"]
        if str(summary.get("id", "")).startswith(("V6-", "V10-", "V11-", "V12-", "V13-", "V14-")) and str(config.get("name", "")).startswith("layer_"):
            layer_rows.append(
                f"| {summary['id']} | {json.dumps(summary.get('dataset_layers'), ensure_ascii=False)} | "
                f"{json.dumps(summary.get('eval_dataset_layers'), ensure_ascii=False)} | {summary['total']} | "
                f"{summary['answer_accuracy_proxy']:.3f} | {summary['citation_accuracy']:.3f} | "
                f"{summary.get('conflict_resolution_accuracy', 0):.3f} | {summary.get('multi_hop_coverage', 0):.3f} | "
                f"{summary.get('table_evidence_accuracy', 0):.3f} | {selection_score(summary):.3f} |"
            )
    if layer_rows:
        lines.extend(
            [
                "",
                "## Layered Difficulty Matrix",
                "",
                "| Version | Loaded Layers | Eval Layers | Cases | Answer | Citation | Conflict | Multi-hop | Table | Weighted Score |",
                "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
                *layer_rows,
                "",
                "Selection rule: standard cases use Answer 30%, Citation 30%, Hit/MRR 20%, Refusal 15%, Latency 5%; hard cases use Citation 25%, Conflict 20%, Multi-hop 15%, Answer 20%, Refusal 15%, Latency 5%.",
            ]
        )

    hard_baseline = next((result for result in completed if result["summary"].get("id") == "V6-hard-bge-small"), None)
    if hard_baseline:
        baseline_scores = {case["id"]: case_quality_score(case) for case in hard_baseline.get("cases", [])}
        win_rows = []
        for result in completed:
            summary = result["summary"]
            if summary.get("selection_profile") != "hard" or summary.get("id") == "V6-hard-bge-small":
                continue
            comparable = [case for case in result.get("cases", []) if case["id"] in baseline_scores]
            if not comparable:
                continue
            wins = sum(1 for case in comparable if case_quality_score(case) > baseline_scores[case["id"]] + 1e-9)
            ties = sum(1 for case in comparable if abs(case_quality_score(case) - baseline_scores[case["id"]]) <= 1e-9)
            win_rows.append(
                f"| {summary['id']} | {len(comparable)} | {wins / len(comparable):.3f} | {wins} | {ties} | {len(comparable) - wins - ties} |"
            )
        if win_rows:
            lines.extend(
                [
                    "",
                    "## Hard Case Win Rate",
                    "",
                    "| Version | Comparable Cases | Win Rate vs V6-hard | Wins | Ties | Losses |",
                    "| --- | ---: | ---: | ---: | ---: | ---: |",
                *win_rows,
                "",
                "A win means the case-level hard weighted score is higher than `V6-hard-bge-small` for the same question.",
            ]
        )

    query_rows = []
    query_targets = [
        "V6-hard-bge-small",
        "V11-hard-structured",
        "V13-hard-query-construction",
        "V14-hard-query-structured",
        "V15-hard-llm-query-construction",
        "V16-hard-llm-query-structured",
    ]
    by_summary_id = {result.get("summary", {}).get("id"): result for result in completed}
    for config_id in query_targets:
        result = by_summary_id.get(config_id)
        if not result:
            continue
        summary = result["summary"]
        query_rows.append(
            f"| {summary['id']} | {summary['retriever']} | {summary.get('query_construction', False)}"
            f"/{summary.get('query_construction_mode', 'rules')} | "
            f"{summary.get('structured_boost', False)} | {summary['answer_accuracy_proxy']:.3f} | "
            f"{summary['citation_accuracy']:.3f} | {summary.get('conflict_resolution_accuracy', 0):.3f} | "
            f"{summary.get('multi_hop_coverage', 0):.3f} | {summary.get('table_evidence_accuracy', 0):.3f} | "
            f"{summary['latency_p95_ms']:.1f} |"
        )
    if query_rows:
        lines.extend(
            [
                "",
                "## Query Construction Findings",
                "",
                "| Version | Retriever | Query Construction | Structured Boost | Answer | Citation | Conflict | Multi-hop | Table | p95 ms |",
                "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
                *query_rows,
                "",
                "Decision rule: query construction is useful only if it improves hard-case coverage without lowering citation, conflict handling, or latency beyond the business tolerance. It should remain an experiment unless it beats V6/V11 on hard weighted score.",
            ]
        )

    embedding_rows = []
    embedding_ids = [
        "V6-bge-small",
        "V9-qwen3-0.6b",
        "V9-bge-m3",
        "V9-gte-qwen2-1.5b",
        "V6-hard-bge-small",
        "V9-hard-qwen3-0.6b",
        "V9-hard-bge-m3",
    ]
    by_id = {result["config"]["id"]: result for result in results}
    for config_id in embedding_ids:
        result = by_id.get(config_id)
        if not result:
            continue
        config = result["config"]
        if result["status"] == "skipped":
            embedding_rows.append(
                f"| {config_id} | {config['embedding_model']} | skipped | - | - | - | - | - | {result.get('skip_reason', '')} |"
            )
            continue
        summary = result["summary"]
        embedding_rows.append(
            f"| {config_id} | {summary['embedding_model']} | completed | {summary.get('embedding_dimension', 0)} | "
            f"{summary.get('model_load_ms', 0):.1f} | {summary['answer_accuracy_proxy']:.3f} | "
            f"{summary['citation_accuracy']:.3f} | {summary['latency_p95_ms']:.1f} | "
            f"trust_remote_code={summary.get('embedding_trust_remote_code', False)}; load_mode={summary.get('embedding_load_mode', '')} |"
        )
    if embedding_rows:
        lines.extend(
            [
                "",
                "## Embedding Model Findings",
                "",
                "| Version | Model | Status | Dim | Load ms | Answer Acc. | Citation | p95 ms | Notes |",
                "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
                *embedding_rows,
                "",
                "Decision rule: MTEB/C-MTEB rank is only used to choose candidates. The project default changes only when a candidate improves enterprise-policy RAG metrics enough to justify latency, disk, memory, and dependency cost.",
            ]
        )

    chunking_rows = []
    chunking_targets = [
        ("V2", "Fixed window", "粗粒度窗口召回强，但引用边界弱。"),
        ("V2R", "Recursive character", "通用递归分块提升答案关键词覆盖，但 citation 不适合制度条款溯源。"),
        ("V6-bge-small", "Header/article-aware", "制度结构分块的引用准确率最高，适合政策问答的可追溯要求。"),
        ("V6-semantic", "Semantic chunk", "语义合并略提升答案覆盖，citation 与结构分块持平，但引入额外 embedding 分块成本。"),
    ]
    by_id = {result["config"]["id"]: result for result in completed}
    for config_id, label, finding in chunking_targets:
        result = by_id.get(config_id)
        if not result:
            continue
        summary = result["summary"]
        chunking_rows.append(
            f"| {label} | {config_id} `{summary['name']}` | {summary['chunks']} | "
            f"{summary['answer_accuracy_proxy']:.3f} | {summary['hit_at_5']:.3f} | "
            f"{summary['citation_accuracy']:.3f} | {finding} |"
        )
    if chunking_rows:
        lines.extend(
            [
                "",
                "## Chunking Strategy Findings",
                "",
                "| Chunk Strategy | Representative Config | Chunks | Answer Acc. | Hit@5 | Citation | Finding |",
                "| --- | --- | ---: | ---: | ---: | ---: | --- |",
                *chunking_rows,
                "",
                "Conclusion: recursive chunking is valuable as a generic fallback and improves broad recall, but enterprise policy QA prioritizes traceable citations. The deployed strategy remains header/article-aware chunking with bge-small hybrid retrieval; semantic chunking is a credible enhancement candidate when answer completeness matters more than strict article-level citation.",
            ]
        )

    index_rows = []
    index_targets = [
        ("V6-bge-small", "Current structured chunk index"),
        ("V10-sentence-window-vector", "Sentence-window vector"),
        ("V10-sentence-window-hybrid", "Sentence-window hybrid"),
        ("V11-structured-hybrid", "Structured metadata boost"),
        ("V12-sentence-structured-hybrid", "Sentence-window + structured boost"),
    ]
    by_id = {result["config"]["id"]: result for result in results}
    for config_id, label in index_targets:
        result = by_id.get(config_id)
        if not result:
            continue
        config = result["config"]
        if result["status"] == "skipped":
            index_rows.append(
                f"| {config_id} | {label} | skipped | {config['chunk_strategy']} | {config['retriever']} | - | - | - | - | - | {result.get('skip_reason', '')} |"
            )
            continue
        summary = result["summary"]
        index_rows.append(
            f"| {config_id} | {label} | completed | {summary['chunk_strategy']} | {summary['retriever']} | "
            f"{summary.get('chunks', 0)} | {summary['answer_accuracy_proxy']:.3f} | {summary['hit_at_5']:.3f} | "
            f"{summary['citation_accuracy']:.3f} | {summary['latency_p95_ms']:.1f} | "
            f"sentence_window={summary.get('sentence_window_size', 0)}, structured_boost={summary.get('structured_boost', False)} |"
        )
    if index_rows:
        lines.extend(
            [
                "",
                "## Index Optimization Findings",
                "",
                "| Version | Index Strategy | Status | Chunk | Retriever | Chunks | Answer Acc. | Hit@5 | Citation | p95 ms | Notes |",
                "| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
                *index_rows,
                "",
                "Decision rule: sentence-window retrieval is useful only if extra local context improves answers without damaging citation quality. Structured retrieval is useful only if metadata boosts improve ranking without over-filtering or hurting refusal behavior.",
            ]
        )

    lines.extend(
        [
            "",
            "## Failure-driven Iteration Notes",
            "",
        ]
    )
    for result in results:
        config = result["config"]
        lines.append(f"### {config['id']} {config['name']}")
        lines.append("")
        if result["status"] == "skipped":
            lines.append(f"- Status: skipped.")
            lines.append(f"- Reason: {result.get('skip_reason', 'unknown')}")
            lines.append(f"- Next optimization: {config['next_step']}")
            lines.append("")
            continue
        lines.append(f"- Finding: {config['description']}")
        lines.append(f"- Next optimization: {config['next_step']}")
        failures = result.get("failure_cases", [])[:3]
        if failures:
            lines.append("- Representative failures:")
            for failure in failures:
                lines.append(
                    f"  - `{failure['id']}` {failure['question']} | expected={failure['expected_doc_ids']} | retrieved={failure['retrieved_doc_ids']}"
                )
        else:
            lines.append("- Representative failures: none in top failure set.")
        lines.append("")

    lines.extend(
        [
            "## Vector Store Selection",
            "",
            "| Option | Fit for this project | Decision |",
            "| --- | --- | --- |",
            "| NumPy | Zero service dependency, easy to deploy on Streamlit, enough for hundreds/thousands of chunks. | Used for quick reproducible experiments. |",
            "| FAISS | Fast local ANN/flat vector search, good for local portfolio demo and offline benchmark. | Used when full dependencies are available. |",
            "| Chroma | Convenient local persistence and metadata APIs, heavier dependency surface than this demo needs. | Good next step, not required here. |",
            "| Milvus | Production-scale vector DB with distributed deployment. | Overkill for personal demo; mention as enterprise option. |",
            "| Elasticsearch | Strong BM25 and hybrid search ecosystem. | Useful if enterprise already has ES. |",
            "| PGVector | Good when policies and metadata already live in Postgres. | Suitable for app integration, not needed for current local demo. |",
            "",
            "## Resume-ready Story",
            "",
            f"基于 {selected.get('total', 0)} 条制度问答评估集，从 `{first.get('name', 'baseline')}` 出发，依次优化 chunk、BM25+向量混合检索、RRF 融合与低置信拒答；{story_prefix}验证链路收益，使 Answer Accuracy Proxy 从 {first.get('answer_accuracy_proxy', 0):.3f} 提升至 {selected.get('answer_accuracy_proxy', 0):.3f}，Citation Accuracy 从 {first.get('citation_accuracy', 0):.3f} 提升至 {selected.get('citation_accuracy', 0):.3f}，Refusal Accuracy 从 {first.get('refusal_accuracy', 0):.3f} 提升至 {selected.get('refusal_accuracy', 0):.3f}。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="Run quick reproducible experiments only.")
    parser.add_argument("--full", action="store_true", help="Run quick experiments plus full embedding-model configs.")
    parser.add_argument("--offline", action="store_true", help="Use local Hugging Face cache only; skipped model configs are allowed.")
    parser.add_argument("--allow-skip", action="store_true", help="Allow unavailable embedding configs to be marked skipped.")
    parser.add_argument("--strict", action="store_true", help="Fail the run if any full embedding config is skipped.")
    parser.add_argument("--config-pattern", default="*.json", help="Only run configs whose filename matches this glob pattern.")
    args = parser.parse_args()
    mode = "full" if args.full else "quick"
    strict = args.strict and mode == "full" and not args.allow_skip

    local_embedding_only = os.getenv("SMARTOFFICE_EMBEDDING_LOCAL_ONLY", "1") == "1"
    if args.offline or local_embedding_only:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
    else:
        os.environ.pop("HF_HUB_OFFLINE", None)
        os.environ.pop("TRANSFORMERS_OFFLINE", None)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DOC_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    configs = load_configs(mode, args.config_pattern)
    results = [evaluate_experiment(config, load_cases(config.eval_dataset_layers)) for config in configs]
    skipped = [result for result in results if result["status"] == "skipped"]
    if strict and skipped:
        skipped_names = ", ".join(result["config"]["name"] for result in skipped)
        raise ExperimentFailed(
            f"Full online experiment is strict and these configs did not complete: {skipped_names}. "
            "Fix network/model availability, or rerun with --offline/--allow-skip for exploratory reports."
        )
    completed = [result for result in results if result["status"] == "completed"]
    selected_result = select_final_result(results)
    selected_summary = selected_result["summary"] if selected_result else {}

    JSON_REPORT_PATH.write_text(
        json.dumps({"mode": mode, "selected_summary": selected_summary, "results": compact_results(results)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_csv(results)
    DOC_REPORT_PATH.write_text(build_markdown(results), encoding="utf-8")

    print(
        json.dumps(
            {"mode": mode, "completed": len(completed), "selected": selected_summary.get("name"), "report": str(DOC_REPORT_PATH)},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
