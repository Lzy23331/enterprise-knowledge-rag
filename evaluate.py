import json
import math
import os
import statistics
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List

PROJECT_ROOT = Path(__file__).resolve().parent
os.environ.setdefault("HF_HOME", str(PROJECT_ROOT / ".cache" / "huggingface"))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("SMARTOFFICE_DISABLE_LLM", "1")

from smart_office_rag.config import DEFAULT_CONFIG, RAGConfig
from smart_office_rag.generator import AnswerGenerator
from smart_office_rag.pipeline import EnterpriseKnowledgeRAG
from smart_office_rag.pipeline import RAGResponse
from smart_office_rag.retrieval import BM25TextRetriever
from smart_office_rag.retrieval import KeywordRetriever
from smart_office_rag.types import Document


EVAL_PATH = PROJECT_ROOT / "data" / "eval" / "eval_cases.jsonl"
JSON_REPORT_PATH = PROJECT_ROOT / "eval_report.json"
MD_REPORT_PATH = PROJECT_ROOT / "eval_report.md"
TOP_K = 5
REFUSAL_MARKERS = ("没有检索到明确依据", "没有明确依据", "无法回答", "建议联系", "未检索到")
STRATEGIES = ("llm_direct", "bm25_only", "vector_only", "hybrid_rrf")


def load_cases(path: Path = EVAL_PATH) -> List[Dict[str, Any]]:
    cases = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
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
    if not expected_doc_ids:
        return 0.0
    if not source_doc_ids:
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
    index = min(len(ordered) - 1, math.ceil((pct / 100) * len(ordered)) - 1)
    return ordered[index]


def average(values: List[float]) -> float:
    return statistics.mean(values) if values else 0.0


