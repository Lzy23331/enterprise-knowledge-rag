# SmartOfficeRAG Experiment Report

## Iteration Summary

- Selected full-candidate version: V13-hard-query-construction `layer_hard_v13_query_construction`
- Quality leader in full candidate pool: V13-hard-query-construction `layer_hard_v13_query_construction`
- Answer Accuracy Proxy: 0.468 -> 0.468
- Hit@5: 0.676 -> 0.676
- Citation Accuracy: 0.698 -> 0.698
- Refusal Accuracy: 1.000 -> 1.000
- Selection rule: compare completed configs with a weighted quality score; 本次 full 实验已完成真实 embedding 配置；如有模型 skipped，应先修复模型缓存或网络后再引用结论。

## Experiment Matrix

| Version | Strategy | Chunk | Embedding | Retriever | Answer Acc. | Hit@5 | Citation | Refusal | p95 ms | Notes |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| V13-hard-query-construction | layer_hard_v13_query_construction | markdown_headers | BAAI/bge-small-zh-v1.5 | hybrid_rrf | 0.468 | 0.676 | 0.698 | 1.000 | 124.9 | Hard layer rule-based query construction: rewrite natural language into retrieval-oriented terms without hard filtering. |
| V15-hard-llm-query-construction | layer_hard_v15_llm_query_construction | markdown_headers | BAAI/bge-small-zh-v1.5 | hybrid_rrf | 0.454 | 0.468 | 0.516 | 1.000 | 2270.6 | Hard layer LLM query construction: use an OpenAI-compatible LLM to rewrite colloquial questions into retrieval-oriented queries. |
| V16-hard-llm-query-structured | layer_hard_v16_llm_query_structured | markdown_headers | BAAI/bge-small-zh-v1.5 | structured_hybrid_rrf | 0.403 | 0.523 | 0.563 | 1.000 | 2131.5 | Hard layer LLM query construction plus structured metadata boost after RRF. |
| V6-hard-bge-small | layer_hard_v6_bge_small | markdown_headers | BAAI/bge-small-zh-v1.5 | hybrid_rrf | 0.461 | 0.568 | 0.603 | 1.000 | 60.4 | Hard layer control using the current main RAG chain. |

## Layered Difficulty Matrix

| Version | Loaded Layers | Eval Layers | Cases | Answer | Citation | Conflict | Multi-hop | Table | Weighted Score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| V13-hard-query-construction | ["baseline", "medium", "hard"] | "hard" | 126 | 0.468 | 0.698 | 0.457 | 0.356 | 0.875 | 0.607 |
| V6-hard-bge-small | ["baseline", "medium", "hard"] | "hard" | 126 | 0.461 | 0.603 | 0.343 | 0.252 | 0.750 | 0.546 |

Selection rule: standard cases use Answer 30%, Citation 30%, Hit/MRR 20%, Refusal 15%, Latency 5%; hard cases use Citation 25%, Conflict 20%, Multi-hop 15%, Answer 20%, Refusal 15%, Latency 5%.

## Query Construction Findings

| Version | Retriever | Query Construction | Structured Boost | Answer | Citation | Conflict | Multi-hop | Table | p95 ms |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| V6-hard-bge-small | hybrid_rrf | False/rules | False | 0.461 | 0.603 | 0.343 | 0.252 | 0.750 | 60.4 |
| V13-hard-query-construction | hybrid_rrf | True/rules | False | 0.468 | 0.698 | 0.457 | 0.356 | 0.875 | 124.9 |
| V15-hard-llm-query-construction | hybrid_rrf | True/llm | False | 0.454 | 0.516 | 0.343 | 0.126 | 0.750 | 2270.6 |
| V16-hard-llm-query-structured | structured_hybrid_rrf | True/llm | True | 0.403 | 0.563 | 0.800 | 0.285 | 0.062 | 2131.5 |

Decision rule: query construction is useful only if it improves hard-case coverage without lowering citation, conflict handling, or latency beyond the business tolerance. It should remain an experiment unless it beats V6/V11 on hard weighted score.

