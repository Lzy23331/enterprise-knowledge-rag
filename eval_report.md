# SmartOfficeRAG Evaluation Report

## Overall Metrics

- Total cases: 324
- Retrieval cases: 300
- Refusal cases: 24
- Hit@1 / Hit@3 / Hit@5: 0.923 / 0.923 / 0.923
- Recall@5: 0.923
- Context Precision@5: 0.923
- MRR@5: 0.923
- nDCG@5: 0.923
- Citation Accuracy: 0.920
- Refusal Accuracy: 1.000
- Faithfulness Proxy: 0.929
- Answer Correctness Proxy: 0.489
- Latency p50 / p95: 18.3 ms / 29.3 ms

## Metrics Notes

- Retrieval metrics use expected document IDs from all `data/eval/*.jsonl` files.
- Faithfulness and answer correctness are deterministic proxies for local evaluation.
- For rigorous judge-based scoring, add RAGAS/DeepEval-style LLM-as-a-judge on the same cases.

## Retrieval Strategy Comparison

| Strategy | Hit@5 | MRR@5 | Citation Acc. | Refusal Acc. | p50 Latency | p95 Latency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| llm_direct | 0.000 | 0.000 | 0.074 | 0.000 | 0.0 ms | 0.0 ms |
| bm25_only | 0.963 | 0.946 | 0.826 | 1.000 | 16.1 ms | 22.5 ms |
| vector_only | 0.753 | 0.700 | 0.355 | 1.000 | 1.9 ms | 2.8 ms |
| hybrid_rrf | 0.923 | 0.923 | 0.920 | 1.000 | 18.3 ms | 29.3 ms |

## Why Hybrid RAG

- BM25 is robust for exact policy names, form IDs, and business terms.
- Vector retrieval improves recall for paraphrased employee questions.
- RRF reduces dependence on one retriever and keeps ranking explainable.
- Low-confidence refusal and citation checks turn failures into auditable cases for chunking, metadata, query rewriting, or policy coverage iteration.

## Question Type Breakdown

| Question Type | Cases | Hit@5 | MRR@5 | Citation Acc. | Refusal Acc. |
| --- | ---: | ---: | ---: | ---: | ---: |
| PDF-事实型 | 15 | 1.000 | 1.000 | 1.000 | 0.000 |
| PDF-例外条件型 | 15 | 1.000 | 1.000 | 1.000 | 0.000 |
| PDF-拒答型 | 2 | 0.000 | 0.000 | 0.500 | 1.000 |
| PDF-时限型 | 15 | 1.000 | 1.000 | 1.000 | 0.000 |
| PDF-材料型 | 15 | 1.000 | 1.000 | 1.000 | 0.000 |
| PDF-版本差异型 | 15 | 1.000 | 1.000 | 1.000 | 0.000 |
| PDF-跨文档引用型 | 15 | 1.000 | 1.000 | 1.000 | 0.000 |
| 合规类 | 30 | 1.000 | 1.000 | 1.000 | 0.000 |
| 同义改写类 | 30 | 0.700 | 0.700 | 0.700 | 0.000 |
| 时限类 | 30 | 0.933 | 0.933 | 0.933 | 0.000 |
| 材料类 | 30 | 0.900 | 0.900 | 0.900 | 0.000 |
| 模糊追问类 | 30 | 0.700 | 0.700 | 0.700 | 0.000 |
| 流程类 | 30 | 1.000 | 1.000 | 1.000 | 0.000 |
| 知识库外拒答类 | 22 | 0.000 | 0.000 | 0.909 | 1.000 |
| 系统入口类 | 30 | 1.000 | 1.000 | 1.000 | 0.000 |

## Top Failure Cases

- `hr_leave_2026_paraphrase` [同义改写类]: 我想咨询年假相关事项，应该看哪份制度、走哪个入口？ | expected=['HR-LEAVE-2026'] retrieved=['PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026']
- `hr_leave_2026_ambiguous_followup` [模糊追问类]: 请假申请材料不齐被退回后怎么处理，是否可以线下先办？ | expected=['HR-LEAVE-2026'] retrieved=['PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026']
- `hr_onboard_2026_materials` [材料类]: 办理入离职流程需要哪些材料？ | expected=['HR-ONBOARD-2026'] retrieved=['PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026']
- `hr_onboard_2026_sla` [时限类]: 入离职流程的审批时限或提前要求是什么？ | expected=['HR-ONBOARD-2026'] retrieved=['PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026']
- `hr_onboard_2026_ambiguous_followup` [模糊追问类]: 入离职流程材料不齐被退回后怎么处理，是否可以线下先办？ | expected=['HR-ONBOARD-2026'] retrieved=['PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026']
- `hr_perf_2026_ambiguous_followup` [模糊追问类]: 绩效管理材料不齐被退回后怎么处理，是否可以线下先办？ | expected=['HR-PERF-2026'] retrieved=['PDF-HR-PERF-2026', 'PDF-HR-PERF-2026', 'PDF-HR-PERF-2026', 'PDF-HR-PERF-2026', 'PDF-HR-PERF-2026']
- `fin_exp_2026_materials` [材料类]: 办理报销申请需要哪些材料？ | expected=['FIN-EXP-2026'] retrieved=['PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026']
- `fin_exp_2026_paraphrase` [同义改写类]: 我想咨询差旅费相关事项，应该看哪份制度、走哪个入口？ | expected=['FIN-EXP-2026'] retrieved=['PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026']
- `fin_exp_2026_ambiguous_followup` [模糊追问类]: 报销申请材料不齐被退回后怎么处理，是否可以线下先办？ | expected=['FIN-EXP-2026'] retrieved=['PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026']
- `fin_budget_2026_ambiguous_followup` [模糊追问类]: 预算管理材料不齐被退回后怎么处理，是否可以线下先办？ | expected=['FIN-BUDGET-2026'] retrieved=['PDF-HR-ATT-2026', 'PDF-HR-ATT-2026', 'PDF-HR-ATT-2026', 'PDF-HR-ATT-2026', 'PDF-HR-ATT-2026']