def summarize_group(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    retrieval_cases = [case for case in cases if not case["should_refuse"]]
    refusal_cases = [case for case in cases if case["should_refuse"]]
    return {
        "total": len(cases),
        "retrieval_cases": len(retrieval_cases),
        "refusal_cases": len(refusal_cases),
        "hit_at_1": average([case["metrics"]["hit_at_1"] for case in retrieval_cases]),
        "hit_at_3": average([case["metrics"]["hit_at_3"] for case in retrieval_cases]),
        "hit_at_5": average([case["metrics"]["hit_at_5"] for case in retrieval_cases]),
        "recall_at_5": average([case["metrics"]["recall_at_5"] for case in retrieval_cases]),
        "context_precision_at_5": average([case["metrics"]["context_precision_at_5"] for case in retrieval_cases]),
        "mrr_at_5": average([case["metrics"]["mrr_at_5"] for case in retrieval_cases]),
        "ndcg_at_5": average([case["metrics"]["ndcg_at_5"] for case in retrieval_cases]),
        "citation_accuracy": average([case["metrics"]["citation_accuracy"] for case in cases]),
        "answer_correctness_proxy": average([case["metrics"]["answer_correctness_proxy"] for case in retrieval_cases]),
        "faithfulness_proxy": average([case["metrics"]["faithfulness_proxy"] for case in cases]),
        "refusal_accuracy": average([case["metrics"]["refusal_accuracy"] for case in refusal_cases]),
    }


def build_markdown_report(report: Dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# SmartOfficeRAG Evaluation Report",
        "",
        "## Overall Metrics",
        "",
        f"- Total cases: {summary['total']}",
        f"- Retrieval cases: {summary['retrieval_cases']}",
        f"- Refusal cases: {summary['refusal_cases']}",
        f"- Hit@1 / Hit@3 / Hit@5: {summary['hit_at_1']:.3f} / {summary['hit_at_3']:.3f} / {summary['hit_at_5']:.3f}",
        f"- Recall@5: {summary['recall_at_5']:.3f}",
        f"- Context Precision@5: {summary['context_precision_at_5']:.3f}",
        f"- MRR@5: {summary['mrr_at_5']:.3f}",
        f"- nDCG@5: {summary['ndcg_at_5']:.3f}",
        f"- Citation Accuracy: {summary['citation_accuracy']:.3f}",
        f"- Refusal Accuracy: {summary['refusal_accuracy']:.3f}",
        f"- Faithfulness Proxy: {summary['faithfulness_proxy']:.3f}",
        f"- Answer Correctness Proxy: {summary['answer_correctness_proxy']:.3f}",
        f"- Latency p50 / p95: {summary['latency_p50_ms']:.1f} ms / {summary['latency_p95_ms']:.1f} ms",
        "",
        "## Metrics Notes",
        "",
        "- Retrieval metrics use expected document IDs from `data/eval/eval_cases.jsonl`.",
        "- Faithfulness and answer correctness are deterministic proxies for local evaluation.",
        "- For rigorous judge-based scoring, add RAGAS/DeepEval-style LLM-as-a-judge on the same cases.",
        "",
        "## Retrieval Strategy Comparison",
        "",
        "| Strategy | Hit@5 | MRR@5 | Citation Acc. | Refusal Acc. | p50 Latency | p95 Latency |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in report.get("strategy_comparison", []):
        lines.append(
            f"| {item['strategy']} | {item['hit_at_5']:.3f} | {item['mrr_at_5']:.3f} | "
            f"{item['citation_accuracy']:.3f} | {item['refusal_accuracy']:.3f} | "
            f"{item['latency_p50_ms']:.1f} ms | {item['latency_p95_ms']:.1f} ms |"
        )

    lines.extend(
        [
            "",
            "## Why Hybrid RAG",
            "",
            "- BM25 is robust for exact policy names, form IDs, and business terms.",
            "- Vector retrieval improves recall for paraphrased employee questions.",
            "- RRF reduces dependence on one retriever and keeps ranking explainable.",
            "- Low-confidence refusal and citation checks turn failures into auditable cases for chunking, metadata, query rewriting, or policy coverage iteration.",
            "",
        "## Question Type Breakdown",
        "",
        "| Question Type | Cases | Hit@5 | MRR@5 | Citation Acc. | Refusal Acc. |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for group, metrics in sorted(report["by_question_type"].items()):
        lines.append(
            f"| {group} | {metrics['total']} | {metrics['hit_at_5']:.3f} | "
            f"{metrics['mrr_at_5']:.3f} | {metrics['citation_accuracy']:.3f} | "
            f"{metrics['refusal_accuracy']:.3f} |"
        )

    lines.extend(["", "## Top Failure Cases", ""])
    failures = report["failure_cases"][:10]
    if not failures:
        lines.append("- No failures detected.")
    for case in failures:
        lines.append(
            f"- `{case['id']}` [{case['question_type']}]: {case['question']} "
            f"| expected={case['expected_doc_ids']} retrieved={case['retrieved_doc_ids']}"
        )
    return "\n".join(lines) + "\n"


def build_sources(chunks: List[Document]) -> List[Dict[str, str]]:
    return EnterpriseKnowledgeRAG._build_sources(chunks)


class EvalRunner:
    name = "base"

    def ask(self, question: str) -> RAGResponse:
        raise NotImplementedError


class HybridRunner(EvalRunner):
    name = "hybrid_rrf"

    def __init__(self, config: RAGConfig):
        self.rag = EnterpriseKnowledgeRAG(config)
        self.index_build_ms = 0.0

    def initialize(self) -> None:
        started = time.perf_counter()
        self.rag.initialize(rebuild_index=True)
        self.index_build_ms = (time.perf_counter() - started) * 1000

    def ask(self, question: str) -> RAGResponse:
        return self.rag.ask(question)


class SingleRetrieverRunner(EvalRunner):
    def __init__(self, name: str, chunks: List[Document], retriever: Any):
        self.name = name
        self.chunks = chunks
        self.retriever = retriever
        self.generator = AnswerGenerator(
            model_name=DEFAULT_CONFIG.llm_model,
            base_url=DEFAULT_CONFIG.llm_base_url,
            temperature=DEFAULT_CONFIG.temperature,
            max_tokens=DEFAULT_CONFIG.max_tokens,
        )

    def ask(self, question: str) -> RAGResponse:
        started = time.perf_counter()
        if EnterpriseKnowledgeRAG._is_out_of_scope(question):
            answer = self.generator.generate_no_evidence(question, [], reason="out_of_scope")
            return RAGResponse(answer, [], [], {"strategy": self.name}, (time.perf_counter() - started) * 1000, True, "out_of_scope")

        docs = self.retriever.invoke(question)[:TOP_K]
        if EnterpriseKnowledgeRAG._is_low_confidence(question, docs):
            answer = self.generator.generate_no_evidence(question, docs[:3], reason="low_confidence")
            return RAGResponse(
                answer,
                build_sources(docs[:3]),
                docs,
                {"strategy": self.name, "refusal_reason": "low_confidence"},
                (time.perf_counter() - started) * 1000,
                True,
                "low_confidence",
            )

        answer = self.generator.generate(question, docs)
        return RAGResponse(
            answer,
            build_sources(docs),
            docs,
            {"strategy": self.name},
            (time.perf_counter() - started) * 1000,
            False,
        )


class DirectLLMBaselineRunner(EvalRunner):
    name = "llm_direct"

    def ask(self, question: str) -> RAGResponse:
        started = time.perf_counter()
        answer = (
            "结论：\n"
            "这是无检索增强的直答基线，不读取企业制度知识库，因此无法提供可验证引用。\n\n"
            "引用来源：\n"
            "- 无。"
        )
        return RAGResponse(answer, [], [], {"strategy": self.name}, (time.perf_counter() - started) * 1000, False)


def build_runners(config: RAGConfig) -> Dict[str, EvalRunner]:
    hybrid = HybridRunner(config)
    hybrid.initialize()
    chunks = hybrid.rag.chunks

    if hybrid.rag.index is None or hybrid.rag.index.vectorstore is None:
        raise RuntimeError("Hybrid runner did not initialize a vectorstore.")
    vectorstore = hybrid.rag.index.vectorstore
    vector_retriever = vectorstore.as_retriever(search_kwargs={"k": max(TOP_K * 4, 20)})

    return {
        "llm_direct": DirectLLMBaselineRunner(),
        "bm25_only": SingleRetrieverRunner("bm25_only", chunks, BM25TextRetriever(chunks, k=max(TOP_K * 4, 20))),
        "vector_only": SingleRetrieverRunner("vector_only", chunks, vector_retriever),
        "hybrid_rrf": hybrid,
    }


def evaluate_runner(cases: List[Dict[str, Any]], runner: EvalRunner) -> Dict[str, Any]:
    evaluated_cases: List[Dict[str, Any]] = []
    latencies: List[float] = []
    for case in cases:
        response = runner.ask(case["question"])
        latency_ms = response.latency_ms
        latencies.append(latency_ms)

        expected_doc_ids = case["expected_doc_ids"]
        retrieved_doc_ids = [str(doc.metadata.get("doc_id")) for doc in response.chunks]
        source_doc_ids = [str(source.get("doc_id", "")) for source in response.sources]
        should_refuse = bool(case["should_refuse"])
        refused = response.refused or contains_refusal(response.answer)

        metrics = {
            "hit_at_1": hit_at_k(retrieved_doc_ids, expected_doc_ids, 1),
            "hit_at_3": hit_at_k(retrieved_doc_ids, expected_doc_ids, 3),
            "hit_at_5": hit_at_k(retrieved_doc_ids, expected_doc_ids, 5),
            "recall_at_5": recall_at_k(retrieved_doc_ids, expected_doc_ids, 5),
            "context_precision_at_5": precision_at_k(retrieved_doc_ids, expected_doc_ids, 5),
            "mrr_at_5": mrr_at_k(retrieved_doc_ids, expected_doc_ids, 5),
            "ndcg_at_5": ndcg_at_k(retrieved_doc_ids, expected_doc_ids, 5),
            "citation_accuracy": citation_accuracy(source_doc_ids, expected_doc_ids, should_refuse),
            "refusal_accuracy": float(refused == should_refuse) if should_refuse else 0.0,
            "answer_correctness_proxy": text_overlap_score(response.answer, case["reference_answer"]) if not should_refuse else 0.0,
            "faithfulness_proxy": 1.0 if (should_refuse and refused) else citation_accuracy(source_doc_ids, expected_doc_ids, should_refuse),
            "latency_ms": latency_ms,
        }

        evaluated_cases.append(
            {
                **case,
                "retrieved_doc_ids": retrieved_doc_ids,
                "sources": response.sources,
                "answer_preview": response.answer[:500],
                "refused": refused,
                "metrics": metrics,
            }
        )

    summary = summarize_group(evaluated_cases)
    summary.update(
        {
            "strategy": runner.name,
            "latency_p50_ms": percentile(latencies, 50),
            "latency_p95_ms": percentile(latencies, 95),
            "latency_avg_ms": average(latencies),
        }
    )
    return {"summary": summary, "cases": evaluated_cases}


def main() -> None:
    cases = load_cases()
    config = RAGConfig(
        data_path=DEFAULT_CONFIG.data_path,
        pdf_data_path=DEFAULT_CONFIG.pdf_data_path,
        pdf_loader_mode=DEFAULT_CONFIG.pdf_loader_mode,
        index_path=DEFAULT_CONFIG.index_path,
        embedding_model=os.getenv("SMARTOFFICE_EVAL_EMBEDDING_MODEL", "local-hashing"),
        top_k=TOP_K,
        llm_model=DEFAULT_CONFIG.llm_model,
        llm_base_url=DEFAULT_CONFIG.llm_base_url,
        temperature=DEFAULT_CONFIG.temperature,
        max_tokens=DEFAULT_CONFIG.max_tokens,
        use_vector_index=True,
    )

    runners = build_runners(config)
    strategy_results = {name: evaluate_runner(cases, runners[name]) for name in STRATEGIES}
    evaluated_cases = strategy_results["hybrid_rrf"]["cases"]
    summary = strategy_results["hybrid_rrf"]["summary"]
    hybrid_runner = runners["hybrid_rrf"]
    summary.update(
        {
            "index_build_ms": getattr(hybrid_runner, "index_build_ms", 0.0),
            "policy_documents": len(getattr(hybrid_runner, "rag").parents),
            "chunks": len(getattr(hybrid_runner, "rag").chunks),
        }
    )

    by_question_type: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_department: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for case in evaluated_cases:
        by_question_type[case["question_type"]].append(case)
        by_department[case["department"]].append(case)

    failure_cases = [
        case
        for case in evaluated_cases
        if (
            (not case["should_refuse"] and case["metrics"]["hit_at_5"] < 1.0)
            or (case["should_refuse"] and case["metrics"]["refusal_accuracy"] < 1.0)
            or case["metrics"]["citation_accuracy"] < 0.5
        )
    ]

    report = {
        "summary": summary,
        "strategy_comparison": [strategy_results[name]["summary"] for name in STRATEGIES],
        "by_question_type": {key: summarize_group(value) for key, value in by_question_type.items()},
        "by_department": {key: summarize_group(value) for key, value in by_department.items()},
        "failure_cases": failure_cases,
        "cases": evaluated_cases,
    }

    JSON_REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    MD_REPORT_PATH.write_text(build_markdown_report(report), encoding="utf-8")
    print(json.dumps({"summary": summary, "failure_count": len(failure_cases)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
