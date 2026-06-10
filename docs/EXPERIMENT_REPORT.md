# SmartOfficeRAG Experiment Report

## Iteration Summary

- Selected quick-regression version: V6 `hybrid_rrf_with_refusal_gate`
- Quality leader in completed candidate pool: V6 `hybrid_rrf_with_refusal_gate`
- Answer Accuracy Proxy: 0.000 -> 0.440
- Hit@5: 0.000 -> 0.903
- Citation Accuracy: 0.074 -> 0.901
- Refusal Accuracy: 0.000 -> 1.000
- Selection rule: compare completed configs with a weighted quality score; quick runs validate the chain, while final embedding selection requires successful `--full` experiments.

## Experiment Matrix

| Version | Strategy | Chunk | Embedding | Retriever | Answer Acc. | Hit@5 | Citation | Refusal | p95 ms | Notes |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| V0 | llm_direct_no_retrieval | none | none | llm_direct | 0.000 | 0.000 | 0.074 | 0.000 | 0.0 | 无知识库直答基线，用于暴露不可追溯和知识库外问题无法拒答的问题。 |
| V1 | keyword_whole_document | whole_document | none | keyword_only | 0.382 | 0.997 | 0.188 | 0.042 | 46.4 | 整文档粒度的关键词检索，验证最小知识库检索是否能命中文档。 |
| V2 | bm25_fixed_window | fixed_window | none | bm25_only | 0.508 | 1.000 | 0.458 | 0.042 | 2.1 | 固定长度滑窗分块 + BM25，测试简单 chunk 策略对召回和引用的影响。 |
| V3 | bm25_header_chunk | markdown_headers | none | bm25_only | 0.416 | 0.973 | 0.794 | 0.042 | 13.0 | Markdown 标题层级分块 + BM25，保留制度章节结构，提高引用可解释性。 |
| V4 | vector_local_hashing_numpy | markdown_headers | local-hashing | vector_only | 0.221 | 0.783 | 0.332 | 0.000 | 0.3 | 本地 hashing embedding + NumPy 向量检索，用作可复现的轻量语义召回基线。 |
| V5 | bm25_vector_rrf_numpy | markdown_headers | local-hashing | hybrid_rrf | 0.440 | 0.903 | 0.836 | 0.000 | 14.7 | BM25 + local hashing 向量召回 + RRF 融合，验证混合检索收益。 |
| V6 | hybrid_rrf_with_refusal_gate | markdown_headers | local-hashing | hybrid_rrf | 0.440 | 0.903 | 0.901 | 1.000 | 18.7 | 混合检索 + 低置信拒答，用于降低知识库外问题误答。 |
| V7 | query_rewrite_metadata_guarded | markdown_headers | local-hashing | hybrid_rrf | 0.445 | 0.900 | 0.898 | 1.000 | 20.3 | 候选增强链路：query rewrite + metadata hint + BM25/向量/RRF + 低置信拒答，用于验证规则增强是否继续提升。 |

## Failure-driven Iteration Notes

### V0 llm_direct_no_retrieval

- Finding: 无知识库直答基线，用于暴露不可追溯和知识库外问题无法拒答的问题。
- Next optimization: 引入企业制度知识库和最小检索链路，先解决答案来源不可追溯问题。
- Representative failures:
  - `hr_leave_2026_process` 员工请假与休假管理制度的办理步骤是什么？ | expected=['HR-LEAVE-2026'] | retrieved=[]
  - `hr_leave_2026_materials` 办理请假申请需要哪些材料？ | expected=['HR-LEAVE-2026'] | retrieved=[]
  - `hr_leave_2026_sla` 请假申请的审批时限或提前要求是什么？ | expected=['HR-LEAVE-2026'] | retrieved=[]

### V1 keyword_whole_document

- Finding: 整文档粒度的关键词检索，验证最小知识库检索是否能命中文档。
- Next optimization: 整文档会导致引用章节粗、上下文噪声大，因此需要测试更细的 chunk。
- Representative failures:
  - `hr_leave_2026_process` 员工请假与休假管理制度的办理步骤是什么？ | expected=['HR-LEAVE-2026'] | retrieved=['HR-LEAVE-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-ATT-2026', 'ADM-MEETING-2026', 'FIN-BUDGET-2026']
  - `hr_leave_2026_materials` 办理请假申请需要哪些材料？ | expected=['HR-LEAVE-2026'] | retrieved=['HR-LEAVE-2026', 'PDF-HR-LEAVE-PDF-2026', 'ADM-MEETING-2026', 'ADM-SEAL-2026', 'ADM-TRAVEL-2026']
  - `hr_leave_2026_sla` 请假申请的审批时限或提前要求是什么？ | expected=['HR-LEAVE-2026'] | retrieved=['HR-LEAVE-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-PROC-PURCHASE-2026', 'ADM-MEETING-2026', 'ADM-SEAL-2026']

### V2 bm25_fixed_window

- Finding: 固定长度滑窗分块 + BM25，测试简单 chunk 策略对召回和引用的影响。
- Next optimization: 固定窗口容易切断制度标题和章节语义，继续测试 Markdown header-aware chunk。
- Representative failures:
  - `hr_leave_2026_process` 员工请假与休假管理制度的办理步骤是什么？ | expected=['HR-LEAVE-2026'] | retrieved=['HR-LEAVE-2026', 'HR-LEAVE-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026']
  - `hr_leave_2026_materials` 办理请假申请需要哪些材料？ | expected=['HR-LEAVE-2026'] | retrieved=['HR-LEAVE-2026', 'HR-LEAVE-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026']
  - `hr_leave_2026_sla` 请假申请的审批时限或提前要求是什么？ | expected=['HR-LEAVE-2026'] | retrieved=['HR-LEAVE-2026', 'PDF-HR-LEAVE-PDF-2026', 'HR-LEAVE-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026']

