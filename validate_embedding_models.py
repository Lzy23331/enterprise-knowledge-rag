import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent
os.environ.setdefault("HF_HOME", str(PROJECT_ROOT / ".cache" / "huggingface"))

from smart_office_rag.indexing import EmbeddingModel

CONFIG_DIR = PROJECT_ROOT / "experiments" / "configs"
REPORT_PATH = PROJECT_ROOT / "docs" / "EMBEDDING_MODEL_SELECTION.md"


def load_candidate_configs() -> List[Dict[str, Any]]:
    configs = []
    for path in sorted(CONFIG_DIR.glob("v[89]_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        model_name = data.get("embedding_model", "")
        if model_name and model_name != "local-hashing":
            configs.append(data)
    seen = {}
    for config in configs:
        seen.setdefault(config["embedding_model"], config)
    return list(seen.values())


def validate_model(config: Dict[str, Any], offline: bool) -> Dict[str, Any]:
    if offline:
        os.environ["SMARTOFFICE_EMBEDDING_LOCAL_ONLY"] = "1"
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
    else:
        os.environ["SMARTOFFICE_EMBEDDING_LOCAL_ONLY"] = "0"
        os.environ.pop("HF_HUB_OFFLINE", None)
        os.environ.pop("TRANSFORMERS_OFFLINE", None)

    started = time.perf_counter()
    try:
        model = EmbeddingModel(
            config["embedding_model"],
            trust_remote_code=bool(config.get("embedding_trust_remote_code", False)),
            query_instruction=config.get("query_instruction", ""),
            document_instruction=config.get("document_instruction", ""),
            normalize_embeddings=bool(config.get("normalize_embeddings", True)),
            max_seq_length=config.get("max_seq_length"),
            require_real_embedding=True,
        )
        query_vector = model.embed_query("员工报销需要提交哪些材料？")
        doc_vectors = model.embed_documents(["员工提交费用报销时，应提供发票、审批单和付款凭证。"])
        return {
            "model": config["embedding_model"],
            "status": "completed",
            "mode": "offline" if offline else "online",
            "load_mode": model.load_mode,
            "dimension": int(query_vector.shape[0]),
            "document_vector_count": int(doc_vectors.shape[0]),
            "trust_remote_code": bool(config.get("embedding_trust_remote_code", False)),
            "elapsed_ms": (time.perf_counter() - started) * 1000,
            "error": "",
        }
    except Exception as exc:
        return {
            "model": config["embedding_model"],
            "status": "failed",
            "mode": "offline" if offline else "online",
            "load_mode": "",
            "dimension": 0,
            "document_vector_count": 0,
            "trust_remote_code": bool(config.get("embedding_trust_remote_code", False)),
            "elapsed_ms": (time.perf_counter() - started) * 1000,
            "error": str(exc),
        }


def write_report(results: List[Dict[str, Any]]) -> None:
    lines = [
        "# Embedding Model Selection",
        "",
        "本报告记录 MTEB/C-MTEB 候选 embedding 模型在本项目中的下载、加载和本地复现状态。MTEB 排名只用于筛选候选，最终选择仍以企业制度 RAG 评估集为准。",
        "",
        "## Candidate Model Validation",
        "",
        "| Model | Mode | Status | Dim | Trust Remote Code | Load Mode | Elapsed ms | Error |",
        "| --- | --- | --- | ---: | --- | --- | ---: | --- |",
    ]
    for result in results:
        error = result["error"].replace("|", "/").replace("\n", " ")[:180]
        lines.append(
            f"| {result['model']} | {result['mode']} | {result['status']} | {result['dimension']} | "
            f"{result['trust_remote_code']} | {result['load_mode']} | {result['elapsed_ms']:.1f} | {error} |"
        )

    experiment_path = PROJECT_ROOT / "experiments" / "results" / "experiment_report.json"
    if experiment_path.exists():
        data = json.loads(experiment_path.read_text(encoding="utf-8"))
        rows = []
        for result in data.get("results", []):
            config_id = result.get("config", {}).get("id", "")
            if config_id not in {"V6-bge-small", "V9-qwen3-0.6b", "V9-bge-m3", "V9-gte-qwen2-1.5b"}:
                continue
            if result.get("status") == "skipped":
                rows.append(
                    f"| {config_id} | {result['config']['embedding_model']} | skipped | - | - | - | - | - | {result.get('skip_reason', '')} |"
                )
                continue
            summary = result.get("summary", {})
            rows.append(
                f"| {config_id} | {summary.get('embedding_model', '')} | completed | "
                f"{summary.get('answer_accuracy_proxy', 0):.3f} | {summary.get('hit_at_5', 0):.3f} | "
                f"{summary.get('citation_accuracy', 0):.3f} | {summary.get('refusal_accuracy', 0):.3f} | "
                f"{summary.get('latency_p95_ms', 0):.1f} | dim={summary.get('embedding_dimension', 0)}, "
                f"load_ms={summary.get('model_load_ms', 0):.1f} |"
            )
        if rows:
            lines.extend(
                [
                    "",
                    "## Project Evaluation Results",
                    "",
                    "| Version | Model | Status | Answer Acc. | Hit@5 | Citation | Refusal | p95 ms | Notes |",
                    "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
                    *rows,
                    "",
                    "当前实验结论：`BAAI/bge-small-zh-v1.5` 仍保留为默认主链路 embedding。`BAAI/bge-m3` 的 Answer Accuracy Proxy 略高，但 Citation Accuracy 略低且 p95 延迟明显更高；`Qwen/Qwen3-Embedding-0.6B` 的 Citation Accuracy 略高，但 Answer Accuracy Proxy 略低且 p95 延迟最高；`gte-Qwen2-1.5B-instruct` 在当前依赖组合下 encode 失败，因此不能作为有效对比结论。",
                ]
            )

    lines.extend(
        [
            "",
            "## Decision Rules",
            "",
            "- `completed` in online mode means the model can be downloaded and encoded in the current environment.",
            "- `completed` in offline mode means the model can be reproduced from `.cache/huggingface` without network access.",
            "- Any failed model must be reported as skipped in `run_experiments.py --full`; it must not fall back to `local-hashing` for final conclusions.",
            "- A larger model only replaces `BAAI/bge-small-zh-v1.5` if it improves project metrics enough to justify latency, disk, memory, and dependency cost.",
        ]
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline-only", action="store_true", help="Only validate local cache loading.")
    args = parser.parse_args()

    configs = load_candidate_configs()
    results: List[Dict[str, Any]] = []
    if not args.offline_only:
        for config in configs:
            results.append(validate_model(config, offline=False))
    for config in configs:
        results.append(validate_model(config, offline=True))
    write_report(results)
    print(json.dumps({"models": len(configs), "results": results, "report": str(REPORT_PATH)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
