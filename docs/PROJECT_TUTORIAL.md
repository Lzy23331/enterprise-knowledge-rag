# SmartOfficeRAG 项目教程与学习说明

这份文档是 SmartOfficeRAG 的主教程，面向项目作者、面试讲解者和后续维护者。目标不是只告诉你“怎么运行”，而是让你能按文件夹顺序理解：

- 这个项目有哪些文件，每个文件负责什么。
- 哪些内容是 RAG 检索知识库，哪些内容是代码。
- 一条用户问题从输入到回答，具体经过哪些步骤。
- 文本如何分块，向量索引如何构建，embedding 模型如何选择。
- BM25、向量检索、RRF、拒答、引用来源分别解决什么问题。
- 评估系统怎么设计，各个指标是什么意思。
- 后续新增的 V0-V7 真实实验如何支撑“发现问题 -> 解决问题 -> 最终选型”的简历故事。

项目路径：

```text
D:\projects\enterprise-knowledge-rag
```

一句话概括：

> SmartOfficeRAG 是一个面向企业内部制度/政策咨询场景的 RAG 问答助手。它基于自制模拟企业制度文档，完成文档治理、结构化 metadata、文本分块、embedding 向量化、FAISS/NumPy 向量索引、BM25 关键词检索、RRF 混合召回、低置信拒答、引用溯源、Streamlit 展示和可复现实验评估。

---

## 1. 项目总览

当前项目主要由这些部分组成：

```text
enterprise-knowledge-rag/
├── app.py
├── app_full.py
├── cli.py
├── evaluate.py
├── run_experiments.py
├── run_web_demo.py
├── requirements.txt
├── requirements-full.txt
├── runtime.txt
├── README.md
├── DEPLOYMENT.md
├── eval_report.json
├── eval_report.md
├── data/
│   ├── policies/
│   └── eval/
├── docs/
│   ├── PROJECT_TUTORIAL.md
│   └── EXPERIMENT_REPORT.md
├── experiments/
│   ├── configs/
│   └── results/
├── scripts/
├── smart_office_rag/
├── vector_index/        # 本地生成，Git 忽略
├── .cache/              # Hugging Face 模型缓存，Git 忽略
└── .venv/               # 虚拟环境，Git 忽略
```

先记住几个最重要的归类：

| 类别 | 路径 | 用途 |
| --- | --- | --- |
| 知识库文档 | `data/policies/*.md` | RAG 实际检索的企业制度文本 |
| 评估集 | `data/eval/eval_cases.jsonl` | 用来测试检索、引用、拒答和答案质量 |
| 核心 RAG 代码 | `smart_office_rag/` | 文档加载、分块、索引、检索、生成、总控 |
| Web 展示 | `app.py` | Streamlit 页面入口 |
| 单次评估 | `evaluate.py` | 跑当前最终链路的评估 |
| 迭代实验 | `run_experiments.py` + `experiments/` | 跑 V0-V7 版本对比和 embedding 选型 |
| 数据生成 | `scripts/generate_enterprise_dataset.py` | 生成模拟制度和评估样本 |
| 报告文档 | `eval_report.*`、`docs/EXPERIMENT_REPORT.md` | 展示评估和实验结果 |

---

## 2. 根目录文件说明

### 2.1 `app.py`

`app.py` 是当前 Streamlit Web Demo 的主入口，也是部署到 Streamlit Cloud 时使用的入口文件。

它负责：

- 设置页面标题、布局和说明。
- 初始化 `EnterpriseKnowledgeRAG`。
- 展示制度文档数、chunk 数、评估指标和实验指标。
- 提供部门、流程类型、风险等级过滤器。
- 提供示例问题按钮。
- 接收用户问题。
- 调用 `rag.ask(question, filters=filters)`。
- 展示回答、引用来源、检索片段、检索分数、拒答原因和端到端耗时。
- 展示离线评估报告。
- 展示研发迭代实验历程，也就是 V0-V7 对比表。

你需要理解的一点：

> `app.py` 不负责实现 RAG 算法。它只是展示层。真正的检索、排序、拒答和生成都封装在 `smart_office_rag/` 里。

页面读取两个报告：

```text
eval_report.json
experiments/results/experiment_report.json
```

其中 `experiment_report.json` 是后续新增的实验报告，用来展示 V0-V7 的迭代过程和最终模型选择。

`app.py` 里有一个重要细节：读取实验报告时会把文件修改时间作为 cache key。

```python
experiment_report_mtime = EXPERIMENT_REPORT_PATH.stat().st_mtime
experiment_report = load_experiment_report(experiment_report_mtime)
```

为什么这样做：

- Streamlit 默认会缓存数据。
- 如果重新跑了实验，JSON 文件变了，但缓存不更新，页面可能仍显示旧结果。
- 加入 `mtime` 后，只要报告文件更新，页面就会重新读取。

### 2.2 `app_full.py`

这是早期的本地完整版 Streamlit 入口，保留作历史参考。

当前主入口已经是 `app.py`。面试或部署时优先讲 `app.py`，不要把 `app_full.py` 当主线。

### 2.3 `cli.py`

命令行测试入口。

用法：

```powershell
.\.venv\Scripts\python.exe cli.py "涉及客户数据导出时需要注意什么？"
```

适合用来：

