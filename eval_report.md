# SmartOfficeRAG Evaluation Report

## Overall Metrics

- Total cases: 232
- Retrieval cases: 210
- Refusal cases: 22
- Hit@1 / Hit@3 / Hit@5: 0.957 / 0.957 / 0.957
- Recall@5: 0.957
- Context Precision@5: 0.957
- MRR@5: 0.957
- nDCG@5: 0.957
- Citation Accuracy: 0.953
- Refusal Accuracy: 1.000
- Faithfulness Proxy: 0.961
- Answer Correctness Proxy: 0.525
- Latency p50 / p95: 6.4 ms / 9.4 ms

## Metrics Notes

- Retrieval metrics use expected document IDs from `data/eval/eval_cases.jsonl`.
- Faithfulness and answer correctness are deterministic proxies for local evaluation.
- For rigorous judge-based scoring, add RAGAS/DeepEval-style LLM-as-a-judge on the same cases.

## Retrieval Strategy Comparison

| Strategy | Hit@5 | MRR@5 | Citation Acc. | Refusal Acc. | p50 Latency | p95 Latency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| llm_direct | 0.000 | 0.000 | 0.095 | 0.000 | 0.0 ms | 0.0 ms |
| bm25_only | 0.857 | 0.855 | 0.822 | 1.000 | 5.5 ms | 8.7 ms |
| vector_only | 0.614 | 0.581 | 0.247 | 1.000 | 1.1 ms | 1.9 ms |
| hybrid_rrf | 0.957 | 0.957 | 0.953 | 1.000 | 6.4 ms | 9.4 ms |

## Why Hybrid RAG

- BM25 is robust for exact policy names, form IDs, and business terms.
- Vector retrieval improves recall for paraphrased employee questions.
- RRF reduces dependence on one retriever and keeps ranking explainable.
- Low-confidence refusal and citation checks turn failures into auditable cases for chunking, metadata, query rewriting, or policy coverage iteration.

## Question Type Breakdown

| Question Type | Cases | Hit@5 | MRR@5 | Citation Acc. | Refusal Acc. |
| --- | ---: | ---: | ---: | ---: | ---: |
| 合规类 | 30 | 1.000 | 1.000 | 1.000 | 0.000 |
| 同义改写类 | 30 | 0.967 | 0.967 | 0.967 | 0.000 |
| 时限类 | 30 | 1.000 | 1.000 | 1.000 | 0.000 |
| 材料类 | 30 | 1.000 | 1.000 | 1.000 | 0.000 |
| 模糊追问类 | 30 | 0.733 | 0.733 | 0.733 | 0.000 |
| 流程类 | 30 | 1.000 | 1.000 | 1.000 | 0.000 |
| 知识库外拒答类 | 22 | 0.000 | 0.000 | 0.909 | 1.000 |
| 系统入口类 | 30 | 1.000 | 1.000 | 1.000 | 0.000 |

## Top Failure Cases

- `hr_leave_2026_ambiguous_followup` [模糊追问类]: 请假申请材料不齐被退回后怎么处理，是否可以线下先办？ | expected=['HR-LEAVE-2026'] retrieved=['OPS-CS-QUALITY-2026', 'OPS-CS-QUALITY-2026', 'OPS-CS-QUALITY-2026', 'OPS-CS-QUALITY-2026', 'OPS-CS-QUALITY-2026']
- `hr_transfer_2026_ambiguous_followup` [模糊追问类]: 岗位变更材料不齐被退回后怎么处理，是否可以线下先办？ | expected=['HR-TRANSFER-2026'] retrieved=['OPS-CS-QUALITY-2026', 'OPS-CS-QUALITY-2026', 'OPS-CS-QUALITY-2026', 'OPS-CS-QUALITY-2026', 'OPS-CS-QUALITY-2026']
- `fin_budget_2026_ambiguous_followup` [模糊追问类]: 预算管理材料不齐被退回后怎么处理，是否可以线下先办？ | expected=['FIN-BUDGET-2026'] retrieved=['OPS-CS-QUALITY-2026', 'OPS-CS-QUALITY-2026', 'OPS-CS-QUALITY-2026', 'OPS-CS-QUALITY-2026', 'OPS-CS-QUALITY-2026']
- `it_perm_2026_paraphrase` [同义改写类]: 我想咨询邮箱相关事项，应该看哪份制度、走哪个入口？ | expected=['IT-PERM-2026'] retrieved=['IT-VPN-2026', 'IT-VPN-2026', 'IT-VPN-2026', 'IT-VPN-2026', 'IT-VPN-2026']
- `it_vpn_2026_ambiguous_followup` [模糊追问类]: IT 服务材料不齐被退回后怎么处理，是否可以线下先办？ | expected=['IT-VPN-2026'] retrieved=['OPS-CS-QUALITY-2026', 'OPS-CS-QUALITY-2026', 'OPS-CS-QUALITY-2026', 'OPS-CS-QUALITY-2026', 'OPS-CS-QUALITY-2026']
- `it_change_2026_ambiguous_followup` [模糊追问类]: 变更申请材料不齐被退回后怎么处理，是否可以线下先办？ | expected=['IT-CHANGE-2026'] retrieved=['OPS-CS-QUALITY-2026', 'OPS-CS-QUALITY-2026', 'OPS-CS-QUALITY-2026', 'OPS-CS-QUALITY-2026', 'OPS-CS-QUALITY-2026']
- `sec_data_2026_ambiguous_followup` [模糊追问类]: 数据合规材料不齐被退回后怎么处理，是否可以线下先办？ | expected=['SEC-DATA-2026'] retrieved=['IT-OSS-2026', 'IT-OSS-2026', 'IT-OSS-2026', 'IT-OSS-2026', 'IT-OSS-2026']
- `adm_seal_2026_ambiguous_followup` [模糊追问类]: 印章申请材料不齐被退回后怎么处理，是否可以线下先办？ | expected=['ADM-SEAL-2026'] retrieved=['OPS-CS-QUALITY-2026', 'OPS-CS-QUALITY-2026', 'OPS-CS-QUALITY-2026', 'OPS-CS-QUALITY-2026', 'OPS-CS-QUALITY-2026']
- `audit_evidence_2026_ambiguous_followup` [模糊追问类]: 监管报送材料不齐被退回后怎么处理，是否可以线下先办？ | expected=['AUDIT-EVIDENCE-2026'] retrieved=['OPS-CS-QUALITY-2026', 'OPS-CS-QUALITY-2026', 'OPS-CS-QUALITY-2026', 'OPS-CS-QUALITY-2026', 'OPS-CS-QUALITY-2026']
- `refuse_05` [知识库外拒答类]: 员工个人所得税专项扣除怎么填最省税？ | expected=[] retrieved=['HR-TRAIN-2026', 'HR-TRAIN-2026', 'HR-TRAIN-2026', 'HR-TRAIN-2026', 'HR-TRAIN-2026']
