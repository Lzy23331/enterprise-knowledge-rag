# SmartOfficeRAG 项目教程与开发说明

这份文档面向项目作者、面试讲解者和后续维护者，目标是把 SmartOfficeRAG 从“能跑起来”讲清楚到“知道每个文件为什么存在、RAG 每一步怎么实现、评估结果怎么解释”。

项目根目录：

```text
D:\projects\enterprise-knowledge-rag
```

一句话概括：SmartOfficeRAG 是一个企业员工服务知识库 RAG 助手。它用 30 篇模拟企业制度文档作为知识库，使用 Markdown 解析、metadata 提取、标题分块、FAISS 向量检索、中文 BM25、RRF 融合排序、文档感知 rerank、来源引用、低置信度拒答和评估报表，最后通过 Streamlit 提供 Web Demo。

---

## 1. 项目整体目录

当前项目主要分为 8 类内容：

```text
enterprise-knowledge-rag/
├── app.py
├── cli.py
├── evaluate.py
├── run_web_demo.py
├── requirements.txt
├── runtime.txt
├── README.md
├── DEPLOYMENT.md
├── eval_report.json
├── eval_report.md
├── data/
│   ├── policies/
│   └── eval/
├── smart_office_rag/
├── scripts/
├── docs/
├── vector_index/        # 本地生成，Git 忽略
├── .cache/              # 模型缓存，Git 忽略
└── .venv/               # 虚拟环境，Git 忽略
```

核心理解：

- `data/policies/` 是被检索的企业制度知识库。
- `smart_office_rag/` 是 RAG 核心代码。
- `app.py` 是 Web 页面入口。
- `evaluate.py` 是评估系统入口。
- `data/eval/eval_cases.jsonl` 是评估问题集。
- `eval_report.json` 和 `eval_report.md` 是当前版本的评估结果。
- `scripts/generate_enterprise_dataset.py` 是生成模拟企业制度和评估集的脚本。
- `vector_index/` 是 FAISS 索引缓存，本地运行时生成，不提交 Git。
- `.cache/huggingface/` 是 embedding 模型缓存，不提交 Git。

---

## 2. 根目录文件说明

### 2.1 `app.py`

这是 Streamlit Web Demo 的入口文件，也是部署到 Streamlit Community Cloud 时推荐填写的入口。

它负责：

- 初始化页面标题、布局和侧边栏。
- 调用 `EnterpriseKnowledgeRAG` 加载知识库。
- 显示知识库概览：制度文档数、chunk 数、评估问题数、Hit@5、拒答准确率。
- 提供部门、流程类型、风险等级 metadata 过滤器。
- 提供分组示例问题。
- 接收用户问题。
- 调用 `rag.ask(question, filters=filters)` 获取回答。
- 展示回答、引用来源和检索片段。

面试讲解时可以这样说：

> `app.py` 只负责交互展示，不直接写检索算法。真正的 RAG 流程封装在 `smart_office_rag.pipeline.EnterpriseKnowledgeRAG` 里，页面只调用统一的 `ask()` 接口。

### 2.2 `cli.py`

这是命令行测试入口。

用法：

```powershell
.\.venv\Scripts\python.exe cli.py "绩效申诉需要在多久内提交？"
```

它适合：

- 快速验证检索和生成是否正常。
- 不启动 Web 页面时调试 RAG。
- 排查 Streamlit 缓存或页面进程问题。

### 2.3 `evaluate.py`

这是评估系统入口。它读取 `data/eval/eval_cases.jsonl`，逐条调用 RAG 系统，然后生成指标报告。

输出：

```text
eval_report.json
eval_report.md
```

当前评估集：

- 总计 172 条问题。
- 150 条知识库内问题。
- 22 条知识库外拒答问题。

当前指标：

- Hit@1/3/5
- Recall@5
- Context Precision@5
- MRR@5
- nDCG@5
- Citation Accuracy
- Refusal Accuracy
- Faithfulness Proxy
- Answer Correctness Proxy
- Latency p50/p95

### 2.4 `run_web_demo.py`

这是本地启动 Streamlit 的便利脚本。

它做两件事：

