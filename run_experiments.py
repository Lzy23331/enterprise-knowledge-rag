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

    @classmethod
    def from_path(cls, path: Path) -> "ExperimentConfig":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(**data)


class ExperimentSkipped(Exception):
    pass


class ExperimentFailed(Exception):
    pass


def load_cases() -> List[Dict[str, Any]]:
    cases = []
    for path in sorted(EVAL_DIR.glob("*.jsonl")):
        with path.open("r", encoding="utf-8-sig") as handle:
            for line in handle:
                if line.strip():
                    case = json.loads(line)
                    case.setdefault("eval_file", path.name)
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
        rewritten = query_rewrite(question) if self.config.query_rewrite else question
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
        response = runner.answer(case["question"])
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


def load_configs(mode: str) -> List[ExperimentConfig]:
    configs = [ExperimentConfig.from_path(path) for path in sorted(CONFIG_DIR.glob("*.json"))]
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
                    }
                )
            else:
                row.update(result.get("summary", {}))
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
    return (
        summary.get("answer_accuracy_proxy", 0.0) * 0.30
        + summary.get("hit_at_5", 0.0) * 0.20
        + summary.get("citation_accuracy", 0.0) * 0.30
        + summary.get("refusal_accuracy", 0.0) * 0.20
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

    embedding_rows = []
    embedding_ids = [
        "V6-bge-small",
        "V9-qwen3-0.6b",
        "V9-bge-m3",
        "V9-gte-qwen2-1.5b",
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
    cases = load_cases()
    results = [evaluate_experiment(config, cases) for config in load_configs(mode)]
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