## Embedding Model Findings

| Version | Model | Status | Dim | Load ms | Answer Acc. | Citation | p95 ms | Notes |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| V6-hard-bge-small | BAAI/bge-small-zh-v1.5 | completed | 512 | 40.8 | 0.461 | 0.603 | 60.4 | trust_remote_code=False; load_mode=local_cache |

Decision rule: MTEB/C-MTEB rank is only used to choose candidates. The project default changes only when a candidate improves enterprise-policy RAG metrics enough to justify latency, disk, memory, and dependency cost.

## Failure-driven Iteration Notes

### V13-hard-query-construction layer_hard_v13_query_construction

- Finding: Hard layer rule-based query construction: rewrite natural language into retrieval-oriented terms without hard filtering.
- Next optimization: Check whether query construction improves version, multi-hop, table and exception hard cases without hurting citations.
- Representative failures:
  - `colloquial_001` 我现在去北京出差，住酒店到底按2025的老标准还是2026的新标准啊？ | expected=['PDF-HARD-TRAVEL-2026'] | retrieved=['PDF-HARD-FIN-NOTICE-2026', 'PDF-HARD-FIN-NOTICE-2026', 'PDF-HARD-FIN-NOTICE-2026', 'PDF-HARD-FIN-NOTICE-2026', 'PDF-HARD-FIN-NOTICE-2026']
  - `colloquial_002` 差旅报销和那个4月份的新通知说法不一样，我按哪个来交材料？ | expected=['PDF-HARD-FIN-NOTICE-2026', 'PDF-MED-FIN-EXPENSE-2026'] | retrieved=['PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026']
  - `colloquial_003` 客户名单今天急着发给供应商，能不能先导出去，明天再补审批？ | expected=['PDF-HARD-DATA-EXPORT-2026'] | retrieved=['PDF-HARD-PROJECT-PROC-2026', 'PDF-HARD-PROJECT-PROC-2026', 'PDF-HARD-PROJECT-PROC-2026', 'PDF-HARD-PROJECT-PROC-2026', 'PDF-HARD-PROJECT-PROC-2026']

### V15-hard-llm-query-construction layer_hard_v15_llm_query_construction

- Finding: Hard layer LLM query construction: use an OpenAI-compatible LLM to rewrite colloquial questions into retrieval-oriented queries.
- Next optimization: Check whether LLM query construction improves colloquial, version-sensitive, multi-hop and exception hard cases without hurting citations.
- Representative failures:
  - `colloquial_001` 我现在去北京出差，住酒店到底按2025的老标准还是2026的新标准啊？ | expected=['PDF-HARD-TRAVEL-2026'] | retrieved=['PDF-HARD-TRAVEL-2025', 'PDF-HARD-TRAVEL-2025', 'PDF-HARD-TRAVEL-2025', 'PDF-HARD-TRAVEL-2025', 'PDF-HARD-TRAVEL-2025']
  - `colloquial_002` 差旅报销和那个4月份的新通知说法不一样，我按哪个来交材料？ | expected=['PDF-HARD-FIN-NOTICE-2026', 'PDF-MED-FIN-EXPENSE-2026'] | retrieved=['PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026']
  - `colloquial_003` 客户名单今天急着发给供应商，能不能先导出去，明天再补审批？ | expected=['PDF-HARD-DATA-EXPORT-2026'] | retrieved=['PDF-SEC-DATAEXPORT-2026', 'PDF-SEC-DATAEXPORT-2026', 'PDF-SEC-DATAEXPORT-2026', 'PDF-SEC-DATAEXPORT-2026', 'PDF-SEC-DATAEXPORT-2026']

### V16-hard-llm-query-structured layer_hard_v16_llm_query_structured