- 不打开网页时快速测试 RAG。
- 验证某个问题是否能召回正确制度。
- 排查 Streamlit 页面缓存问题。

### 2.4 `evaluate.py`

`evaluate.py` 是单次评估脚本。

它读取：

```text
data/eval/eval_cases.jsonl
```

输出：

```text
eval_report.json
eval_report.md
```

它主要用于评估当前最终链路，包括：

- Hit@5
- MRR@5
- nDCG@5
- Citation Accuracy
- Refusal Accuracy
- Faithfulness Proxy
- Answer Correctness Proxy
- latency p50/p95

注意：`evaluate.py` 现在也包含简单策略对比，但它不是完整实验框架。完整版本线请看 `run_experiments.py`。

### 2.5 `run_experiments.py`

这是后续优化中新增的关键文件。

它负责跑真实研发迭代实验，不是简单评估最终链路。

它会读取：

```text
experiments/configs/*.json
```

并生成：

```text
docs/EXPERIMENT_REPORT.md
experiments/results/experiment_report.json
experiments/results/experiment_report.csv
```

支持两种模式：

```powershell
.\.venv\Scripts\python.exe run_experiments.py --quick
.\.venv\Scripts\python.exe run_experiments.py --full
```

区别：

- `--quick`：跑轻量可复现实验，主要包括 V0、V1、V2、V3、V4 local-hashing、V5、V6、V7。
- `--full`：在线下载/加载真实 embedding 模型，完整对比 bge-small、bge-base、multilingual-e5。

严格规则：

- `--full` 默认是严格模式。
- 如果某个 embedding 模型没有成功加载，脚本会失败。
- 只有显式加 `--offline --allow-skip`，才允许模型不可用时标记 skipped。

这点很重要。它保证最后简历里的模型选型不是“兜底跑出来的”，而是真实跑通多个模型后得到的结论。

### 2.6 `run_web_demo.py`

本地启动 Streamlit 的便利脚本。

它会默认设置：

```python
SMARTOFFICE_USE_VECTOR=1
HF_HOME=.cache/huggingface
```

启动：

```powershell
.\.venv\Scripts\python.exe run_web_demo.py
```

### 2.7 `requirements.txt`

轻量部署依赖，主要给 Streamlit Cloud 使用。

当前包括：

```text
streamlit
rank_bm25
python-dotenv
openai
numpy
```

它不包含 `sentence-transformers` 和 `faiss-cpu`，原因是：

- Streamlit Cloud 免费环境资源有限。
- 全量 embedding 模型可能导致部署慢或失败。
- 公开 Demo 可以用轻量 fallback 和预生成报告展示主要能力。

### 2.8 `requirements-full.txt`

本地完整实验和完整向量体验依赖。

包括：

```text
faiss-cpu
sentence-transformers
rank_bm25
openai
numpy
streamlit
```

如果你要跑 full embedding 实验，必须安装：

```powershell
.\.venv\Scripts\python.exe -m pip install --prefer-binary -r requirements-full.txt
```

### 2.9 `runtime.txt`

Streamlit Cloud 使用的 Python 版本：

```text
python-3.12
```

### 2.10 `README.md`

项目 GitHub 首页说明。

现在 README 已经更新为“真实实验过程”口径，包含：

- 项目业务目标。
- RAG 核心链路。
- 232 条评估集说明。
- V0-V7 实验摘要。
- 最终 embedding 选型结论。
- 运行方式。
- 简历描述。

### 2.11 `DEPLOYMENT.md`

部署说明，主要讲：

- Streamlit Cloud 怎么部署。
- 入口文件是 `app.py`。
- API Key 怎么放 Secrets。
- `run_experiments.py --full` 是正式在线实验。
- `--offline --allow-skip` 只是缓存复现，不适合作为最终选型依据。

### 2.12 `eval_report.json` 和 `eval_report.md`

单次评估结果。

- `eval_report.json`：给页面和程序读取。
- `eval_report.md`：给人看。

现在项目真正的“研发迭代故事”主要看：

```text
docs/EXPERIMENT_REPORT.md
```

---

## 3. `data/`：知识库与评估集

### 3.1 `data/policies/` 是检索知识库

这里的 `.md` 文件就是 RAG 系统实际检索的知识库。

当前共有 30 篇模拟企业制度，覆盖：

- HR：请假、入离职、培训、绩效、转岗。
- Finance：报销、备用金、发票、预算、付款。
- IT：权限、VPN、资产、故障、生产变更。
- Security：数据安全、访客、安全事件、信息分级、审计复核。
- Admin：会议室、印章、出差支持。
- Legal：合同评审、保密协议。
- Procurement：供应商准入、采购招投标。
- Audit：审计整改、监管报送。
- Operations：业务连续性演练。

这些文档是虚拟制度，不包含真实企业隐私。

每篇制度是 Markdown 格式，顶部有 front matter metadata：

```markdown
---
doc_id: IT-CHANGE-2026
title: 生产系统变更与应急处理规范
department: IT
process_type: 变更申请
risk_level: 高
doc_type: 制度
version: v2026.1
effective_date: 2026-01-01
updated_at: 2026-05-30
owner: 变更管理委员会
system: 变更管理平台
form_id: IT-F-005
approval_sla: 普通生产变更至少提前三个工作日提交
---
```

metadata 的作用：

