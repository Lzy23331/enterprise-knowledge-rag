# SmartOfficeRAG Evaluation Report

## Overall Metrics

- Total cases: 324
- Retrieval cases: 300
- Refusal cases: 24
- Hit@1 / Hit@3 / Hit@5: 0.903 / 0.903 / 0.903
- Recall@5: 0.903
- Context Precision@5: 0.903
- MRR@5: 0.903
- nDCG@5: 0.903
- Citation Accuracy: 0.901
- Refusal Accuracy: 1.000
- Faithfulness Proxy: 0.910
- Answer Correctness Proxy: 0.441
- Latency p50 / p95: 10.1 ms / 16.5 ms

## Metrics Notes

- Retrieval metrics use expected document IDs from all `data/eval/*.jsonl` files.
- Faithfulness and answer correctness are deterministic proxies for local evaluation.
- For rigorous judge-based scoring, add RAGAS/DeepEval-style LLM-as-a-judge on the same cases.

## Retrieval Strategy Comparison

| Strategy | Hit@5 | MRR@5 | Citation Acc. | Refusal Acc. | p50 Latency | p95 Latency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| llm_direct | 0.000 | 0.000 | 0.074 | 0.000 | 0.0 ms | 0.0 ms |
| bm25_only | 0.973 | 0.924 | 0.856 | 1.000 | 8.3 ms | 10.6 ms |
| vector_only | 0.783 | 0.686 | 0.397 | 1.000 | 1.0 ms | 2.5 ms |
| hybrid_rrf | 0.903 | 0.903 | 0.901 | 1.000 | 10.1 ms | 16.5 ms |

## Why Hybrid RAG

- BM25 is robust for exact policy names, form IDs, and business terms.
- Vector retrieval improves recall for paraphrased employee questions.
- RRF reduces dependence on one retriever and keeps ranking explainable.
- Low-confidence refusal and citation checks turn failures into auditable cases for chunking, metadata, query rewriting, or policy coverage iteration.

## Question Type Breakdown

| Question Type | Cases | Hit@5 | MRR@5 | Citation Acc. | Refusal Acc. |
| --- | ---: | ---: | ---: | ---: | ---: |
| PDF-事实型 | 15 | 1.000 | 1.000 | 1.000 | 0.000 |
| PDF-例外条件型 | 15 | 0.933 | 0.933 | 0.933 | 0.000 |
| PDF-拒答型 | 2 | 0.000 | 0.000 | 0.500 | 1.000 |
| PDF-时限型 | 15 | 1.000 | 1.000 | 1.000 | 0.000 |
| PDF-材料型 | 15 | 0.933 | 0.933 | 0.933 | 0.000 |
| PDF-版本差异型 | 15 | 1.000 | 1.000 | 1.000 | 0.000 |
| PDF-跨文档引用型 | 15 | 1.000 | 1.000 | 1.000 | 0.000 |
| 合规类 | 30 | 1.000 | 1.000 | 1.000 | 0.000 |
| 同义改写类 | 30 | 0.733 | 0.733 | 0.733 | 0.000 |
| 时限类 | 30 | 0.933 | 0.933 | 0.933 | 0.000 |
| 材料类 | 30 | 0.867 | 0.867 | 0.867 | 0.000 |
| 模糊追问类 | 30 | 0.567 | 0.567 | 0.567 | 0.000 |
| 流程类 | 30 | 1.000 | 1.000 | 1.000 | 0.000 |
| 知识库外拒答类 | 22 | 0.000 | 0.000 | 0.909 | 1.000 |
| 系统入口类 | 30 | 1.000 | 1.000 | 1.000 | 0.000 |

## Top Failure Cases

- `hr_leave_2026_ambiguous_followup` [模糊追问类]: 请假申请材料不齐被退回后怎么处理，是否可以线下先办？ | expected=['HR-LEAVE-2026'] retrieved=['PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026']
- `hr_onboard_2026_materials` [材料类]: 办理入离职流程需要哪些材料？ | expected=['HR-ONBOARD-2026'] retrieved=['PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026']
- `hr_onboard_2026_sla` [时限类]: 入离职流程的审批时限或提前要求是什么？ | expected=['HR-ONBOARD-2026'] retrieved=['PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026']
- `hr_onboard_2026_ambiguous_followup` [模糊追问类]: 入离职流程材料不齐被退回后怎么处理，是否可以线下先办？ | expected=['HR-ONBOARD-2026'] retrieved=['PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026']
- `hr_perf_2026_materials` [材料类]: 办理绩效管理需要哪些材料？ | expected=['HR-PERF-2026'] retrieved=['PDF-HR-PERF-2026', 'PDF-HR-PERF-2026', 'PDF-HR-PERF-2026', 'PDF-HR-PERF-2026', 'PDF-HR-PERF-2026']
- `hr_perf_2026_ambiguous_followup` [模糊追问类]: 绩效管理材料不齐被退回后怎么处理，是否可以线下先办？ | expected=['HR-PERF-2026'] retrieved=['PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026']
- `hr_transfer_2026_ambiguous_followup` [模糊追问类]: 岗位变更材料不齐被退回后怎么处理，是否可以线下先办？ | expected=['HR-TRANSFER-2026'] retrieved=['PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026']
- `fin_exp_2026_paraphrase` [同义改写类]: 我想咨询差旅费相关事项，应该看哪份制度、走哪个入口？ | expected=['FIN-EXP-2026'] retrieved=['PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026']
- `fin_exp_2026_ambiguous_followup` [模糊追问类]: 报销申请材料不齐被退回后怎么处理，是否可以线下先办？ | expected=['FIN-EXP-2026'] retrieved=['PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026']
- `fin_budget_2026_ambiguous_followup` [模糊追问类]: 预算管理材料不齐被退回后怎么处理，是否可以线下先办？ | expected=['FIN-BUDGET-2026'] retrieved=['PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026']