- 默认设置 `SMARTOFFICE_USE_VECTOR=1`，启用向量检索。
- 默认设置 `HF_HOME=.cache/huggingface`，让模型缓存放在项目目录下。

本地启动：

```powershell
.\.venv\Scripts\python.exe run_web_demo.py
```

部署到云端时，推荐入口仍然是 `app.py`。

### 2.5 `requirements.txt`

项目依赖文件。主要依赖包括：

- `streamlit`：Web Demo。
- `openai`：调用 DeepSeek / OpenAI-compatible Chat Completions API。
- `sentence-transformers`：本地可选，用于加载中文 embedding 模型；云端公开 Demo 默认使用本地哈希向量，避免重依赖导致部署超时。
- `faiss-cpu`：向量数据库。
- `rank_bm25`：BM25 稀疏检索。
- `sentence-transformers`：embedding 模型加载。
- `openai`：兼容 DeepSeek API 的客户端。
- `numpy`：本地向量索引兜底和数值计算。

### 2.6 `runtime.txt`

云端部署 Python 版本声明：

```text
python-3.12
```

### 2.7 `README.md`

项目主页说明，适合 GitHub 展示。内容包括：

- 项目定位。
- 项目亮点。
- 当前评估结果。
- 本地运行方式。
- 公开部署方式。
- 示例问题。

### 2.8 `DEPLOYMENT.md`

部署说明文档，重点讲 Streamlit Community Cloud：

- GitHub 仓库部署。
- 入口文件 `app.py`。
- DeepSeek API Key 放 Secrets。
- 哪些文件不应该提交。

### 2.9 `eval_report.json` 和 `eval_report.md`

当前版本的评估结果。

- `eval_report.json`：结构化详细报告，给程序和页面读取。
- `eval_report.md`：Markdown 摘要，方便人看和面试展示。

---

## 3. `data/`：知识库与评估集

### 3.1 `data/policies/`

这里是 RAG 的检索知识库。每个 `.md` 文件是一篇模拟企业制度。

当前共有 30 篇，覆盖：

- HR：请假、入离职、培训、绩效、转岗。
- Finance：报销、备用金、发票、预算、付款。
- IT：权限、VPN、资产、故障、生产变更。
- Security：数据安全、访客、安全事件、数据分级、审计复核。
- Admin：会议室、印章、出差支持。
- Legal：合同评审、保密协议。
- Procurement：供应商准入、采购招投标。
- Audit：审计整改、监管报送。
- Operations：业务连续性演练。

每篇制度的结构基本一致：

```markdown
---
doc_id: HR-PERF-2026
title: 绩效目标与考核申诉流程
department: HR
process_type: 绩效管理
risk_level: 中
doc_type: 制度
version: v2026.1
effective_date: 2026-01-01
updated_at: 2026-05-30
owner: 人力资源部
system: 绩效系统
form_id: HR-F-004
approval_sla: 绩效申诉须在结果发布后三个工作日内提交
---

# 绩效目标与考核申诉流程

## 适用对象
...

## 办理条件
...

## 办理步骤
...

## 所需材料
...

## 审批 SLA 与例外流程
...

## 注意事项
...

## 常见问题
...
```

上方 `---` 包围的部分叫 front matter。它不是正文，而是结构化 metadata。

这些 metadata 的作用：

- `doc_id`：唯一文档 ID，用于评估和引用。
- `title`：制度标题，用于展示和标题 boost。
- `department`：部门过滤。
- `process_type`：流程类型过滤和问题匹配。
- `risk_level`：风险等级过滤。
- `owner`：制度负责人。
- `system`：办理系统入口。
- `form_id`：表单编号。
- `approval_sla`：审批时限。

### 3.2 `data/eval/eval_cases.jsonl`

这是评估数据集，每行一条 JSON。

字段固定为：

```json
{
  "id": "hr_perf_2026_sla",
  "question": "绩效管理的审批时限或提前要求是什么？",
  "expected_doc_ids": ["HR-PERF-2026"],
  "expected_sections": ["审批 SLA 与例外流程"],
  "reference_answer": "标准时限或提前要求为：绩效申诉须在结果发布后三个工作日内提交；材料缺失时从补齐后重新计算。",
  "question_type": "时限类",
  "department": "HR",
  "should_refuse": false
}
```