| 字段 | 用途 |
| --- | --- |
| `doc_id` | 唯一文档 ID，评估和引用都靠它 |
| `title` | 制度标题，展示和排序增强 |
| `department` | 部门过滤 |
| `process_type` | 流程类型过滤和问题匹配 |
| `risk_level` | 风险等级过滤和高风险提示 |
| `owner` | 制度负责人 |
| `system` | 办理入口系统 |
| `form_id` | 所需表单 |
| `approval_sla` | 审批时限 |

正文结构通常是：

```markdown
# 制度标题

## 适用对象
## 办理条件
## 办理步骤
## 所需材料
## 审批 SLA 与例外流程
## 注意事项
## 常见问题
### 申请被退回怎么办
### 审批完成后发现信息填错怎么办
### 谁负责最终解释
```

这些标题会直接影响分块和引用来源。

### 3.2 `data/eval/eval_cases.jsonl` 是评估集

这是 RAG 的测试题库。

当前共有 232 条问题：

- 210 条知识库内问题。
- 22 条知识库外拒答问题。

覆盖的问题类型：

- 流程类。
- 材料类。
- 时限类。
- 合规类。
- 系统入口类。
- 同义改写类。
- 模糊追问类。
- 知识库外拒答类。

一条样本长这样：

```json
{
  "id": "it_change_2026_sla",
  "question": "变更申请的审批时限或提前要求是什么？",
  "expected_doc_ids": ["IT-CHANGE-2026"],
  "expected_sections": ["审批 SLA 与例外流程"],
  "reference_answer": "标准时限或提前要求为：普通生产变更至少提前三个工作日提交；材料缺失时从补齐后重新计算。",
  "question_type": "时限类",
  "department": "IT",
  "should_refuse": false
}
```

字段解释：

| 字段 | 含义 |
| --- | --- |
| `id` | 评估样本 ID |
| `question` | 用户问题 |
| `expected_doc_ids` | 正确制度文档 |
| `expected_sections` | 期望命中的章节 |
| `reference_answer` | 参考答案，用于答案正确性 proxy |
| `question_type` | 问题类型 |
| `department` | 相关部门 |
| `should_refuse` | 是否应该拒答 |

---

## 4. `smart_office_rag/`：核心 RAG 代码

### 4.1 `types.py`

定义最基础的数据结构：

```python
@dataclass
class Document:
    page_content: str
    metadata: Dict[str, Any]
```

整个项目中，制度文档、chunk、检索结果都用这个 `Document` 表示。

### 4.2 `config.py`

集中管理配置。

关键配置：

```python
data_path = PROJECT_ROOT / "data" / "policies"
index_path = PROJECT_ROOT / "vector_index"
embedding_model = os.getenv("SMARTOFFICE_EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
top_k = 5
llm_model = "deepseek-chat"
llm_base_url = "https://api.deepseek.com"
use_vector_index = os.getenv("SMARTOFFICE_USE_VECTOR", "1") == "1"
```

重要点：

- 默认 embedding 是 `BAAI/bge-small-zh-v1.5`。
- 可以用环境变量 `SMARTOFFICE_EMBEDDING_MODEL` 切换。
- `SMARTOFFICE_USE_VECTOR=1` 时启用向量检索。

### 4.3 `documents.py`

负责文档加载、metadata 解析和文本分块。

核心类：

```python
PolicyDocumentLoader
```

#### 4.3.1 加载制度文档

调用：

```python
loader.load_parent_documents()
```

它会遍历：

```text
data/policies/*.md
```

每一篇制度会变成一个 parent document。

#### 4.3.2 解析 front matter

代码使用正则：

```python
FRONT_MATTER_PATTERN = re.compile(...)
```

把 Markdown 顶部的 YAML-like metadata 解析到：

```python
Document.metadata
```

#### 4.3.3 三种分块策略

后续实验框架新增了可插拔分块策略：

```python
chunk_strategy="whole_document"
chunk_strategy="fixed_window"
chunk_strategy="markdown_headers"
```

这三种策略分别对应实验中的 V1、V2、V3。

##### 策略一：整文档分块 `whole_document`

一整篇制度就是一个 chunk。

优点：

- 简单。
- 不容易漏掉信息。
- Hit@5 可能很高，因为只要文档命中就算命中。

缺点：

- chunk 太大，上下文噪声多。
- 引用无法精确到章节。
- Citation Accuracy 较低。
- 大模型生成时容易混入不相关内容。

实验结果：

```text
V1 keyword_whole_document
Answer Accuracy Proxy: 0.416
Citation Accuracy: 0.184
Refusal Accuracy: 0.045
```

结论：整文档能找到文档，但不适合作为最终 RAG chunk。

##### 策略二：固定窗口 `fixed_window`

按固定字符长度切分，例如：

```text
chunk_size = 900
overlap = 120
```

优点：

- 实现简单。
- 比整文档更细。
- BM25 很容易命中关键词。

缺点：

- 可能把标题和正文切开。
- 可能把“办理步骤”和“所需材料”切在一起。
- 引用来源不如标题分块清楚。

实验结果：

```text
V2 bm25_fixed_window
Answer Accuracy Proxy: 0.555
Citation Accuracy: 0.372
Refusal Accuracy: 0.182
```

结论：答案 proxy 提升，但引用仍不够好。

