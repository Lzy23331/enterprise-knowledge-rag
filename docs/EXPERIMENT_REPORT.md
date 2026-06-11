# SmartOfficeRAG Experiment Report

## Iteration Summary

- Selected full-candidate version: V6-bge-small `hybrid_bge_small_faiss_guarded`
- Quality leader in full candidate pool: V6-bge-small `hybrid_bge_small_faiss_guarded`
- Answer Accuracy Proxy: 0.000 -> 0.476
- Hit@5: 0.000 -> 0.903
- Citation Accuracy: 0.074 -> 0.901
- Refusal Accuracy: 0.000 -> 1.000
- Selection rule: compare completed configs with a weighted quality score; 本次 full 实验已完成真实 embedding 配置；如有模型 skipped，应先修复模型缓存或网络后再引用结论。

## Experiment Matrix

| Version | Strategy | Chunk | Embedding | Retriever | Answer Acc. | Hit@5 | Citation | Refusal | p95 ms | Notes |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| V0 | llm_direct_no_retrieval | none | none | llm_direct | 0.000 | 0.000 | 0.074 | 0.000 | 0.0 | 无知识库直答基线，用于暴露不可追溯和知识库外问题无法拒答的问题。 |
| V1 | keyword_whole_document | whole_document | none | keyword_only | 0.382 | 0.997 | 0.188 | 0.042 | 41.1 | 整文档粒度的关键词检索，验证最小知识库检索是否能命中文档。 |
| V2 | bm25_fixed_window | fixed_window | none | bm25_only | 0.508 | 1.000 | 0.458 | 0.042 | 1.9 | 固定长度滑窗分块 + BM25，测试简单 chunk 策略对召回和引用的影响。 |
| V2R | bm25_recursive_character_chunk | recursive_character | none | bm25_only | 0.553 | 0.983 | 0.474 | 0.083 | 2.0 | 递归字符分块 + BM25，对比固定窗口和制度结构分块的边界质量。 |
| V3 | bm25_header_chunk | markdown_headers | none | bm25_only | 0.416 | 0.973 | 0.794 | 0.042 | 11.1 | Markdown 标题层级分块 + BM25，保留制度章节结构，提高引用可解释性。 |
| V3S | bm25_semantic_chunk | semantic | none | bm25_only | 0.386 | 0.973 | 0.797 | 0.042 | 11.9 | 语义分块 + BM25，先用 bge-small 合并相邻语义单元，再测试关键词检索效果。 |
| V4-bge-base | vector_bge_base_zh_faiss | markdown_headers | BAAI/bge-base-zh-v1.5 | vector_only | 0.388 | 0.883 | 0.417 | 0.000 | 45.1 | BAAI/bge-base-zh-v1.5 + FAISS，测试更大中文 embedding 的召回收益和成本。 |
| V4-bge-small | vector_bge_small_zh_faiss | markdown_headers | BAAI/bge-small-zh-v1.5 | vector_only | 0.363 | 0.883 | 0.386 | 0.000 | 12.1 | BAAI/bge-small-zh-v1.5 + FAISS，测试中文轻量 embedding 的语义召回表现。 |
| V4-e5 | vector_multilingual_e5_faiss | markdown_headers | intfloat/multilingual-e5-small | vector_only | 0.362 | 0.847 | 0.406 | 0.000 | 22.2 | intfloat/multilingual-e5-small + FAISS，测试多语言 embedding 在中文制度问答中的表现。 |
| V4-recursive | vector_bge_small_recursive_faiss | recursive_character | BAAI/bge-small-zh-v1.5 | vector_only | 0.500 | 0.943 | 0.343 | 0.000 | 12.2 | 递归字符分块 + bge-small + FAISS，测试通用递归分块在纯向量召回中的表现。 |
| V4-semantic | vector_bge_small_semantic_faiss | semantic | BAAI/bge-small-zh-v1.5 | vector_only | 0.343 | 0.870 | 0.376 | 0.000 | 12.5 | 语义分块 + bge-small + FAISS，测试 semantic chunking 对纯向量召回的影响。 |
| V4 | vector_local_hashing_numpy | markdown_headers | local-hashing | vector_only | 0.221 | 0.783 | 0.332 | 0.000 | 0.2 | 本地 hashing embedding + NumPy 向量检索，用作可复现的轻量语义召回基线。 |
| V5 | bm25_vector_rrf_numpy | markdown_headers | local-hashing | hybrid_rrf | 0.440 | 0.903 | 0.836 | 0.000 | 10.5 | BM25 + local hashing 向量召回 + RRF 融合，验证混合检索收益。 |
| V6-bge-base | hybrid_bge_base_faiss_guarded | markdown_headers | BAAI/bge-base-zh-v1.5 | hybrid_rrf | 0.475 | 0.903 | 0.901 | 1.000 | 56.2 | BAAI/bge-base-zh-v1.5 + BM25 + RRF + 低置信拒答，测试更大中文 embedding 是否带来可观收益。 |
| V6-bge-small | hybrid_bge_small_faiss_guarded | markdown_headers | BAAI/bge-small-zh-v1.5 | hybrid_rrf | 0.476 | 0.903 | 0.901 | 1.000 | 28.9 | BAAI/bge-small-zh-v1.5 + BM25 + RRF + 低置信拒答，测试轻量中文 embedding 在最终链路中的表现。 |
| V6-e5 | hybrid_multilingual_e5_faiss_guarded | markdown_headers | intfloat/multilingual-e5-small | hybrid_rrf | 0.469 | 0.903 | 0.901 | 1.000 | 37.3 | intfloat/multilingual-e5-small + BM25 + RRF + 低置信拒答，测试多语言 embedding 在中文制度问答中的可用性。 |
| V6 | hybrid_rrf_with_refusal_gate | markdown_headers | local-hashing | hybrid_rrf | 0.440 | 0.903 | 0.901 | 1.000 | 14.4 | 混合检索 + 低置信拒答，用于降低知识库外问题误答。 |
| V6-recursive | hybrid_bge_small_recursive_guarded | recursive_character | BAAI/bge-small-zh-v1.5 | hybrid_rrf | 0.565 | 0.963 | 0.531 | 1.000 | 18.0 | 递归字符分块 + bge-small + BM25 + RRF + 低置信拒答，测试通用分块在最终链路中的可用性。 |
| V6-semantic | hybrid_bge_small_semantic_guarded | semantic | BAAI/bge-small-zh-v1.5 | hybrid_rrf | 0.479 | 0.903 | 0.901 | 1.000 | 25.4 | 语义分块 + bge-small + BM25 + RRF + 低置信拒答，测试 semantic chunking 在最终链路中的收益。 |
| V7 | query_rewrite_metadata_guarded | markdown_headers | local-hashing | hybrid_rrf | 0.445 | 0.900 | 0.898 | 1.000 | 13.8 | 候选增强链路：query rewrite + metadata hint + BM25/向量/RRF + 低置信拒答，用于验证规则增强是否继续提升。 |