字段解释：

- `id`：评估样例 ID。
- `question`：用户问题。
- `expected_doc_ids`：期望召回的制度文档。
- `expected_sections`：期望命中的章节。
- `reference_answer`：参考答案，用于答案正确性 proxy。
- `question_type`：问题类型，如流程类、材料类、时限类。
- `department`：所属部门。
- `should_refuse`：是否应拒答。

---

## 4. `smart_office_rag/`：RAG 核心代码

### 4.1 `config.py`

集中管理 RAG 配置。

关键配置：

```python
data_path = PROJECT_ROOT / "data" / "policies"
index_path = PROJECT_ROOT / "vector_index"
embedding_model = "BAAI/bge-small-zh-v1.5"
top_k = 5
llm_model = "deepseek-chat"
llm_base_url = "https://api.deepseek.com"
use_vector_index = os.getenv("SMARTOFFICE_USE_VECTOR", "1") == "1"
```

含义：

- 知识库路径是 `data/policies/`。
- FAISS 索引保存在 `vector_index/`。
- embedding 模型是中文向量模型 `BAAI/bge-small-zh-v1.5`。
- 默认检索 top-5。
- 默认使用 DeepSeek 的 OpenAI-compatible 接口。
- 默认启用向量检索。

### 4.2 `documents.py`

负责文档加载、metadata 解析和分块。

核心类：

```python
PolicyDocumentLoader
```

主要方法：

- `load_parent_documents()`
- `split_documents()`

#### 4.2.1 Markdown 加载

`load_parent_documents()` 会遍历：

```text
data/policies/*.md
```

然后读取每篇 Markdown。

#### 4.2.2 Front matter metadata 提取

代码用正则：

```python
FRONT_MATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
```

它会把 Markdown 顶部的 metadata 解析成字典。

例如：

```yaml
doc_id: HR-PERF-2026
department: HR
process_type: 绩效管理
```

会进入：

```python
Document.metadata
```

#### 4.2.3 文本分块策略

项目使用：

```python
MarkdownHeaderTextSplitter
```

标题层级：

```python
("#", "section_1")
("##", "section_2")
("###", "section_3")
```

也就是说，文本不是按固定 token 数硬切，而是按 Markdown 标题结构切。

为什么这样做：

- 企业制度文档天然按章节组织。
- `办理步骤`、`所需材料`、`审批 SLA`、`注意事项` 本身就是语义完整单元。
- 按标题切块可以保留章节引用，方便回答时给出来源。

每个 chunk 会添加：

```python
chunk_id
chunk_index
section
citation
chunk_size
```

例如：

```text
citation = 《绩效目标与考核申诉流程》审批 SLA 与例外流程
```

这就是 Web 页面“引用来源”的基础。

### 4.3 `indexing.py`

负责向量索引构建和加载。

核心类：

```python
VectorIndex
```

使用 embedding：

```python
HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-zh-v1.5",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)
```

#### 4.3.1 Embedding 模型

模型：

```text
BAAI/bge-small-zh-v1.5
```

选择理由：

- 中文效果较好。
- 模型相对小，适合本地和 Streamlit Cloud。
- 输出向量维度为 512。

#### 4.3.2 FAISS 向量库

优先使用：

```python
FAISS.from_documents(documents, embeddings)
```

保存到：

```text
vector_index/
├── index.faiss
└── index.pkl
```

运行流程：

1. 把每个 chunk 的文本送入 embedding 模型。
2. 得到向量。
3. 存入 FAISS。
4. 查询时把用户问题也转为向量。
5. 在 FAISS 中找语义相近的 chunk。

#### 4.3.3 本地 numpy 兜底

如果没有 `faiss-cpu`，代码会自动使用 `LocalVectorStore`：

- 用 numpy 存向量。
- 查询时计算 cosine similarity。
- 作为 FAISS 不可用时的兜底。

这让项目在缺少 FAISS 的环境中仍能展示向量检索链路。

### 4.4 `retrieval.py`