##### 策略三：Markdown 标题分块 `markdown_headers`

按 `#`、`##`、`###` 标题结构切块。

优点：

- 企业制度天然就是章节化文本。
- 每个 chunk 对应一个制度章节。
- 引用可以精确到“《制度名》章节名”。
- Citation Accuracy 大幅提升。

实验结果：

```text
V3 bm25_header_chunk
Citation Accuracy: 0.840
```

结论：最终采用 Markdown 标题分块作为主策略。

每个 chunk 会生成：

```python
chunk_id
chunk_index
section
citation
chunk_size
```

示例 citation：

```text
《生产系统变更与应急处理规范》审批 SLA 与例外流程
```

### 4.4 `indexing.py`

负责 embedding 和向量索引。

核心类：

```python
EmbeddingModel
VectorStore
VectorRetriever
VectorIndex
```

#### 4.4.1 `EmbeddingModel`

支持两类 embedding：

1. 真实 sentence-transformers 模型。
2. `local-hashing` fallback。

真实模型包括：

```text
BAAI/bge-small-zh-v1.5
BAAI/bge-base-zh-v1.5
intfloat/multilingual-e5-small
```

这些模型在 full 实验中真实在线跑通。

#### 4.4.2 `local-hashing` 是什么

`local-hashing` 不是一个真正的语义 embedding 模型。

它的实现思路：

1. 把文本切成 token。
2. 对 token 做 hash。
3. 映射到固定维度向量。
4. 归一化。

作用：

- 快速。
- 不需要联网。
- 不需要 Hugging Face 模型。
- 适合作为 fallback 或 quick baseline。

限制：

- 不具备真正语义理解能力。
- 不能作为最终 embedding 选型结论。

所以现在项目里的严谨说法是：

> `local-hashing` 只作为快速可复现 baseline；最终 embedding 选型来自在线 full 实验中的 bge-small、bge-base、multilingual-e5 对比。

#### 4.4.3 向量库：FAISS 与 NumPy

`VectorStore` 支持：

- FAISS。
- NumPy fallback。

如果安装了 `faiss-cpu`，默认使用 FAISS：

```python
faiss.IndexFlatIP
```

如果没有 FAISS，就用 NumPy 矩阵乘法做相似度：

```python
scores = vectors @ query_vector
```

实验中：

- quick 模式用 `local-hashing + numpy`，保证可复现。
- full 模式用真实 embedding + FAISS，做严谨模型对比。

#### 4.4.4 为什么最终不是 Milvus/ES/PGVector

本项目是个人项目和面试展示，数据规模是 30 篇制度、330 个 chunk。

选择 FAISS 的原因：

- 本地可运行。
- 无需部署额外服务。
- 与 Streamlit Demo 更容易集成。
- 对当前规模足够。

其他方案怎么讲：

| 方案 | 适用场景 | 本项目结论 |
| --- | --- | --- |
| FAISS | 本地向量检索、原型验证、离线实验 | 当前 full 实验使用 |
| NumPy | 小规模、无依赖 fallback | quick baseline 使用 |
| Chroma | 本地持久化和 metadata 管理 | 可作为后续增强 |
| Milvus | 大规模生产向量库 | 当前规模过重 |
| Elasticsearch | 企业已有搜索基础设施、BM25 强 | 企业落地可考虑 |
| PGVector | 数据已在 Postgres 中 | 适合业务系统集成 |

### 4.5 `retrieval.py`

负责检索和排序。

核心类：

```python
KeywordRetriever
BM25TextRetriever
HybridRetriever
```

#### 4.5.1 KeywordRetriever

朴素关键词检索。

它用中文二元/三元 n-gram 做 token：

```python
员工请假 -> 员工、工请、请假、员工请、工请假
```

实验中 V1 使用它。

#### 4.5.2 BM25TextRetriever

BM25 是经典稀疏检索方法。

适合：

- 表单编号。
- 制度标题。
- 系统名称。
- 部门名称。
- 业务关键词。

中文没有空格分词，所以项目继续使用自定义 n-gram token。

实验中：

- V2：固定窗口 + BM25。
- V3：标题分块 + BM25。

#### 4.5.3 VectorRetriever

向量检索不在 `retrieval.py` 里定义，而是在 `indexing.py` 里。

它负责：

1. 把 query 编码成向量。
2. 在 FAISS 或 NumPy 中找相似 chunk。
3. 返回带 `vector_score` 的文档。

实验中：

- V4-local：local-hashing + NumPy。
- V4-bge-small：bge-small + FAISS。
- V4-bge-base：bge-base + FAISS。
- V4-e5：multilingual-e5 + FAISS。

#### 4.5.4 HybridRetriever

最终主链路的检索器。

流程：

```text
query
  ├── vector retriever
  └── BM25 retriever
       ↓
     RRF
       ↓
 doc-aware order
       ↓
 primary doc context expansion
```

#### 4.5.5 RRF 融合

RRF 是 Reciprocal Rank Fusion。

它不强行比较 BM25 分数和向量分数，而是比较排名：

```text
score += 1 / (rrf_k + rank)
```

优点：

- 向量分数和 BM25 分数尺度不同，也能融合。
- 排名稳定。
- 工程实现简单。

#### 4.5.6 文档级排序增强

项目不只看 chunk 分数，还会聚合同一 `doc_id` 的分数。

