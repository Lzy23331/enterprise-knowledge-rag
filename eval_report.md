# SmartOfficeRAG Evaluation Report

## Overall Metrics

- Total cases: 498
- Retrieval cases: 459
- Refusal cases: 39
- Hit@1 / Hit@3 / Hit@5: 0.832 / 0.832 / 0.832
- Recall@5: 0.798
- Context Precision@5: 0.832
- MRR@5: 0.832
- nDCG@5: 0.805
- Citation Accuracy: 0.835
- Refusal Accuracy: 1.000
- Faithfulness Proxy: 0.845
- Answer Correctness Proxy: 0.477
- Latency p50 / p95: 61.9 ms / 93.3 ms

## Metrics Notes

- Retrieval metrics use expected document IDs from all `data/eval/*.jsonl` files.
- Faithfulness and answer correctness are deterministic proxies for local evaluation.
- For rigorous judge-based scoring, add RAGAS/DeepEval-style LLM-as-a-judge on the same cases.

## Retrieval Strategy Comparison

| Strategy | Hit@5 | MRR@5 | Citation Acc. | Refusal Acc. | p50 Latency | p95 Latency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| llm_direct | 0.000 | 0.000 | 0.078 | 0.000 | 0.0 ms | 0.0 ms |
| bm25_only | 0.941 | 0.886 | 0.784 | 1.000 | 21.3 ms | 36.1 ms |
| vector_only | 0.874 | 0.732 | 0.457 | 1.000 | 25.7 ms | 44.7 ms |
| hybrid_rrf | 0.832 | 0.832 | 0.835 | 1.000 | 61.9 ms | 93.3 ms |

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
| 中等-事实型 | 6 | 1.000 | 1.000 | 1.000 | 0.000 |
| 中等-例外条件 | 6 | 1.000 | 1.000 | 1.000 | 0.000 |
| 中等-材料型 | 6 | 1.000 | 1.000 | 1.000 | 0.000 |
| 中等-流程型 | 6 | 1.000 | 1.000 | 1.000 | 0.000 |
| 中等-表格定位 | 6 | 1.000 | 1.000 | 1.000 | 0.000 |
| 中等-跨文档引用 | 6 | 1.000 | 1.000 | 1.000 | 0.000 |
| 中等-金额阈值 | 6 | 1.000 | 1.000 | 1.000 | 0.000 |
| 中等-风险合规 | 6 | 1.000 | 1.000 | 1.000 | 0.000 |
| 口语化-优先级 | 2 | 0.000 | 0.000 | 0.000 | 0.000 |
| 口语化-例外条件 | 6 | 0.000 | 0.000 | 0.000 | 0.000 |
| 口语化-安全合规 | 3 | 0.000 | 0.000 | 0.000 | 0.000 |
| 口语化-拒答 | 3 | 0.000 | 0.000 | 0.333 | 1.000 |
| 口语化-流程型 | 2 | 0.000 | 0.000 | 0.000 | 0.000 |
| 口语化-版本冲突 | 2 | 0.000 | 0.000 | 0.000 | 0.000 |
| 口语化-表格定位 | 2 | 0.000 | 0.000 | 0.000 | 0.000 |
| 口语化-诊断型 | 1 | 0.000 | 0.000 | 0.000 | 0.000 |
| 口语化-跨文档 | 7 | 0.429 | 0.429 | 0.429 | 0.000 |
| 口语化-金额阈值 | 2 | 0.000 | 0.000 | 0.000 | 0.000 |
| 合规类 | 30 | 1.000 | 1.000 | 1.000 | 0.000 |
| 同义改写类 | 30 | 0.733 | 0.733 | 0.733 | 0.000 |
| 困难-优先级 | 12 | 1.000 | 1.000 | 1.000 | 0.000 |
| 困难-例外条件 | 12 | 0.000 | 0.000 | 0.000 | 0.000 |
| 困难-模糊口语 | 12 | 1.000 | 1.000 | 1.000 | 0.000 |
| 困难-版本冲突 | 12 | 0.000 | 0.000 | 0.000 | 0.000 |
| 困难-相似条款 | 12 | 1.000 | 1.000 | 1.000 | 0.000 |
| 困难-知识库外拒答 | 12 | 0.000 | 0.000 | 1.000 | 1.000 |
| 困难-表格金额 | 12 | 1.000 | 1.000 | 1.000 | 0.000 |
| 困难-跨文档 | 12 | 1.000 | 1.000 | 1.000 | 0.000 |
| 时限类 | 30 | 0.933 | 0.933 | 0.933 | 0.000 |
| 材料类 | 30 | 0.867 | 0.867 | 0.867 | 0.000 |
| 模糊追问类 | 30 | 0.567 | 0.567 | 0.567 | 0.000 |
| 流程类 | 30 | 1.000 | 1.000 | 1.000 | 0.000 |
| 知识库外拒答类 | 22 | 0.000 | 0.000 | 0.909 | 1.000 |
| 系统入口类 | 30 | 1.000 | 1.000 | 1.000 | 0.000 |

