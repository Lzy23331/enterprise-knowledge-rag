# Embedding Model Selection

本报告记录 MTEB/C-MTEB 候选 embedding 模型在本项目中的下载、加载和本地复现状态。MTEB 排名只用于筛选候选，最终选择仍以企业制度 RAG 评估集为准。

## Candidate Model Validation

| Model | Mode | Status | Dim | Trust Remote Code | Load Mode | Elapsed ms | Error |
| --- | --- | --- | ---: | --- | --- | ---: | --- |
| BAAI/bge-m3 | offline | completed | 1024 | False | local_cache | 6656.7 |  |
| Alibaba-NLP/gte-Qwen2-1.5B-instruct | offline | failed | 0 | True |  | 869.2 | 'DynamicCache' object has no attribute 'get_usable_length' |
| Qwen/Qwen3-Embedding-0.6B | offline | completed | 1024 | True | local_cache | 1148.6 |  |

## Project Evaluation Results

| Version | Model | Status | Answer Acc. | Hit@5 | Citation | Refusal | p95 ms | Notes |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| V6-bge-small | BAAI/bge-small-zh-v1.5 | completed | 0.476 | 0.903 | 0.901 | 1.000 | 30.1 | dim=512, load_ms=42.1 |
| V9-bge-m3 | BAAI/bge-m3 | completed | 0.484 | 0.900 | 0.898 | 1.000 | 111.9 | dim=1024, load_ms=788.1 |
| V9-gte-qwen2-1.5b | Alibaba-NLP/gte-Qwen2-1.5B-instruct | skipped | - | - | - | - | - | Embedding build failed: Alibaba-NLP/gte-Qwen2-1.5B-instruct; 'DynamicCache' object has no attribute 'get_usable_length' |
| V9-qwen3-0.6b | Qwen/Qwen3-Embedding-0.6B | completed | 0.472 | 0.910 | 0.907 | 1.000 | 222.2 | dim=1024, load_ms=995.8 |

当前实验结论：`BAAI/bge-small-zh-v1.5` 仍保留为默认主链路 embedding。`BAAI/bge-m3` 的 Answer Accuracy Proxy 略高，但 Citation Accuracy 略低且 p95 延迟明显更高；`Qwen/Qwen3-Embedding-0.6B` 的 Citation Accuracy 略高，但 Answer Accuracy Proxy 略低且 p95 延迟最高；`gte-Qwen2-1.5B-instruct` 在当前依赖组合下 encode 失败，因此不能作为有效对比结论。

## Decision Rules

- `completed` in online mode means the model can be downloaded and encoded in the current environment.
- `completed` in offline mode means the model can be reproduced from `.cache/huggingface` without network access.
- Any failed model must be reported as skipped in `run_experiments.py --full`; it must not fall back to `local-hashing` for final conclusions.
- A larger model only replaces `BAAI/bge-small-zh-v1.5` if it improves project metrics enough to justify latency, disk, memory, and dependency cost.