它会额外考虑：

- 同一制度多个 chunk 的累计分。
- title 是否出现在 query 中。
- process_type 是否出现在 query 中。
- BM25 最佳排名。

这样做是因为企业制度常常是“一篇制度多个章节”，最终回答应该集中在同一主制度上。

#### 4.5.7 主文档上下文补全

当 top 文档确定后，系统会补充同一文档下的其他章节。

例如用户问：

```text
访问生产系统需要走什么审批？
```

系统可能先命中 `办理步骤`，但回答还需要：

- 所需材料。
- 审批 SLA。
- 注意事项。

所以会从同一个 `doc_id` 中补充相关 chunk。

### 4.6 `generator.py`

负责答案生成。

支持两种路径：

1. LLM 生成。
2. 本地抽取式兜底。

#### 4.6.1 LLM 生成

如果配置了：

```text
DEEPSEEK_API_KEY
OPENAI_API_KEY
```

则使用 OpenAI-compatible 客户端调用模型。

默认模型：

```text
deepseek-chat
```

Prompt 要求：

- 只基于给定资料回答。
- 不要编造制度。
- 无明确依据时拒答。
- 固定输出结构：

```text
结论：
办理/处理步骤：
所需材料：
注意事项：
引用来源：
```

#### 4.6.2 本地抽取式兜底

如果没有 API key，或设置：

```text
SMARTOFFICE_DISABLE_LLM=1
```

系统会使用本地抽取式回答。

它会：

- 选择 top 文档。
- 根据问题意图排序章节。
- 抽取相关内容。
- 用固定模板输出。

这保证：

- 面试现场没有 API key 也能演示。
- 评估不依赖外部模型。
- 成本稳定。

#### 4.6.3 高风险业务提示

后续优化中新增了高风险 guardrail。

如果制度风险等级是“高”，或涉及：

- 数据。
- 生产系统。
- 合同。
- 付款。
- 印章。
- 监管。
- 权限。
- 审计。

回答会强调：

```text
需保留系统流水、审批意见和执行证据；不得用口头确认替代系统审批。
```

这体现业务思维，不只是技术检索。

#### 4.6.4 无依据回答

`generate_no_evidence()` 用于拒答场景。

它不只是说“没有答案”，还会给下一步建议：

- 确认问题所属部门。
- 联系制度负责人。
- 准备问题背景、申请人、所属部门、截图/合同/清单。
- 高风险事项必须人工确认。

### 4.7 `pipeline.py`

RAG 总控层。

核心类：

```python
EnterpriseKnowledgeRAG
```

核心方法：

```python
initialize()
ask(question, filters=None)
```

#### 4.7.1 初始化

```text
load_parent_documents()
  ↓
split_documents()
  ↓
build/load vector index
  ↓
HybridRetriever
  ↓
AnswerGenerator
```

#### 4.7.2 问答流程

```text
用户问题
  ↓
out-of-scope 检查
  ↓
混合检索
  ↓
低置信检查
  ↓
生成答案
  ↓
构建引用来源
  ↓
返回 RAGResponse
```

`RAGResponse` 包含：

```python
answer
sources
chunks
retrieval_trace
latency_ms
refused
refusal_reason
```

这些字段会在 Streamlit 页面上展示。

#### 4.7.3 Out-of-scope 拒答

项目内置越界词，例如：

- 股票。
- 子女入学。
- 宠物。
- 购房。
- 健身卡。
- 停车位。
- 食堂菜单。

这些问题不属于当前制度库，直接拒答。

#### 4.7.4 低置信拒答

如果检索结果与问题的关键词重叠太弱：

```python
max_overlap < 3
```

系统选择拒答，避免编造。

这是 V6 实验中显著提升 Refusal Accuracy 的关键策略。

---

## 5. `scripts/`：模拟数据生成

### 5.1 `scripts/generate_enterprise_dataset.py`

这个脚本生成：

- 30 篇制度文档。
- 232 条评估样本。

运行：

```powershell
.\.venv\Scripts\python.exe scripts\generate_enterprise_dataset.py
```

它的作用：

- 避免真实企业隐私。
- 保证项目数据可复现。
- 保证制度和评估集字段一致。

注意：

运行它会重写 `data/policies/` 和 `data/eval/eval_cases.jsonl`。

### 5.2 评估样本如何生成

每篇制度生成多类问题：

- 办理步骤。
- 所需材料。
- 审批 SLA。
- 风险注意事项。
- 系统入口。
- 同义改写。
- 模糊追问。

例如：

```text
我想咨询客户数据相关事项，应该看哪份制度、走哪个入口？
```

这类问题比直接问制度标题更接近真实员工提问。

---

## 6. `experiments/`：真实研发迭代实验

这是后续优化新增的最重要部分。

目录：

```text
experiments/
├── configs/
└── results/
```

### 6.1 `experiments/configs/`

这里每个 JSON 是一个实验版本。

配置字段示例：

```json
{
  "id": "V6-bge-small",
  "name": "hybrid_bge_small_faiss_guarded",
  "stage": "full",
  "chunk_strategy": "markdown_headers",
  "retriever": "hybrid_rrf",
  "embedding_model": "BAAI/bge-small-zh-v1.5",
  "vector_backend": "faiss",
  "query_rewrite": false,
  "metadata_filter": false,
  "refusal_gate": true,
  "final_candidate": true
}
```