## Chunking Strategy Findings

| Chunk Strategy | Representative Config | Chunks | Answer Acc. | Hit@5 | Citation | Finding |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Fixed window | V2 `bm25_fixed_window` | 118 | 0.508 | 1.000 | 0.458 | 粗粒度窗口召回强，但引用边界弱。 |
| Recursive character | V6-recursive `hybrid_bge_small_recursive_guarded` | 122 | 0.565 | 0.963 | 0.531 | 通用递归分块提升召回和答案关键词覆盖，但 citation 不适合制度条款溯源。 |
| Header/article-aware | V6-bge-small `hybrid_bge_small_faiss_guarded` | 833 | 0.476 | 0.903 | 0.901 | 制度结构分块的引用准确率最高，适合政策问答的可追溯要求。 |
| Semantic chunk | V6-semantic `hybrid_bge_small_semantic_guarded` | 706 | 0.479 | 0.903 | 0.901 | 语义合并略提升答案覆盖，citation 与结构分块持平，但引入额外 embedding 分块成本。 |

Conclusion: recursive chunking is valuable as a generic fallback and improves broad recall, but enterprise policy QA prioritizes traceable citations. The deployed strategy remains header/article-aware chunking with bge-small hybrid retrieval; semantic chunking is a credible enhancement candidate when answer completeness matters more than strict article-level citation.

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

### V2R bm25_recursive_character_chunk

