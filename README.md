# SmartOfficeRAG: 企业员工服务知识库助手

SmartOfficeRAG 是一个面向求职展示的通用企业知识库 RAG 项目。它模拟企业内部 HR、财务、IT、信息安全、行政、法务、采购、内审和运营制度，帮助员工查询流程、材料、注意事项和引用来源。

## 项目亮点

- 30 篇自制模拟企业制度文档，避免隐私和版权风险。
- 支持 Markdown 加载、结构化 metadata、标题分块、向量索引。
- 支持 FAISS 向量检索 + 中文 BM25 + RRF + 文档感知 rerank。
- 支持部门、流程类型、风险等级等 metadata 过滤。
- 支持低置信度拒答和个人生活/福利类越界问题防误答。
- 回答固定包含结论、处理步骤、所需材料、注意事项和引用来源。
- 有 Streamlit Web Demo，适合面试展示。
- 没有 LLM API key 时会使用抽取式模板回答，便于本地调试。

## 当前评估结果

评估集位于 `data/eval/eval_cases.jsonl`，包含 172 条问题，其中 150 条知识库内问题、22 条知识库外拒答问题。运行 `evaluate.py` 会生成 `eval_report.json` 和 `eval_report.md`。

| 指标 | 当前结果 |
| --- | ---: |
| Hit@5 / Recall@5 | 1.000 / 1.000 |
| Context Precision@5 | 1.000 |
| MRR@5 / nDCG@5 | 1.000 / 1.000 |
| Citation Accuracy | 1.000 |
| Refusal Accuracy | 1.000 |
| Faithfulness Proxy | 1.000 |
| Latency p50 / p95 | 31.1 ms / 36.9 ms |

## 运行方式

```powershell
cd D:\projects\enterprise-knowledge-rag
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install --prefer-binary -r requirements.txt
```

如需接入 DeepSeek：

```powershell
$env:DEEPSEEK_API_KEY="你的 DeepSeek API Key"
```

启动 Web Demo：

```powershell
.\.venv\Scripts\python.exe run_web_demo.py
```

`run_web_demo.py` 默认启用向量索引，并使用项目内 Hugging Face 缓存。命令行测试也可以显式设置：

```powershell
$env:SMARTOFFICE_USE_VECTOR="1"
$env:HF_HOME="D:\projects\enterprise-knowledge-rag\.cache\huggingface"
.\.venv\Scripts\python.exe cli.py "新员工如何申请邮箱和 VPN 权限？"
```

项目会优先使用 `.venv` 中的 `faiss-cpu` 保存和加载 FAISS 索引。若当前环境没有 `faiss-cpu`，代码会自动使用本地 numpy 向量索引兜底，仍可验证向量检索 + 中文 BM25/关键词检索 + RRF 融合链路。

本项目默认 embedding 模型为 `BAAI/bge-small-zh-v1.5`。首次启用向量索引时需要下载该 Hugging Face 模型；如果模型已经存在于本机 Hugging Face 缓存，可使用离线模式：

```powershell
$env:HF_HUB_OFFLINE="1"
$env:TRANSFORMERS_OFFLINE="1"
$env:HF_HOME="D:\projects\enterprise-knowledge-rag\.cache\huggingface"
```

命令行快速测试：

```powershell
.\.venv\Scripts\python.exe cli.py "新员工如何申请邮箱和 VPN 权限？"
```

运行评估样例：

```powershell
.\.venv\Scripts\python.exe evaluate.py
```

## 公开部署

推荐使用 Streamlit Community Cloud：

1. 将本项目推送到 GitHub。
2. 在 Streamlit Community Cloud 新建应用。
3. 入口文件选择 `app.py`。
4. 如需 DeepSeek，在 Cloud 的 Secrets 中配置：

```toml
DEEPSEEK_API_KEY = "你的 DeepSeek API Key"
```

不要把 API Key 写入代码或提交到 GitHub。没有 API Key 时，应用会自动使用本地抽取式回答。详细说明见 `DEPLOYMENT.md`。

## 示例问题

- 员工请年假需要提前多久申请？
- 报销差旅费需要哪些材料？
- 新员工如何申请邮箱和 VPN 权限？
- 访问生产系统需要走什么审批？
- 涉及客户数据导出时需要注意什么？
- 如果知识库里没有这个制度怎么办？