字段解释：

| 字段 | 含义 |
| --- | --- |
| `id` | 版本号，例如 V0、V6-bge-small |
| `name` | 实验名称 |
| `stage` | quick 或 full |
| `chunk_strategy` | 分块策略 |
| `retriever` | 检索策略 |
| `embedding_model` | embedding 模型 |
| `vector_backend` | numpy 或 faiss |
| `query_rewrite` | 是否启用查询改写 |
| `metadata_filter` | 是否启用 metadata hint/filter |
| `refusal_gate` | 是否启用拒答门控 |
| `final_candidate` | 是否参与最终模型选型 |

### 6.2 V0-V7 实验线

#### V0：LLM direct

无知识库，不检索，直接回答。

目的：

- 作为不可追溯 baseline。
- 暴露纯 LLM 无法保证引用和拒答。

结果：

```text
Answer Accuracy Proxy: 0.000
Citation Accuracy: 0.095
Refusal Accuracy: 0.000
```

#### V1：整文档关键词检索

策略：

```text
whole_document + keyword_only
```

结论：

- Hit@5 很高。
- 但引用准确率很差，因为整篇制度太粗。

#### V2：固定窗口 + BM25

策略：

```text
fixed_window + bm25_only
```

结论：

- Answer Accuracy Proxy 提升。
- 但章节引用仍然不精确。

#### V3：Markdown header chunk + BM25

策略：

```text
markdown_headers + bm25_only
```

结论：

- 引用准确率大幅提升。
- 说明企业制度适合标题结构分块。

#### V4：纯向量 embedding 对比

对比：

```text
local-hashing + NumPy
bge-small + FAISS
bge-base + FAISS
multilingual-e5 + FAISS
```

结论：

- 纯向量召回在当前制度库上不如 BM25 稳。
- bge-base 纯向量略优于 bge-small。
- multilingual-e5 引用表现不错，但中文检索 Hit@5 不如 bge 系列。
- 纯向量不能单独作为最终方案。

#### V5：BM25 + vector + RRF

策略：

```text
BM25 + local-hashing vector + RRF
```

结论：

- 混合检索显著提升 citation。
- 但没有拒答门控时，知识库外问题仍可能误召回相近制度。

#### V6：Hybrid RRF + 拒答门控

策略：

```text
BM25 + vector + RRF + refusal_gate
```

这是最终主链路。

在 full 实验中又细分：

```text
V6-bge-small
V6-bge-base
V6-e5
```

#### V7：Query rewrite + metadata hint

策略：

```text
query_rewrite + metadata_filter + hybrid_rrf + refusal_gate
```

结论：

- 不是所有增强都会提升效果。
- 当前规则改写会把部分相似制度导向错误部门。
- 所以没有选 V7。

这是非常适合面试讲的点：

> 我不是堆功能，而是通过实验发现 query rewrite 在当前样本上有副作用，因此没有上线。

### 6.3 最终 embedding 选型

full 在线实验已经真实跑通：

```text
BAAI/bge-small-zh-v1.5
BAAI/bge-base-zh-v1.5
intfloat/multilingual-e5-small
```

最终结果摘要：

| 版本 | Embedding | Answer Acc. | Hit@5 | Citation Acc. | Refusal Acc. | p95 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| V6-bge-base | bge-base | 0.573 | 0.990 | 0.983 | 1.000 | 高 |
| V6-bge-small | bge-small | 0.570 | 0.990 | 0.983 | 1.000 | 低很多 |
| V6-e5 | multilingual-e5 | 0.566 | 0.990 | 0.983 | 1.000 | 中等 |

严谨结论：

- bge-base 是质量 leader，Answer Accuracy Proxy 略高。
- bge-small 与 bge-base 在 Hit@5、Citation Accuracy、Refusal Accuracy 上完全持平。
- bge-small 的 p95 latency 明显低于 bge-base。
- 因此部署选型选择 `BAAI/bge-small-zh-v1.5`。

这不是因为 bge-base 没跑成功，而是因为：

> bge-base 的质量收益很小，但延迟成本明显更高。

### 6.4 `experiments/results/`

包含：

```text
experiment_report.json
experiment_report.csv
```

`experiment_report.json` 给 Streamlit 页面读取。

`experiment_report.csv` 方便用表格查看每个版本结果。

为了避免文件太大，JSON 只保留：

- config。
- summary。
- failure_cases。

不再保存全部 232 条逐条结果。

---

## 7. `docs/`：文档和报告

### 7.1 `docs/PROJECT_TUTORIAL.md`

就是你正在看的这份教程。

用途：

- 帮你学习项目。
- 帮你准备面试讲解。
- 帮你知道每个文件对应 RAG 哪一步。

### 7.2 `docs/EXPERIMENT_REPORT.md`

研发实验报告。

重点看：

- Iteration Summary。
- Experiment Matrix。
- Failure-driven Iteration Notes。
- Vector Store Selection。
- Resume-ready Story。

这个文件是简历故事的事实依据。

---

## 8. 一条问题的完整 RAG 流程

以问题为例：

```text
涉及客户数据导出时需要注意什么？
```

### 第一步：页面接收问题

文件：

```text
app.py
```

用户在 Streamlit 输入问题，点击生成回答。

### 第二步：调用 RAG 总控