- Finding: 递归字符分块 + BM25，对比固定窗口和制度结构分块的边界质量。
- Next optimization: 如果引用边界仍不如制度结构分块，则保留为通用文档 fallback，而不作为制度主策略。
- Representative failures:
  - `hr_leave_2026_process` 员工请假与休假管理制度的办理步骤是什么？ | expected=['HR-LEAVE-2026'] | retrieved=['HR-LEAVE-2026', 'HR-LEAVE-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026']
  - `hr_leave_2026_materials` 办理请假申请需要哪些材料？ | expected=['HR-LEAVE-2026'] | retrieved=['HR-LEAVE-2026', 'HR-LEAVE-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026']
  - `hr_leave_2026_sla` 请假申请的审批时限或提前要求是什么？ | expected=['HR-LEAVE-2026'] | retrieved=['HR-LEAVE-2026', 'HR-LEAVE-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026']

### V3 bm25_header_chunk

- Finding: Markdown 标题层级分块 + BM25，保留制度章节结构，提高引用可解释性。
- Next optimization: BM25 对精确词效果好，但同义问法和模糊问法仍需要语义召回。
- Representative failures:
  - `hr_leave_2026_ambiguous_followup` 请假申请材料不齐被退回后怎么处理，是否可以线下先办？ | expected=['HR-LEAVE-2026'] | retrieved=['PDF-HR-LEAVE-PDF-2026', 'HR-LEAVE-2026', 'PDF-PROC-PURCHASE-2026', 'PDF-SEC-INFO-2026', 'IT-CHANGE-2026']
  - `hr_onboard_2026_materials` 办理入离职流程需要哪些材料？ | expected=['HR-ONBOARD-2026'] | retrieved=['PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026']
  - `hr_onboard_2026_sla` 入离职流程的审批时限或提前要求是什么？ | expected=['HR-ONBOARD-2026'] | retrieved=['PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026']

### V3S bm25_semantic_chunk

- Finding: 语义分块 + BM25，先用 bge-small 合并相邻语义单元，再测试关键词检索效果。
- Next optimization: 观察语义合并是否改善答案完整性，或是否牺牲条款级 citation。
- Representative failures:
  - `hr_leave_2026_paraphrase` 我想咨询年假相关事项，应该看哪份制度、走哪个入口？ | expected=['HR-LEAVE-2026'] | retrieved=['HR-LEAVE-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026']
  - `hr_leave_2026_ambiguous_followup` 请假申请材料不齐被退回后怎么处理，是否可以线下先办？ | expected=['HR-LEAVE-2026'] | retrieved=['PDF-HR-LEAVE-PDF-2026', 'HR-LEAVE-2026', 'PDF-PROC-PURCHASE-2026', 'PDF-SEC-INFO-2026', 'IT-CHANGE-2026']
  - `hr_onboard_2026_materials` 办理入离职流程需要哪些材料？ | expected=['HR-ONBOARD-2026'] | retrieved=['PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026']

### V4-bge-base vector_bge_base_zh_faiss

- Finding: BAAI/bge-base-zh-v1.5 + FAISS，测试更大中文 embedding 的召回收益和成本。
- Next optimization: 如果收益不明显，优先选择更轻量模型降低部署成本。
- Representative failures:
  - `hr_leave_2026_materials` 办理请假申请需要哪些材料？ | expected=['HR-LEAVE-2026'] | retrieved=['PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-ATT-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026']
  - `hr_leave_2026_sla` 请假申请的审批时限或提前要求是什么？ | expected=['HR-LEAVE-2026'] | retrieved=['HR-LEAVE-2026', 'PDF-HR-LEAVE-PDF-2026', 'SEC-ACCESS-2026', 'FIN-PAYMENT-2026', 'HR-TRANSFER-2026']
  - `hr_leave_2026_risk` 员工请假与休假管理制度有哪些风险提示和注意事项？ | expected=['HR-LEAVE-2026'] | retrieved=['HR-LEAVE-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-ATT-2026']

### V4-bge-small vector_bge_small_zh_faiss