负责混合检索和排序。

核心类：

```python
HybridRetriever
KeywordRetriever
```

整体检索链路：

```text
用户问题
  ├── FAISS 向量检索
  ├── 中文 BM25 检索
  └── RRF 融合排序
        ↓
   文档感知 rerank
        ↓
   主文档上下文补全
        ↓
   top-k chunks
```

#### 4.4.1 语义检索

FAISS 负责语义相似度。

优点：

- 能理解“绩效申诉多久提交”和“审批时限”这类语义近似。
- 不完全依赖关键词重合。

#### 4.4.2 中文 BM25

BM25 是传统关键词检索方法。

中文不能像英文按空格分词，所以项目自定义了中文 n-gram tokenizer：

```python
terms.extend(run[index : index + 2])
terms.extend(run[index : index + 3])
```

也就是对中文连续文本生成二字词和三字词。

优点：

- 对制度标题、表单编号、部门、流程类型等精确词很敏感。
- 弥补向量检索可能“语义泛化过头”的问题。

#### 4.4.3 RRF 融合排序

RRF 全称 Reciprocal Rank Fusion。

它不直接比较向量分数和 BM25 分数，而是比较排名。

公式思想：

```text
score += 1 / (rrf_k + rank)
```

优点：

- 不需要把向量分数和 BM25 分数归一化。
- 对多路检索结果融合很稳定。

#### 4.4.4 文档感知 rerank

企业制度库中，同一个制度会被切成多个 chunk。普通 top-k 可能混入相邻制度。

项目做了 doc-aware rerank：

- 先按 chunk 得到 RRF 分数。
- 再按 `doc_id` 聚合同一文档的总分。
- 如果问题中包含完整制度标题，给该制度 boost。
- 如果问题中包含流程类型，给对应文档 boost。

这样能减少“绩效问题误召回报销制度”这类问题。

#### 4.4.5 主文档上下文补全

当 top-1 文档确定后，系统会优先补充同一主文档的其他相关章节。

目的：

- 提高 Context Precision。
- 让回答引用集中在同一制度。
- 避免把弱相关制度片段混进答案。

### 4.5 `generator.py`

负责答案生成。

它支持两种模式：

1. LLM 生成模式。
2. 本地抽取式兜底模式。

#### 4.5.1 LLM 生成

如果环境变量或 Streamlit Secrets 中有：

```text
DEEPSEEK_API_KEY
```

则使用：

```python
ChatOpenAI(
    model="deepseek-chat",
    base_url="https://api.deepseek.com",
)
```

因为 DeepSeek 支持 OpenAI-compatible API，所以项目通过 `openai` SDK 的 Chat Completions 接口调用。

Prompt 要求：

- 只基于给定资料回答。
- 不编造制度。
- 无明确依据时拒答。
- 按固定格式输出：

```text
结论：

办理/处理步骤：

所需材料：

注意事项：

引用来源：
```

#### 4.5.2 LLM 失败兜底

如果 API key 无效、网络失败或 DeepSeek 报错，系统不会崩溃，而是自动切换到本地抽取式回答。

这样做是为了保证 Demo 稳定：

- 面试现场即使没有网络也能演示。
- key 失效不会让页面报错。
- 部署环境没有 Secrets 时仍可用。

#### 4.5.3 本地抽取式回答

本地模式会：

1. 找到 top-1 主文档。
2. 只从主文档相关 chunk 中抽取内容。
3. 根据问题意图优先排序章节：
   - 问“多久、时限、提前”优先 `审批 SLA 与例外流程`。
   - 问“材料、资料”优先 `所需材料`。
   - 问“系统、流程、步骤、如何”优先 `办理步骤`。
   - 问“风险、注意”优先 `注意事项`。
4. 用固定格式拼出答案。

### 4.6 `pipeline.py`

这是 RAG 总控层。

核心类：

```python
EnterpriseKnowledgeRAG
```

核心方法：

```python
initialize()
ask(question, filters=None)
```

#### 4.6.1 初始化流程

```text
load_parent_documents()
  ↓
split_documents()
  ↓
VectorIndex.load() 或 VectorIndex.build()
  ↓
HybridRetriever(...)
  ↓
AnswerGenerator(...)
```