文件：

```text
smart_office_rag/pipeline.py
```

调用：

```python
rag.ask(question, filters=filters)
```

### 第三步：越界判断

如果问题包含股票、宠物、停车位、食堂菜单等知识库外词，会直接拒答。

当前问题是客户数据，属于制度库范围，所以继续。

### 第四步：文本分块已在初始化时完成

文件：

```text
smart_office_rag/documents.py
```

制度文档已按 Markdown 标题分成 chunk。

其中会有：

```text
《数据安全与客户信息保护规范》注意事项
《数据安全与客户信息保护规范》所需材料
《数据安全与客户信息保护规范》审批 SLA 与例外流程
```

### 第五步：embedding 和索引

文件：

```text
smart_office_rag/indexing.py
```

当前部署选型：

```text
BAAI/bge-small-zh-v1.5 + FAISS
```

每个 chunk 已经被编码成向量。

问题也会编码成向量。

### 第六步：并行检索

文件：

```text
smart_office_rag/retrieval.py
```

并行两路：

```text
向量检索：找语义相近 chunk
BM25：找关键词匹配 chunk
```

### 第七步：RRF 融合

把两路检索结果按排名融合。

目的：

- 既保留语义召回。
- 又保留业务关键词精确命中。

### 第八步：文档级 rerank 和上下文补全

系统确认主文档大概率是：

```text
SEC-DATA-2026 数据安全与客户信息保护规范
```

然后补充同一制度下的：

- 注意事项。
- 所需材料。
- 审批 SLA。
- 适用对象。

### 第九步：低置信拒答判断

如果检索结果太弱，拒答。

当前问题命中足够强，所以继续生成。

### 第十步：生成回答

文件：

```text
smart_office_rag/generator.py
```

如果有 LLM key：

```text
调用 DeepSeek/OpenAI-compatible API
```

如果没有：

```text
本地抽取式模板回答
```

回答会强调：

- 客户数据属于高风险。
- 需要审批记录。
- 需要合规审查或风险评估。
- 不得绕过系统审批。

### 第十一步：页面展示

文件：

```text
app.py
```

展示：

- 回答。
- 引用来源。
- 检索片段。
- vector_score。
- bm25_score。
- rrf_score。
- latency。
- 是否拒答。
- retrieval_trace。

---

## 9. 评估系统详解

### 9.1 单次评估和实验评估的区别

| 文件 | 用途 |
| --- | --- |
| `evaluate.py` | 评估当前最终链路 |
| `run_experiments.py` | 评估多个版本并形成研发故事 |

`evaluate.py` 更像健康检查。

`run_experiments.py` 更像研发实验记录。

### 9.2 Hit@5

含义：

> 正确文档是否出现在 top-5 检索结果中。

意义：

- 衡量能不能找到正确制度。
- RAG 最基础的检索指标。

### 9.3 Recall@5

含义：

> 期望召回的文档中，有多少比例出现在 top-5。

如果一个问题有多个正确文档，Recall 比 Hit 更细。

### 9.4 Context Precision@5

含义：

> top-5 里有多少结果来自正确文档。

意义：

- 衡量上下文是否干净。
- 混入太多无关片段会增加幻觉风险。

### 9.5 MRR@5

MRR 是 Mean Reciprocal Rank。

含义：

> 正确文档排得越靠前，分数越高。

例子：

- 正确文档第 1 名：1.0。
- 第 2 名：0.5。
- 第 3 名：0.333。

### 9.6 nDCG@5

衡量排序质量。

本项目里相关性是二值：

- 正确文档：1。
- 其他文档：0。

nDCG 越高，说明正确文档越靠前。

### 9.7 Citation Accuracy

含义：

> 答案引用来源是否来自期望文档。

为什么重要：

- 企业制度问答必须可追溯。
- 引用错了，答案再自然也不可信。

V0 的 Citation Accuracy 很低，因为没有检索知识库。

V6 的 Citation Accuracy 到 0.983，说明引用来源已经基本可靠。

### 9.8 Refusal Accuracy

含义：

> 知识库外问题是否正确拒答。

例如：

```text
公司股票什么时候可以买入？
```

制度库里没有，就应该拒答。

V5 没有拒答门控，所以 Refusal Accuracy 是 0。

V6 加入低置信拒答后，Refusal Accuracy 到 1.000。

### 9.9 Faithfulness Proxy

含义：

> 答案是否由检索来源支撑。

本项目用确定性 proxy：

- 如果引用来源正确，就认为答案更可信。
- 如果知识库外问题正确拒答，也视为 faithful。

局限：

- 它不是严格的 LLM-as-a-judge。
- 更严格可以接 RAGAS 或 DeepEval。

### 9.10 Answer Accuracy Proxy

含义：

> 回答和参考答案之间的关键词重叠比例。

它是低成本本地指标。

优点：

- 不需要额外 LLM。
- 可复现。
- 适合比较不同检索策略的趋势。

局限：

- 不真正理解语义。
- 对抽取式长答案不完全公平。

所以面试中要说：

> Answer Accuracy Proxy 是自动化粗评指标，主要用于版本间趋势比较；最终仍需要人工抽样或 LLM judge。

### 9.11 Latency p50 / p95

含义：

- p50：一半请求低于这个耗时。
- p95：95% 请求低于这个耗时。