### V3 bm25_header_chunk

- Finding: Markdown 标题层级分块 + BM25，保留制度章节结构，提高引用可解释性。
- Next optimization: BM25 对精确词效果好，但同义问法和模糊问法仍需要语义召回。
- Representative failures:
  - `hr_leave_2026_ambiguous_followup` 请假申请材料不齐被退回后怎么处理，是否可以线下先办？ | expected=['HR-LEAVE-2026'] | retrieved=['PDF-HR-LEAVE-PDF-2026', 'HR-LEAVE-2026', 'PDF-PROC-PURCHASE-2026', 'PDF-SEC-INFO-2026', 'IT-CHANGE-2026']
  - `hr_onboard_2026_materials` 办理入离职流程需要哪些材料？ | expected=['HR-ONBOARD-2026'] | retrieved=['PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026']
  - `hr_onboard_2026_sla` 入离职流程的审批时限或提前要求是什么？ | expected=['HR-ONBOARD-2026'] | retrieved=['PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026']

### V4 vector_local_hashing_numpy

- Finding: 本地 hashing embedding + NumPy 向量检索，用作可复现的轻量语义召回基线。
- Next optimization: 单向量召回对业务关键词不稳定，需要和 BM25 融合。
- Representative failures:
  - `hr_leave_2026_process` 员工请假与休假管理制度的办理步骤是什么？ | expected=['HR-LEAVE-2026'] | retrieved=['HR-LEAVE-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-HANDBOOK-2026', 'PDF-HR-LEAVE-PDF-2026']
  - `hr_leave_2026_materials` 办理请假申请需要哪些材料？ | expected=['HR-LEAVE-2026'] | retrieved=['IT-CHANGE-2026', 'FIN-BUDGET-2026', 'IT-INCIDENT-2026', 'IT-VPN-2026', 'AUDIT-EVIDENCE-2026']
  - `hr_leave_2026_sla` 请假申请的审批时限或提前要求是什么？ | expected=['HR-LEAVE-2026'] | retrieved=['IT-VPN-2026', 'SEC-ACCESS-2026', 'FIN-ADV-2026', 'LEGAL-CONTRACT-2026', 'HR-TRANSFER-2026']

### V5 bm25_vector_rrf_numpy

- Finding: BM25 + local hashing 向量召回 + RRF 融合，验证混合检索收益。
- Next optimization: 融合后仍可能召回知识库外相近制度，需要低置信拒答和业务规则。
- Representative failures:
  - `hr_leave_2026_ambiguous_followup` 请假申请材料不齐被退回后怎么处理，是否可以线下先办？ | expected=['HR-LEAVE-2026'] | retrieved=['PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026']
  - `hr_onboard_2026_materials` 办理入离职流程需要哪些材料？ | expected=['HR-ONBOARD-2026'] | retrieved=['PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026']
  - `hr_onboard_2026_sla` 入离职流程的审批时限或提前要求是什么？ | expected=['HR-ONBOARD-2026'] | retrieved=['PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026']

### V6 hybrid_rrf_with_refusal_gate

- Finding: 混合检索 + 低置信拒答，用于降低知识库外问题误答。
- Next optimization: 对员工自然语言中的部门、流程、系统入口做 query rewrite 和 metadata hint。
- Representative failures:
  - `hr_leave_2026_ambiguous_followup` 请假申请材料不齐被退回后怎么处理，是否可以线下先办？ | expected=['HR-LEAVE-2026'] | retrieved=['PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026']
  - `hr_onboard_2026_materials` 办理入离职流程需要哪些材料？ | expected=['HR-ONBOARD-2026'] | retrieved=['PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026']
  - `hr_onboard_2026_sla` 入离职流程的审批时限或提前要求是什么？ | expected=['HR-ONBOARD-2026'] | retrieved=['PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026']

### V7 query_rewrite_metadata_guarded

- Finding: 候选增强链路：query rewrite + metadata hint + BM25/向量/RRF + 低置信拒答，用于验证规则增强是否继续提升。
- Next optimization: 如果接入真实企业数据，应继续做权限过滤、人工反馈回流和 LLM judge 评估。
- Representative failures:
  - `hr_onboard_2026_materials` 办理入离职流程需要哪些材料？ | expected=['HR-ONBOARD-2026'] | retrieved=['PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026']
  - `hr_onboard_2026_sla` 入离职流程的审批时限或提前要求是什么？ | expected=['HR-ONBOARD-2026'] | retrieved=['PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026']
  - `hr_perf_2026_materials` 办理绩效管理需要哪些材料？ | expected=['HR-PERF-2026'] | retrieved=['PDF-HR-PERF-2026', 'PDF-HR-PERF-2026', 'PDF-HR-PERF-2026', 'PDF-HR-PERF-2026', 'PDF-HR-PERF-2026']

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

基于 324 条制度问答评估集，从 `llm_direct_no_retrieval` 出发，依次优化 chunk、BM25+向量混合检索、RRF 融合与低置信拒答；当前 quick 回归使用轻量向量 baseline 验证链路收益，使 Answer Accuracy Proxy 从 0.000 提升至 0.440，Citation Accuracy 从 0.074 提升至 0.901，Refusal Accuracy 从 0.000 提升至 1.000。真实 embedding 选型需以 `run_experiments.py --full` 成功完成 bge-small、bge-base 和 multilingual-e5 对比后的结果为准。