#### 4.6.2 问答流程

```text
用户问题
  ↓
out-of-scope guardrail
  ↓
retriever.search()
  ↓
low confidence check
  ↓
generator.generate()
  ↓
build_sources()
  ↓
RAGResponse(answer, sources, chunks)
```

#### 4.6.3 Out-of-scope guardrail

项目定义了个人福利、生活、投资等越界关键词，例如：

- 股票
- 子女入学
- 宠物
- 购房
- 停车位
- 生日礼物
- 水电费

这些问题不属于企业制度库范围，会直接拒答，避免强行匹配到相似制度。

#### 4.6.4 低置信度拒答

如果检索到的 chunk 和问题关键词重叠太弱，系统会拒答。

目的：

- 防止知识库外问题被向量检索“硬匹配”。
- 降低无依据回答风险。

### 4.7 `__init__.py`

包初始化文件，标记 `smart_office_rag` 是一个 Python package。

---

## 5. `scripts/`：数据生成脚本

### `scripts/generate_enterprise_dataset.py`

这个脚本生成：

- 30 篇企业制度 Markdown。
- 172 条评估问题 JSONL。

运行：

```powershell
.\.venv\Scripts\python.exe scripts\generate_enterprise_dataset.py
```

它的价值：

- 让模拟数据可复现。
- 不依赖真实企业隐私数据。
- 可以向面试官解释数据构造方式。

注意：

运行脚本会先清理 `data/policies/*.md`，再重新生成制度文件。

---

## 6. RAG 全流程详解

### 6.1 第一步：准备知识库文档

文件：

```text
data/policies/*.md
```

每篇文档有两部分：

1. metadata front matter。
2. Markdown 正文。

metadata 负责过滤、引用、评估和排序增强。

正文负责被检索和生成答案。

### 6.2 第二步：加载文档

对应文件：

```text
smart_office_rag/documents.py
```

执行：

```python
loader.load_parent_documents()
```

输出：

```python
List[Document]
```

每个 parent document 对应一整篇制度。

### 6.3 第三步：按标题结构分块

对应文件：

```text
smart_office_rag/documents.py
```

执行：

```python
loader.split_documents(parents)
```

分块策略：

- 按 `#`
- 按 `##`
- 按 `###`

不是固定长度切分。

为什么适合本项目：

- 企业制度天然有章节。
- 每个章节语义完整。
- 引用来源更清楚。

输出 chunk 示例：

```text
《绩效目标与考核申诉流程》审批 SLA 与例外流程
```

### 6.4 第四步：Embedding 向量化

对应文件：

```text
smart_office_rag/indexing.py
```

模型：

```text
BAAI/bge-small-zh-v1.5
```

每个 chunk 会被转成一个 512 维向量。

用户问题也会转成同一向量空间中的向量。

这样就可以计算“问题”和“制度片段”的语义相似度。

### 6.5 第五步：构建向量数据库

对应文件：

```text
smart_office_rag/indexing.py
```

优先使用：

```text
FAISS
```

FAISS 索引本地缓存：

```text
vector_index/index.faiss
vector_index/index.pkl
```

这些文件不提交 Git，因为：

- 可以由代码重新生成。
- 体积可能增长。
- 云端部署时可重新构建。

### 6.6 第六步：混合检索

对应文件：

```text
smart_office_rag/retrieval.py
```

并行两路检索：

```text
FAISS 向量检索
中文 BM25 检索
```

向量检索适合语义匹配。

BM25 适合关键词、标题、表单编号、系统名、部门名精确匹配。

### 6.7 第七步：RRF 融合排序

对应文件：

```text
smart_office_rag/retrieval.py
```

作用：

- 合并向量检索和 BM25 检索结果。
- 综合两边的排名。
- 得到更稳的候选 chunk 排序。

### 6.8 第八步：文档感知 rerank

对应文件：

```text
smart_office_rag/retrieval.py
```

作用：

- 聚合同一 `doc_id` 的 chunk 分数。
- 如果问题里包含制度标题，提升该制度。
- 如果问题里包含流程类型，提升对应文档。