## Top Failure Cases

- `colloquial_001` [口语化-版本冲突]: 我现在去北京出差，住酒店到底按2025的老标准还是2026的新标准啊？ | expected=['PDF-HARD-TRAVEL-2026'] retrieved=['ADM-TRAVEL-2026', 'ADM-TRAVEL-2026', 'ADM-TRAVEL-2026', 'ADM-TRAVEL-2026', 'ADM-TRAVEL-2026']
- `colloquial_002` [口语化-优先级]: 差旅报销和那个4月份的新通知说法不一样，我按哪个来交材料？ | expected=['PDF-HARD-FIN-NOTICE-2026', 'PDF-MED-FIN-EXPENSE-2026'] retrieved=['PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026']
- `colloquial_003` [口语化-例外条件]: 客户名单今天急着发给供应商，能不能先导出去，明天再补审批？ | expected=['PDF-HARD-DATA-EXPORT-2026'] retrieved=['LEGAL-NDA-2026', 'LEGAL-NDA-2026', 'LEGAL-NDA-2026', 'LEGAL-NDA-2026', 'LEGAL-NDA-2026']
- `colloquial_005` [口语化-金额阈值]: 三万多的采购，拆成两张单是不是就不用走高一级审批了？ | expected=['PDF-HARD-PROJECT-PROC-2026'] retrieved=['PDF-PROC-PURCHASE-2026', 'PDF-PROC-PURCHASE-2026', 'PDF-PROC-PURCHASE-2026', 'PDF-PROC-PURCHASE-2026', 'PDF-PROC-PURCHASE-2026']
- `colloquial_007` [口语化-跨文档]: 领导让我先把客户数据导出来给外包团队，后面合同再补，这样行吗？ | expected=['PDF-HARD-DATA-EXPORT-2026', 'PDF-MED-PROC-CONTRACT-2026'] retrieved=['PDF-SEC-DATAEXPORT-2026', 'PDF-SEC-DATAEXPORT-2026', 'PDF-SEC-DATAEXPORT-2026', 'PDF-SEC-DATAEXPORT-2026', 'PDF-SEC-DATAEXPORT-2026']
- `colloquial_008` [口语化-表格定位]: 今年的住宿标准涨了吗？我报销酒店费按哪个表看？ | expected=['PDF-HARD-TRAVEL-2026'] retrieved=['PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026']
- `colloquial_009` [口语化-例外条件]: 发票少了一张，但是金额不大，可以直接报吗？ | expected=['PDF-HARD-FIN-NOTICE-2026', 'PDF-MED-FIN-EXPENSE-2026'] retrieved=['PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026']
- `colloquial_011` [口语化-流程型]: 临时加班打车回家，这种交通费能不能走报销？ | expected=['PDF-MED-FIN-EXPENSE-2026', 'PDF-HARD-FIN-NOTICE-2026'] retrieved=['FIN-EXP-2026', 'FIN-EXP-2026', 'FIN-EXP-2026', 'FIN-EXP-2026', 'FIN-EXP-2026']
- `colloquial_012` [口语化-安全合规]: 远程办公的时候能不能把文件先下载到自己电脑，处理完再删？ | expected=['PDF-HARD-REMOTE-SEC-2026', 'PDF-HARD-DATA-EXPORT-2026'] retrieved=['PDF-HR-REMOTE-2026', 'PDF-HR-REMOTE-2026', 'PDF-HR-REMOTE-2026', 'PDF-HR-REMOTE-2026', 'PDF-HR-REMOTE-2026']
- `colloquial_013` [口语化-例外条件]: 采购供应商以前合作过，是不是就不用再比价了？ | expected=['PDF-MED-PROC-CONTRACT-2026', 'PDF-HARD-PROJECT-PROC-2026'] retrieved=['PDF-PROC-PURCHASE-2026', 'PDF-PROC-PURCHASE-2026', 'PDF-PROC-PURCHASE-2026', 'PDF-PROC-PURCHASE-2026', 'PDF-PROC-PURCHASE-2026']