- Finding: Hard layer LLM query construction plus structured metadata boost after RRF.
- Next optimization: Check whether LLM-rewritten queries and structured metadata boost can improve hard cases, or whether the two signals over-amplify wrong metadata.
- Representative failures:
  - `colloquial_005` 三万多的采购，拆成两张单是不是就不用走高一级审批了？ | expected=['PDF-HARD-PROJECT-PROC-2026'] | retrieved=['PDF-HARD-FIN-NOTICE-2026', 'PDF-HARD-FIN-NOTICE-2026', 'PDF-HARD-FIN-NOTICE-2026', 'PDF-HARD-FIN-NOTICE-2026', 'PDF-HARD-FIN-NOTICE-2026']
  - `colloquial_007` 领导让我先把客户数据导出来给外包团队，后面合同再补，这样行吗？ | expected=['PDF-HARD-DATA-EXPORT-2026', 'PDF-MED-PROC-CONTRACT-2026'] | retrieved=['PDF-SEC-DATAEXPORT-2026', 'PDF-SEC-DATAEXPORT-2026', 'PDF-SEC-DATAEXPORT-2026', 'PDF-SEC-DATAEXPORT-2026', 'PDF-SEC-DATAEXPORT-2026']
  - `colloquial_009` 发票少了一张，但是金额不大，可以直接报吗？ | expected=['PDF-HARD-FIN-NOTICE-2026', 'PDF-MED-FIN-EXPENSE-2026'] | retrieved=['FIN-INVOICE-2026', 'FIN-INVOICE-2026', 'FIN-INVOICE-2026', 'FIN-INVOICE-2026', 'FIN-INVOICE-2026']

### V6-hard-bge-small layer_hard_v6_bge_small

- Finding: Hard layer control using the current main RAG chain.
- Next optimization: Baseline for hard benchmark; advanced strategies must beat it without hurting citation or refusal.
- Representative failures:
  - `colloquial_001` 我现在去北京出差，住酒店到底按2025的老标准还是2026的新标准啊？ | expected=['PDF-HARD-TRAVEL-2026'] | retrieved=['ADM-TRAVEL-2026', 'ADM-TRAVEL-2026', 'ADM-TRAVEL-2026', 'ADM-TRAVEL-2026', 'ADM-TRAVEL-2026']
  - `colloquial_002` 差旅报销和那个4月份的新通知说法不一样，我按哪个来交材料？ | expected=['PDF-HARD-FIN-NOTICE-2026', 'PDF-MED-FIN-EXPENSE-2026'] | retrieved=['PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026', 'PDF-FIN-EXP-2026']
  - `colloquial_003` 客户名单今天急着发给供应商，能不能先导出去，明天再补审批？ | expected=['PDF-HARD-DATA-EXPORT-2026'] | retrieved=['LEGAL-NDA-2026', 'LEGAL-NDA-2026', 'LEGAL-NDA-2026', 'LEGAL-NDA-2026', 'LEGAL-NDA-2026']

## Vector Store Selection

| Option | Fit for this project | Decision |
| --- | --- | --- |
| NumPy | Zero service dependency, easy to deploy on Streamlit, enough for hundreds/thousands of chunks. | Used for quick reproducible experiments. |
| FAISS | Fast local ANN/flat vector search, good for local portfolio demo and offline benchmark. | Used when full dependencies are available. |
| Chroma | Convenient local persistence and metadata APIs, heavier dependency surface than this demo needs. | Good next step, not required here. |
| Milvus | Production-scale vector DB with distributed deployment. | Overkill for personal demo; mention as enterprise option. |
| Elasticsearch | Strong BM25 and hybrid search ecosystem. | Useful if enterprise already has ES. |
| PGVector | Good when policies and metadata already live in Postgres. | Suitable for app integration, not needed for current local demo. |

## Resume-ready Story

基于 126 条制度问答评估集，从 `layer_hard_v13_query_construction` 出发，依次优化 chunk、BM25+向量混合检索、RRF 融合与低置信拒答；真实 embedding full 实验验证链路收益，使 Answer Accuracy Proxy 从 0.468 提升至 0.468，Citation Accuracy 从 0.698 提升至 0.698，Refusal Accuracy 从 1.000 提升至 1.000。