这一步是为企业制度库特意加的。

### 6.9 第九步：主文档上下文补全

对应文件：

```text
smart_office_rag/retrieval.py
```

当 top 文档确定后，系统优先补全同一文档的相关章节。

好处：

- 回答更集中。
- 引用更一致。
- 减少弱相关片段。
- Context Precision 更高。

### 6.10 第十步：生成回答

对应文件：

```text
smart_office_rag/generator.py
```

两种路径：

```text
有 DeepSeek API Key
  → DeepSeek 生成自然语言答案

没有 Key / Key 失效 / 网络失败
  → 本地抽取式模板生成答案
```

两种路径都要求输出：

```text
结论
办理/处理步骤
所需材料
注意事项
引用来源
```

### 6.11 第十一步：页面展示

对应文件：

```text
app.py
```

页面展示：

- 回答。
- 引用来源。
- 检索片段。
- metadata。
- 检索分数和排序信息。
- 评估概览。

---

## 7. 评估系统详解

### 7.1 评估入口

```powershell
.\.venv\Scripts\python.exe evaluate.py
```

输入：

```text
data/eval/eval_cases.jsonl
```

输出：

```text
eval_report.json
eval_report.md
```

### 7.2 检索指标

#### Hit@K

含义：

> 期望文档是否出现在前 K 个检索结果中。

例如 Hit@5 = 1，表示正确文档出现在 top-5 中。

意义：

- 衡量“能不能找到正确文档”。
- 是 RAG 检索最基础指标。

#### Recall@K

含义：

> 应该召回的文档中，有多少比例出现在 top-K。

如果一个问题有多个期望文档，Recall@K 比 Hit@K 更有意义。

#### Context Precision@K

含义：

> top-K 检索片段中，有多少来自正确文档。

意义：

- 衡量上下文是否纯净。
- 低 Context Precision 说明虽然找到了正确文档，但混了很多无关片段。
- 这会增加大模型幻觉风险。

#### MRR@K

MRR 全称 Mean Reciprocal Rank。

含义：

> 正确文档排得越靠前，分数越高。

例子：

- 正确文档第 1 名：1.0
- 第 2 名：0.5
- 第 3 名：0.333

意义：

- 面试中很好解释：不仅要找得到，还要排得靠前。

#### nDCG@K

含义：

> 考虑相关性和排序位置的综合指标。

本项目中相关性是二值的：

- 目标文档：1
- 非目标文档：0

意义：

- 适合衡量排序质量。
- 比 Hit@K 更关注“排在第几”。

### 7.3 生成指标

#### Citation Accuracy

含义：

> 答案引用来源是否来自期望文档。

为什么重要：

- RAG 的一个核心优势是可追溯。
- 只要引用错了，即使答案看起来合理，也不可信。

#### Faithfulness Proxy

含义：

> 答案是否受到检索来源支撑。

本项目用确定性 proxy：

- 引用准确，且不是知识库外乱答，则视为 grounded。

注意：

这不是严格的 LLM-as-a-judge faithfulness。更严格的版本可以接 RAGAS 或 DeepEval。

#### Answer Correctness Proxy

含义：

> 回答和参考答案之间的关键词重叠比例。

作用：

- 作为本地、低成本的答案正确性近似。
- 不需要调用额外 LLM。

局限：

- 它不理解复杂语义。
- 更像粗略质量信号，不是最终人工评分。

### 7.4 拒答指标

#### Refusal Accuracy

含义：

> 知识库外问题是否被正确拒答。

例如：

```text
员工停车位摇号规则是什么？
```

如果知识库没有这类制度，系统应该回答：

```text
当前知识库没有检索到明确依据，建议联系对应负责部门确认。
```

意义：

- 防止 RAG 编造制度。
- 对企业知识库非常重要。

### 7.5 工程指标

#### Latency p50 / p95

含义：

- p50：一半请求快于这个时间。
- p95：95% 请求快于这个时间。

意义：

- 衡量系统响应速度。
- 面试中可以说明工程化意识。

#### Index Build Time

含义：

> 构建向量索引耗时。