- Finding: BAAI/bge-small-zh-v1.5 + FAISS，测试中文轻量 embedding 的语义召回表现。
- Next optimization: 对比更大中文 embedding 和多语言 embedding 的召回质量与耗时。
- Representative failures:
  - `hr_leave_2026_process` 员工请假与休假管理制度的办理步骤是什么？ | expected=['HR-LEAVE-2026'] | retrieved=['HR-LEAVE-2026', 'PDF-HR-LEAVE-PDF-2026', 'HR-LEAVE-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-ATT-2026']
  - `hr_leave_2026_materials` 办理请假申请需要哪些材料？ | expected=['HR-LEAVE-2026'] | retrieved=['HR-LEAVE-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'IT-CHANGE-2026', 'HR-TRANSFER-2026']
  - `hr_leave_2026_sla` 请假申请的审批时限或提前要求是什么？ | expected=['HR-LEAVE-2026'] | retrieved=['HR-LEAVE-2026', 'PDF-HR-LEAVE-PDF-2026', 'FIN-PAYMENT-2026', 'SEC-ACCESS-2026', 'HR-LEAVE-2026']

### V4-e5 vector_multilingual_e5_faiss

- Finding: intfloat/multilingual-e5-small + FAISS，测试多语言 embedding 在中文制度问答中的表现。
- Next optimization: 结合准确率、延迟、模型大小和部署可用性选择 embedding。
- Representative failures:
  - `hr_leave_2026_process` 员工请假与休假管理制度的办理步骤是什么？ | expected=['HR-LEAVE-2026'] | retrieved=['HR-LEAVE-2026', 'HR-LEAVE-2026', 'HR-ONBOARD-2026', 'PDF-HR-ATT-2026', 'PDF-HR-LEAVE-PDF-2026']
  - `hr_leave_2026_materials` 办理请假申请需要哪些材料？ | expected=['HR-LEAVE-2026'] | retrieved=['PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'HR-LEAVE-2026', 'HR-LEAVE-2026']
  - `hr_leave_2026_sla` 请假申请的审批时限或提前要求是什么？ | expected=['HR-LEAVE-2026'] | retrieved=['HR-LEAVE-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'HR-LEAVE-2026', 'HR-TRANSFER-2026']

### V4-recursive vector_bge_small_recursive_faiss

- Finding: 递归字符分块 + bge-small + FAISS，测试通用递归分块在纯向量召回中的表现。
- Next optimization: 与 header/article-aware chunk 对比，判断通用分块是否会损失制度引用精度。
- Representative failures:
  - `hr_leave_2026_process` 员工请假与休假管理制度的办理步骤是什么？ | expected=['HR-LEAVE-2026'] | retrieved=['HR-LEAVE-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-ATT-2026']
  - `hr_leave_2026_materials` 办理请假申请需要哪些材料？ | expected=['HR-LEAVE-2026'] | retrieved=['HR-LEAVE-2026', 'FIN-ADV-2026', 'ADM-TRAVEL-2026', 'HR-TRAIN-2026', 'SEC-ACCESS-2026']
  - `hr_leave_2026_sla` 请假申请的审批时限或提前要求是什么？ | expected=['HR-LEAVE-2026'] | retrieved=['SEC-ACCESS-2026', 'HR-LEAVE-2026', 'FIN-PAYMENT-2026', 'HR-LEAVE-2026', 'IT-CHANGE-2026']

### V4-semantic vector_bge_small_semantic_faiss

- Finding: 语义分块 + bge-small + FAISS，测试 semantic chunking 对纯向量召回的影响。
- Next optimization: 与结构分块纯向量结果对比，判断语义合并是否提升自然语言召回。
- Representative failures:
  - `hr_leave_2026_process` 员工请假与休假管理制度的办理步骤是什么？ | expected=['HR-LEAVE-2026'] | retrieved=['HR-LEAVE-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-ATT-2026', 'PDF-HR-LEAVE-PDF-2026']
  - `hr_leave_2026_materials` 办理请假申请需要哪些材料？ | expected=['HR-LEAVE-2026'] | retrieved=['PDF-HR-LEAVE-PDF-2026', 'HR-LEAVE-2026', 'PROC-BIDDING-2026', 'IT-INCIDENT-2026', 'IT-CHANGE-2026']
  - `hr_leave_2026_sla` 请假申请的审批时限或提前要求是什么？ | expected=['HR-LEAVE-2026'] | retrieved=['HR-LEAVE-2026', 'FIN-PAYMENT-2026', 'SEC-ACCESS-2026', 'IT-ASSET-2026', 'ADM-MEETING-2026']

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

### V6-bge-base hybrid_bge_base_faiss_guarded

- Finding: BAAI/bge-base-zh-v1.5 + BM25 + RRF + 低置信拒答，测试更大中文 embedding 是否带来可观收益。
- Next optimization: 如果准确率收益有限但延迟/模型体积更高，则不选择 bge-base。
- Representative failures:
  - `hr_leave_2026_ambiguous_followup` 请假申请材料不齐被退回后怎么处理，是否可以线下先办？ | expected=['HR-LEAVE-2026'] | retrieved=['PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026']
  - `hr_onboard_2026_materials` 办理入离职流程需要哪些材料？ | expected=['HR-ONBOARD-2026'] | retrieved=['PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026']
  - `hr_onboard_2026_sla` 入离职流程的审批时限或提前要求是什么？ | expected=['HR-ONBOARD-2026'] | retrieved=['PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026']

### V6-bge-small hybrid_bge_small_faiss_guarded

- Finding: BAAI/bge-small-zh-v1.5 + BM25 + RRF + 低置信拒答，测试轻量中文 embedding 在最终链路中的表现。
- Next optimization: 与 bge-base/e5 的同类 hybrid 配置比较准确率、引用准确率、拒答准确率和延迟。
- Representative failures:
  - `hr_leave_2026_ambiguous_followup` 请假申请材料不齐被退回后怎么处理，是否可以线下先办？ | expected=['HR-LEAVE-2026'] | retrieved=['PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026']
  - `hr_onboard_2026_materials` 办理入离职流程需要哪些材料？ | expected=['HR-ONBOARD-2026'] | retrieved=['PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026']
  - `hr_onboard_2026_sla` 入离职流程的审批时限或提前要求是什么？ | expected=['HR-ONBOARD-2026'] | retrieved=['PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026', 'PDF-HR-ONOFF-2026']

### V6-e5 hybrid_multilingual_e5_faiss_guarded

- Finding: intfloat/multilingual-e5-small + BM25 + RRF + 低置信拒答，测试多语言 embedding 在中文制度问答中的可用性。
- Next optimization: 如果中文效果不如 bge 系列，则保留为多语言场景备选而非中文主链路。
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

### V6-recursive hybrid_bge_small_recursive_guarded

- Finding: 递归字符分块 + bge-small + BM25 + RRF + 低置信拒答，测试通用分块在最终链路中的可用性。
- Next optimization: 如果指标接近但 citation 较弱，继续保留结构分块作为制度文档主策略。
- Representative failures:
  - `hr_leave_2026_process` 员工请假与休假管理制度的办理步骤是什么？ | expected=['HR-LEAVE-2026'] | retrieved=['HR-LEAVE-2026', 'HR-LEAVE-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026']
  - `hr_leave_2026_materials` 办理请假申请需要哪些材料？ | expected=['HR-LEAVE-2026'] | retrieved=['HR-LEAVE-2026', 'HR-LEAVE-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026']
  - `hr_leave_2026_sla` 请假申请的审批时限或提前要求是什么？ | expected=['HR-LEAVE-2026'] | retrieved=['HR-LEAVE-2026', 'HR-LEAVE-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026', 'PDF-HR-LEAVE-PDF-2026']

### V6-semantic hybrid_bge_small_semantic_guarded

- Finding: 语义分块 + bge-small + BM25 + RRF + 低置信拒答，测试 semantic chunking 在最终链路中的收益。
- Next optimization: 如果答案完整性提升但 citation 下降，应说明制度类文档仍优先采用结构感知分块。
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

基于 324 条制度问答评估集，从 `llm_direct_no_retrieval` 出发，依次优化 chunk、BM25+向量混合检索、RRF 融合与低置信拒答；真实 embedding full 实验验证链路收益，使 Answer Accuracy Proxy 从 0.000 提升至 0.476，Citation Accuracy 从 0.074 提升至 0.901，Refusal Accuracy 从 0.000 提升至 1.000。