为什么它影响最终模型选择：

- bge-base 质量略高。
- bge-small 延迟明显低。
- 核心指标持平时，部署应选择更低延迟模型。

### 9.12 Index Build Time

含义：

> 构建向量索引耗时。

full 实验中 bge-base 构建更慢，因为模型更大。

---

## 10. 当前真实实验结论怎么讲

推荐讲法：

> 我没有直接把最终方案写死，而是设计了 232 条制度问答评估集，从无检索 baseline 开始，依次比较整文档检索、固定窗口分块、Markdown 标题分块、纯向量检索、BM25+向量混合检索、RRF 融合、低置信拒答和不同 embedding 模型。实验发现，单纯向量检索不如 BM25 稳，标题分块能显著提升引用准确率，低置信拒答能把知识库外拒答准确率提升到 1.0。embedding 对比中 bge-base 质量略高，但相对 bge-small 提升很小，而延迟明显更高，所以最终选择 bge-small + BM25 + RRF + 拒答门控作为部署链路。

简历数字：

```text
Answer Accuracy Proxy: 0.000 -> 0.570
Hit@5: 0.000 -> 0.990
Citation Accuracy: 0.095 -> 0.983
Refusal Accuracy: 0.000 -> 1.000
```

注意：

- 不要说“训练了大模型”。
- 应该说“构建评估集并迭代优化 RAG 检索和生成约束链路”。
- 如果说模型选择，要说明 bge-base 也跑了，但因为收益/延迟权衡没有选。

---

## 11. 常见问题与排查

### 11.1 为什么页面显示旧实验结果

可能原因：

- Streamlit Cloud 还没 redeploy。
- 本地 Streamlit 缓存旧 JSON。
- 浏览器页面没刷新。

现在 `app.py` 已经加入文件修改时间作为 cache key，一般重新跑实验后刷新页面即可。

如果是 Streamlit Cloud：

1. 确认代码已经 push 到 GitHub。
2. 等 Cloud 自动 redeploy。
3. 必要时点击 Reboot app。

### 11.2 为什么 V4 曾经显示 None

之前是因为 full 实验用离线缓存跑，bge-base/e5 没有缓存，所以被 skipped。

现在已改成：

- `--full` 默认在线严格跑。
- bge-small、bge-base、e5 都已成功完成。
- 离线 skipped 只用于缓存复现，不用于最终结论。

### 11.3 为什么 local-hashing 还在报告里

它用于 quick baseline。

意义：

- 说明没有真实模型时也能复现一条向量链路。
- 作为对照，证明真实 embedding 更有价值。

但它不是最终 embedding 选型。

### 11.4 为什么不是 bge-base

因为最终决策不是只看一个准确率。

实验结果：

- bge-base Answer Accuracy Proxy 最高。
- bge-small 与 bge-base 在 Hit@5、Citation Accuracy、Refusal Accuracy 上持平。
- bge-small p95 延迟明显更低。

因此部署选择 bge-small。

### 11.5 为什么 V7 没选

V7 加了 query rewrite 和 metadata hint。

实验发现它会误导某些相似制度召回，例如把访客安全问题导向行政接待制度。

所以结论是：

> 规则增强要通过实验验证，不是越多越好。

---

## 12. 推荐学习顺序

如果你要快速掌握这个项目，建议按这个顺序读：

1. `README.md`：先看项目定位和最终故事。
2. `data/policies/`：看 2-3 篇制度，理解知识库长什么样。
3. `data/eval/eval_cases.jsonl`：看评估问题怎么设计。
4. `smart_office_rag/documents.py`：理解 metadata 和分块。
5. `smart_office_rag/indexing.py`：理解 embedding 和 FAISS。
6. `smart_office_rag/retrieval.py`：理解 BM25、向量检索、RRF。
7. `smart_office_rag/generator.py`：理解 LLM 生成和抽取式兜底。
8. `smart_office_rag/pipeline.py`：串起完整流程。
9. `evaluate.py`：理解单次评估。
10. `run_experiments.py`：理解真实迭代实验。
11. `docs/EXPERIMENT_REPORT.md`：背熟面试里的实验故事。
12. `app.py`：理解页面如何展示这些能力。

---

## 13. 面试讲解模板

可以这样讲：

> 这个项目是在 all-in-rag 思路基础上，结合企业内部制度问答场景重新设计的数据、文档结构、评估集和展示系统。我没有直接用最终方案，而是先构造 30 篇模拟制度和 232 条评估问题，从无检索 LLM baseline 开始，逐步验证整文档检索、固定窗口分块、Markdown 标题分块、纯向量、BM25、RRF 混合检索、低置信拒答和不同 embedding 模型。实验发现标题分块能提升引用准确率，BM25+向量+RRF 能提升召回稳定性，低置信拒答能把知识库外问题拒答准确率提升到 1.0。embedding 对比中 bge-base 质量略高，但 bge-small 在核心指标持平下延迟更低，所以最终选择 bge-small + BM25 + RRF + 拒答门控。系统最终支持 Streamlit 展示回答、引用、检索片段、分数和实验历程。

最重要的三个亮点：

1. 有完整 RAG 工程链路，不只是调 API。
2. 有真实可复现实验，不是拍脑袋选方案。
3. 有业务风控意识，包括引用溯源、拒答和高风险流程提醒。