本项目会记录在 `eval_report.json` 中。

### 7.6 当前评估结果如何解释

当前报告显示：

```text
Total cases: 172
Retrieval cases: 150
Refusal cases: 22
Hit@5: 1.000
Recall@5: 1.000
Context Precision@5: 1.000
MRR@5: 1.000
nDCG@5: 1.000
Citation Accuracy: 1.000
Refusal Accuracy: 1.000
Faithfulness Proxy: 1.000
Answer Correctness Proxy: 0.603
Latency p50 / p95: 31.1 ms / 36.9 ms
```

解释：

- 检索在当前模拟评估集上表现很好。
- 引用来源完全命中期望文档。
- 知识库外问题全部正确拒答。
- Answer Correctness Proxy 只有 0.603，不代表系统差，而是因为它用关键词重叠衡量抽取式答案和参考答案，口径比较粗。
- 如果要更接近业界评估，可以进一步加入 RAGAS/DeepEval 风格的 LLM-as-a-judge。

---

## 8. 一次用户问题在项目中的完整路径

以问题为例：

```text
绩效申诉需要在多久内提交？
```

完整路径：

1. `app.py` 接收问题。
2. 调用 `EnterpriseKnowledgeRAG.ask()`。
3. `pipeline.py` 判断不是 out-of-scope。
4. `retrieval.py` 同时进行 FAISS 向量检索和中文 BM25。
5. RRF 融合排序。
6. 标题/流程类型 boost。
7. 主文档上下文补全。
8. 返回与 `HR-PERF-2026` 相关的 chunk。
9. `generator.py` 发现问题含“多久”，优先选择 `审批 SLA 与例外流程`。
10. 如果 DeepSeek 可用，调用 LLM 生成；否则本地抽取式生成。
11. 返回答案：

```text
绩效申诉须在结果发布后三个工作日内提交。
```

12. `app.py` 展示回答、引用来源和检索片段。

---

## 9. 常见问题与排查

### 9.1 页面结果和 CLI 不一致

可能原因：

- Streamlit 还在运行旧进程。
- `st.cache_resource` 缓存了旧知识库。
- 浏览器访问的是旧端口。

处理：

1. 终端按 `Ctrl + C` 停止 Streamlit。
2. 重新运行：

```powershell
.\.venv\Scripts\python.exe run_web_demo.py
```

3. 页面左侧点击“重新加载知识库”。

### 9.2 DeepSeek 401

原因：

```text
DEEPSEEK_API_KEY 无效
```

处理：

- 检查当前终端是否设置了正确 key。
- 在 Streamlit Cloud 中用 Secrets 设置 key。
- 如果 key 无效，系统会自动退回本地抽取式回答。

### 9.3 Hugging Face 模型下载慢

模型：

```text
BAAI/bge-small-zh-v1.5
```

首次运行需要下载。之后会缓存到：

```text
.cache/huggingface
```

### 9.4 为什么不提交 `vector_index/`

因为索引可以由代码生成，而且不同环境下路径和二进制兼容性可能不同。

云端第一次启动会重新构建或缓存索引。

---

## 10. 面试讲解建议

可以按这条线讲：

1. 项目目标：企业员工服务知识库助手。
2. 数据构造：30 篇自制模拟制度，避免隐私和版权风险。
3. 文档结构：Markdown + front matter metadata。
4. 分块策略：按 Markdown 标题结构切块。
5. 向量化：`BAAI/bge-small-zh-v1.5`。
6. 检索：FAISS 语义检索 + 中文 BM25。
7. 融合：RRF + 文档感知 rerank。
8. 生成：DeepSeek 或本地抽取式兜底。
9. 安全：低置信度拒答 + out-of-scope guardrail。
10. 评估：172 条评估集，覆盖检索、引用、拒答和延迟。
11. 展示：Streamlit Web Demo + GitHub + Streamlit Cloud 部署。

一句高级总结：

> 这个项目不是单纯调用大模型问答，而是围绕企业制度知识库构建了完整的 RAG 工程链路，包括结构化文档、metadata、标题分块、混合检索、RRF 融合、引用约束、拒答策略和可复现实验评估。
