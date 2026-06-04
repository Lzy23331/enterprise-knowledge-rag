# SmartOfficeRAG Evaluation Report

## Overall Metrics

- Total cases: 172
- Retrieval cases: 150
- Refusal cases: 22
- Hit@1 / Hit@3 / Hit@5: 1.000 / 1.000 / 1.000
- Recall@5: 1.000
- Context Precision@5: 1.000
- MRR@5: 1.000
- nDCG@5: 1.000
- Citation Accuracy: 1.000
- Refusal Accuracy: 1.000
- Faithfulness Proxy: 1.000
- Answer Correctness Proxy: 0.603
- Latency p50 / p95: 31.1 ms / 36.9 ms

## Metrics Notes

- Retrieval metrics use expected document IDs from `data/eval/eval_cases.jsonl`.
- Faithfulness and answer correctness are deterministic proxies for local evaluation.
- For rigorous judge-based scoring, add RAGAS/DeepEval-style LLM-as-a-judge on the same cases.

## Question Type Breakdown

| Question Type | Cases | Hit@5 | MRR@5 | Citation Acc. | Refusal Acc. |
| --- | ---: | ---: | ---: | ---: | ---: |
| 合规类 | 30 | 1.000 | 1.000 | 1.000 | 0.000 |
| 时限类 | 30 | 1.000 | 1.000 | 1.000 | 0.000 |
| 材料类 | 30 | 1.000 | 1.000 | 1.000 | 0.000 |
| 流程类 | 30 | 1.000 | 1.000 | 1.000 | 0.000 |
| 知识库外拒答类 | 22 | 0.000 | 0.000 | 1.000 | 1.000 |
| 系统入口类 | 30 | 1.000 | 1.000 | 1.000 | 0.000 |

## Top Failure Cases

- No failures detected.
