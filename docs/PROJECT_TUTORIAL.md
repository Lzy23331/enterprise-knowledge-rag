# SmartOfficeRAG 项目教程与学习说明

这份文档是 SmartOfficeRAG 的主教程，面向项目作者、面试讲解者和后续维护者。它不是只告诉你“怎么运行”，而是按文件夹顺序解释：项目里有哪些内容、哪些是检索知识库、哪些是代码、RAG 链路如何从文档加载走到分块、索引、检索、生成和评估。

项目路径：

```text
D:\projects\enterprise-knowledge-rag
```

一句话概括：

> SmartOfficeRAG 是一个面向企业内部制度/政策咨询场景的 RAG 问答助手。它基于自制模拟企业制度文档，完成 Markdown/PDF 多格式接入、结构化 metadata、正式条款分块、embedding 向量化、FAISS/NumPy 向量索引、BM25 关键词检索、RRF 混合召回、低置信拒答、引用溯源、Streamlit 展示和可复现实验评估。

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
├── requirements-pdf-advanced.txt
├── README.md
├── DEPLOYMENT.md
├── eval_report.json
├── eval_report.md
├── data/
│   ├── policies/
│   ├── policies_pdf/
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

最重要的归类：

| 类别 | 路径 | 用途 |
| --- | --- | --- |
| Markdown 知识库文档 | `data/policies/*.md` | 30 篇结构化 Markdown 制度，使用 front matter metadata |
| PDF 知识库文档 | `data/policies_pdf/*.pdf` | 15 篇正式制度 PDF，使用 sidecar metadata |
| PDF metadata | `data/policies_pdf/*.metadata.json` | 给 PDF 补充 doc_id、部门、风险等级、版本、SLA 等结构化字段 |
| 评估集 | `data/eval/*.jsonl` | Markdown + PDF 的检索、引用、拒答和答案质量测试题 |
| 核心 RAG 代码 | `smart_office_rag/` | 文档加载、分块、索引、检索、生成、总控 |
| Web 展示 | `app.py` | Streamlit 页面入口 |
| 单次评估 | `evaluate.py` | 跑当前最终链路的评估 |
| 迭代实验 | `run_experiments.py` + `experiments/` | 跑 V0-V7 版本对比 |
| 数据生成 | `scripts/generate_enterprise_dataset.py`、`scripts/generate_pdf_policies.py` | 生成 Markdown 制度、PDF 制度和评估样本 |
| 报告文档 | `eval_report.*`、`docs/EXPERIMENT_REPORT.md` | 展示评估和实验结果 |

---

## 2. 根目录文件说明

### 2.1 `app.py`

`app.py` 是当前 Streamlit Web Demo 的主入口，也是部署到 Streamlit Cloud 时使用的入口文件。

它负责：

- 初始化 `EnterpriseKnowledgeRAG`。
- 展示制度文档数、chunk 数、评估指标和实验指标。
- 提供部门、流程类型、风险等级过滤器。
- 接收用户问题并调用 `rag.ask(question, filters=filters)`。
- 展示回答、引用来源、检索片段、检索分数、拒答原因和端到端耗时。
- 展示离线评估报告和研发迭代实验历程。

你需要记住：

> `app.py` 是展示层，不实现 RAG 算法。真正的文档加载、检索、排序、拒答和生成都在 `smart_office_rag/` 里。

页面读取两个报告：

```text
eval_report.json
experiments/results/experiment_report.json
```

`app.py` 读取报告时会使用文件修改时间作为 cache key。这样重新跑评估或实验后，Streamlit 刷新页面能读到新结果。

### 2.2 `app_full.py`

这是早期的本地完整版 Streamlit 入口，保留作历史参考。当前主入口是 `app.py`。

### 2.3 `cli.py`

命令行测试入口：

```powershell
.\.venv\Scripts\python.exe cli.py "涉及客户数据导出时需要注意什么？"
```

适合用来快速验证某个问题能否召回正确制度。

### 2.4 `evaluate.py`

`evaluate.py` 是单次评估脚本。它读取：

```text
data/eval/*.jsonl
```

输出：

```text
eval_report.json
eval_report.md
```

现在它会同时读取原 Markdown 评估集和新增 PDF 评估集，而不是只读 `eval_cases.jsonl`。

当前评估规模：

| 项目 | 数量 |
| --- | ---: |
| 制度文档 | 57 |
| Markdown 制度 | 30 |
| baseline PDF 制度 | 15 |
| medium/hard 长 PDF 制度 | 12 |
| baseline chunk | 833 |
| all-layer chunk | 1331 |
| 评估样本 | 468 |
| baseline 评估样本 | 324 |
| medium/hard 评估样本 | 144 |

### 2.5 `run_experiments.py`

这是研发迭代实验入口。它读取：

```text
experiments/configs/*.json
```

并生成：

```text
docs/EXPERIMENT_REPORT.md
experiments/results/experiment_report.json
experiments/results/experiment_report.csv
```

支持：

```powershell
.\.venv\Scripts\python.exe run_experiments.py --quick
.\.venv\Scripts\python.exe run_experiments.py --full
```

区别：

- `--quick`：跑轻量可复现实验，包括 V0、V1、V2、V3、V4 local-hashing、V5、V6、V7。
- `--full`：默认从本地 Hugging Face 缓存加载真实 embedding 模型，完整对比 bge-small、bge-base、multilingual-e5。

严谨口径：

- `--quick` 可以证明链路、指标和失败样本分析是否正常。
- `--full` 才能支撑真实 embedding 模型选型。
- 当前项目已验证三个模型可从 `.cache/huggingface` 稳定加载；如果换机器后缓存缺失，脚本会失败或标记 skipped，项目不会伪造模型对比结果。

### 2.6 `run_web_demo.py`

本地启动 Streamlit 的便利脚本：

```powershell
.\.venv\Scripts\python.exe run_web_demo.py
```

它会设置本地向量相关环境变量并启动 `app.py`。

### 2.7 `requirements.txt`

轻量部署依赖，主要给 Streamlit Cloud 使用。包含：

```text
streamlit
langchain-core
langchain-community
pypdf
rank_bm25
python-dotenv
openai
numpy
```

其中 `langchain-community + pypdf` 用来支持默认 PDF 解析，也就是 `PyPDFLoader`。

### 2.8 `requirements-full.txt`

本地完整向量体验依赖。当前包含：

```text
faiss-cpu
sentence-transformers
reportlab
rank_bm25
openai
numpy
streamlit
langchain-core
langchain-community
pypdf
```

注意：它不包含 `unstructured[pdf]`。这是有意设计，避免复杂 PDF 依赖污染主环境。

### 2.9 `requirements-pdf-advanced.txt`

可选复杂 PDF 解析依赖。只有你要实验 `UnstructuredPDFLoader` 处理扫描件、复杂表格或版式 PDF 时才安装：

```powershell
.\.venv\Scripts\python.exe -m pip install --prefer-binary -r requirements-pdf-advanced.txt
```

本项目当前正式 PDF 是数字文本制度，所以主链路选择 `PyPDFLoader`。

### 2.10 `README.md`

项目 GitHub 首页说明，适合快速了解业务目标、核心链路、数据规模、运行方式和简历表述。

### 2.11 `eval_report.json` 和 `eval_report.md`

单次评估结果：

- `eval_report.json`：给页面和程序读取。
- `eval_report.md`：给人看。

---

## 3. `data/`：知识库与评估集

### 3.1 `data/policies/`：Markdown 检索知识库

这里有 30 篇结构化 Markdown 制度，覆盖 HR、财务、IT、信息安全、行政、法务、采购、内审和运营。

每篇制度顶部都有 front matter：

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

正文通常使用 Markdown 标题：

```markdown
# 制度标题

## 适用对象
## 办理条件
## 办理步骤
## 所需材料
## 审批 SLA 与例外流程
## 注意事项
## 常见问题
```

这些标题会直接影响分块和引用来源。

### 3.2 `data/policies_pdf/`：正式 PDF 检索知识库

这是本轮升级的重点。当前目录下有 15 份正式企业制度 PDF，以及 15 个同名 `.metadata.json` sidecar 文件。

这些 PDF 不是把 Markdown 转成 PDF，也不是旧 5 份短文档的延长版，而是独立生成的新制度资料，覆盖：

| doc_id | 制度标题 | 主要场景 |
| --- | --- | --- |
| `PDF-HR-HANDBOOK-2026` | 员工手册 | 综合制度、跨章节问答 |
| `PDF-HR-ATT-2026` | 员工考勤管理制度 | 迟到、打卡、弹性工作 |
| `PDF-HR-LEAVE-PDF-2026` | 员工休假管理办法 | 年假、病假、婚假、试用期差异 |
| `PDF-FIN-EXP-2026` | 费用报销管理制度 | 金额、票据、审批 |
| `PDF-SEC-INFO-2026` | 信息安全管理制度 | 账号、权限、客户数据 |
| `PDF-HR-PERF-2026` | 绩效考核管理办法 | 评分、周期、申诉 |
| `PDF-HR-ONOFF-2026` | 入离职流程说明 | 入职、离职、资产归还 |
| `PDF-HR-REMOTE-2026` | 远程办公与异地协作安全规范 | 远程申请、设备、数据安全 |
| `PDF-IT-OSS-2026` | 开源软件引入与许可证合规规范 | 开源准入、许可证合规 |
| `PDF-AI-USAGE-2026` | 生成式 AI 工具使用与内容审核规范 | AI 使用、敏感信息、审核 |
| `PDF-LEGAL-RETENTION-2026` | 业务记录留存与销毁管理规范 | 留存年限、销毁审批 |
| `PDF-OPS-CS-QUALITY-2026` | 客户服务话术质检与升级处理规范 | 质检、投诉升级 |
| `PDF-PROC-PURCHASE-2026` | 采购申请与供应商管理制度 | 采购、供应商、比价 |
| `PDF-SEC-DATAEXPORT-2026` | 数据导出与外发审批规范 | 数据导出、脱敏、跨部门审批 |
| `PDF-OPS-BCP-2026` | 业务连续性与应急演练制度 | BCP、演练、应急恢复 |

每份 PDF 的正式结构包括：

- 公司名称。
- 制度编号。
- 版本号。
- 发布日期。
- 生效日期。
- 适用范围。
- 修订记录表。
- 正文条款。
- 附件清单表。
- 审批流程表。
- 解释权归属。
- 页眉、页脚、页码、密级。

PDF 正文使用正式制度格式：

```text
第一章 总则
第一条 为规范员工考勤管理，维护正常工作秩序，根据公司实际情况，制定本制度。
第二条 本制度适用于公司全体正式员工、试用期员工及实习生。
```

它不再包含：

```text
---
# 标题
## 二级标题
- 列表项
```

### 3.3 PDF sidecar metadata

每个 PDF 旁边都有一个同名 metadata 文件：

```text
data/policies_pdf/attendance_policy_2026.pdf
data/policies_pdf/attendance_policy_2026.metadata.json
```

sidecar 至少包含：

```json
{
  "doc_id": "PDF-HR-ATT-2026",
  "title": "员工考勤管理制度",
  "department": "HR",
  "process_type": "考勤管理",
  "risk_level": "中",
  "owner": "人力资源中心",
  "system": "人力资源服务平台",
  "form_id": "HR-ATT-F-001",
  "approval_sla": "考勤异常申诉应在三个工作日内提交",
  "version": "V2.1",
  "effective_date": "2026-02-01",
  "source_type": "pdf"
}
```

为什么用 sidecar：

- 真实企业 PDF 的结构化字段常来自 OA、DMS 或台账，不一定可靠地写在正文里。
- PDF 抽文本对字体、分页、表格很敏感，不能依赖正文 front matter。
- sidecar 可以稳定提供检索过滤、引用、评估需要的字段。

PDF loader 会在 sidecar 基础上继续补充解析质检字段：

| 字段 | 含义 |
| --- | --- |
| `page_count` | PDF 页数 |
| `extracted_page_count` | 成功抽出文本的页数 |
| `text_length` | 合并后的正文字符数 |
| `avg_chars_per_page` | 平均每页抽取字符数 |
| `has_sidecar_metadata` | 是否读取到同名 metadata JSON |
| `missing_required_metadata` | 缺失的关键 metadata 字段 |
| `extraction_quality` | `ok`、`empty_text`、`partial_text`、`low_text_density` 或 `metadata_incomplete` |

这一步的意义是：PDF 虽然是非结构化正文，但进入 RAG 链路前会先经过“可观测的接入质检”。如果将来接入扫描件、空白页、错误 PDF 或 metadata 缺失文件，系统能在 loader 层暴露问题，而不是等到检索失败后才发现。

### 3.4 `data/eval/`：评估集

现在评估脚本读取目录下所有 JSONL：

```text
data/eval/eval_cases.jsonl
data/eval/pdf_eval_cases.jsonl
```

`eval_cases.jsonl` 是原 Markdown 评估集；`pdf_eval_cases.jsonl` 是新增 PDF 专属评估集，覆盖事实型、流程型、材料型、时限型、金额/阈值型、例外条件型、跨文档引用型、版本差异型、拒答型。

一条评估样本长这样：

```json
{
  "id": "hr_handbook_2026_sla",
  "question": "员工手册的审批或办理时限是什么？",
  "expected_doc_ids": ["PDF-HR-HANDBOOK-2026"],
  "expected_sections": ["审批流程"],
  "reference_answer": "标准办理时限为：员工手册争议解释应在五个工作日内反馈。",
  "question_type": "PDF-时限型",
  "department": "HR",
  "should_refuse": false
}
```

字段解释：

| 字段 | 含义 |
| --- | --- |
| `id` | 评估样本 ID |
| `question` | 用户问题 |
| `expected_doc_ids` | 正确制度文档 |
| `expected_sections` | 期望命中的章节或条款 |
| `reference_answer` | 参考答案，用于答案正确性 proxy |
| `question_type` | 问题类型 |
| `department` | 相关部门 |
| `should_refuse` | 是否应该拒答 |

---

## 4. `smart_office_rag/`：核心 RAG 代码

### 4.1 `types.py`

定义项目内部统一使用的 `Document` 类型：

```python
try:
    from langchain_core.documents import Document
except Exception:
    ...
```

如果当前环境安装了 `langchain-core`，项目使用 LangChain 标准 `Document`。如果没有安装，会回退到轻量 dataclass，保证基础功能仍能跑。

推荐理解：

> 后续所有 Markdown、PDF、chunk、检索结果都会统一归一化为 LangChain Document：`page_content` 放正文，`metadata` 放结构化信息。

### 4.2 `config.py`

集中管理路径、模型和环境变量。关键配置包括：

```python
data_path = PROJECT_ROOT / "data" / "policies"
pdf_data_path = PROJECT_ROOT / "data" / "policies_pdf"
pdf_loader_mode = os.getenv("SMARTOFFICE_PDF_LOADER", "pypdf")
index_path = PROJECT_ROOT / "vector_index"
embedding_model = os.getenv("SMARTOFFICE_EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
top_k = 5
use_vector_index = os.getenv("SMARTOFFICE_USE_VECTOR", "1") == "1"
```

PDF 默认 loader 是 `pypdf`，也就是 `PyPDFLoader`。

### 4.3 `loaders.py`

多格式文档加载层。核心类：

```python
MarkdownPolicyLoader
PDFPolicyLoader
MultiFormatPolicyLoader
```

#### MarkdownPolicyLoader

加载：

```text
data/policies/*.md
```

处理步骤：

1. 读取 Markdown 原文。
2. 解析顶部 front matter。
3. 将 front matter 写入 `Document.metadata`。
4. 将正文写入 `Document.page_content`。
5. 补充 `source_type=markdown`、`loader=MarkdownPolicyLoader`、`chunk_type=parent`。

这里没有直接用 `UnstructuredMarkdownLoader`，因为当前 Markdown 已有稳定 front matter，而且项目需要精确控制企业业务 metadata。

#### PDFPolicyLoader

加载：

```text
data/policies_pdf/*.pdf
```

默认使用：

```python
from langchain_community.document_loaders import PyPDFLoader
```

处理步骤：

1. 使用 `PyPDFLoader` 按页抽取 PDF 文本。
2. 合并同一 PDF 的页面文本为一篇 parent document。
3. 读取同名 `.metadata.json`。
4. 用 sidecar metadata 覆盖和补全文档字段。
5. 记录实际使用的 loader：`loader=PyPDFLoader`。
6. 补充 `source_type=pdf`、`page_numbers`、`source_file`、`chunk_type=parent`。

如果显式设置 `SMARTOFFICE_PDF_LOADER=unstructured`，项目会尝试使用 `UnstructuredPDFLoader`，但它是可选增强，不是当前主链路。loader metadata 会记录实际使用的 loader，而不是请求模式，方便检查是否真的用了 PyPDFLoader 或 UnstructuredPDFLoader。

#### MultiFormatPolicyLoader

把 Markdown 和 PDF 合并：

```text
MarkdownPolicyLoader(data/policies)
  ↓
PDFPolicyLoader(data/policies_pdf)
  ↓
List[Document]
```

这一步之后，后续分块、embedding、BM25、RRF、生成和引用都只处理统一的 `Document`。

### 4.4 `documents.py`

负责父文档加载和文本分块。核心类：

```python
PolicyDocumentLoader
```

支持五种分块策略：

| 策略 | 用途 |
| --- | --- |
| `whole_document` | V1 baseline，整篇文档作为一个 chunk |
| `fixed_window` | V2 baseline，固定长度滑窗 |
| `recursive_character` | V2R/V4-recursive/V6-recursive，按段落、换行、句号、分号、逗号等层级递归切分 |
| `markdown_headers` | 主策略，对 Markdown 用标题分块，对 PDF 用正式章条分块 |
| `semantic` | V3S/V4-semantic/V6-semantic，先按结构单元切，再用 bge-small 合并相邻语义相近单元 |

Markdown 分块识别：

```text
# 制度标题
## 办理步骤
## 所需材料
### 常见问题
```

PDF 正式条款分块识别：

```text
第一章 总则
第二章 管理要求
第一条 ...
第二条 ...
附件一 ...
附表一 ...
审批流程
修订记录
典型场景与处理口径
监督检查矩阵
解释权归属
```

PDF chunk 会维护 `section_path`、`section_type`、`chapter_no`、`article_no` 等语义字段，例如：

```text
第五章 异常申诉与月度结算 / 第十八条 考勤异常申诉应在异常发生后三个工作日内提交
```

页面引用会显示成类似：

```text
《员工考勤管理制度》第五章 异常申诉与月度结算 / 第十八条 考勤异常申诉应在异常发生后三个工作日内提交...
```

这比只显示“第 2 页”更适合制度问答，因为用户真正关心的是条款依据。

当前 PDF chunk 的 `section_type` 包括：

| section_type | 含义 |
| --- | --- |
| `chapter` | 正文章节 |
| `article` | 具体制度条款 |
| `approval_flow` | 审批流程 |
| `revision_record` | 修订记录 |
| `appendix` | 附件 |
| `appendix_table` | 附表 |
| `scenario_notes` | 典型场景与处理口径 |
| `control_matrix` | 监督检查矩阵 |
| `explanation` | 解释权归属 |

#### 递归字符分块

`recursive_character` 是 LangChain 里很常见的通用分块思路。本项目实现了项目内版本，递归分隔符顺序是：

```text
空行 -> 换行 -> 句号 -> 分号 -> 逗号 -> 空格 -> 单字符兜底
```

它比固定窗口更自然，因为会优先沿段落和句子边界切，不会机械地每 900 个字符切一刀。实验里它对应：

```text
V2R bm25_recursive_character_chunk
V4-recursive vector_bge_small_recursive_faiss
V6-recursive hybrid_bge_small_recursive_guarded
```

#### 语义分块

`semantic` 的流程是：

```text
先按 Markdown 标题 / PDF 章条切成基础单元
  ↓
用 BAAI/bge-small-zh-v1.5 对每个基础单元编码
  ↓
计算相邻单元 cosine similarity
  ↓
相似度高于阈值且合并后不超过最大长度时合并
```

当前默认参数：

```text
semantic_similarity_threshold = 0.72
semantic_max_chunk_size = 1200
semantic_embedding_model = BAAI/bge-small-zh-v1.5
```

它对应：

```text
V3S bm25_semantic_chunk
V4-semantic vector_bge_small_semantic_faiss
V6-semantic hybrid_bge_small_semantic_guarded
```

### 4.5 `indexing.py`

负责 embedding、向量索引构建和向量检索后端。

当前项目要区分两个概念：

```text
向量检索库：FAISS / NumPy
向量数据库服务：Milvus / Chroma / PGVector / Elasticsearch 等
```

本项目当前没有接入独立向量数据库服务，主链路使用的是本地 FAISS 向量索引；NumPy 只作为轻量 baseline 和 fallback 实验后端。

#### 当前真实使用的向量后端

| 后端 | 使用位置 | 作用 |
| --- | --- | --- |
| `FAISS` | full 实验和最终主链路 | 本地高性能向量检索库 |
| `NumPy` | quick baseline / local-hashing 实验 | 零服务依赖的矩阵乘法检索 |

代码里对应：

```python
if faiss is not None and len(vectors):
    self.index = faiss.IndexFlatIP(vectors.shape[1])
    self.index.add(vectors)
```

如果 FAISS 可用，`VectorStore` 会创建 `faiss.IndexFlatIP`；如果实验配置指定 `vector_backend=numpy`，则把 `vectorstore.index` 置空，检索时走：

```python
scores = self.vectorstore.vectors @ query_vector
ranked_indices = np.argsort(scores)[::-1]
```

这里的 `IndexFlatIP` 表示 flat inner product search，也就是不做近似压缩、不做聚类，直接对所有向量做精确内积检索。由于当前 sentence-transformers 调用里设置了 `normalize_embeddings=True`，向量已经归一化，所以 inner product 基本等价于 cosine similarity。

#### 为什么 FAISS 适合当前项目

当前知识库规模是：

```text
制度文档：45 份
chunk：833 个
评估样本：324 条
```

这个规模下，FAISS 的优势很明显：

- 不需要单独启动数据库服务。
- 可以直接在本地和 Streamlit demo 中运行。
- 安装 `faiss-cpu` 后即可使用。
- 对几百到几千个 chunk 来说，检索足够快。
- 和现有 `sentence-transformers + NumPy vectors` 代码衔接简单。
- 方便在实验中固定其他变量，只比较 embedding、chunk 和检索策略。

当前最终主链路是：

```text
BAAI/bge-small-zh-v1.5 + FAISS + BM25 + RRF + 低置信拒答
```

对应实验：

```text
V6-bge-small hybrid_bge_small_faiss_guarded
```

#### NumPy 在项目里的定位

NumPy 不是最终向量库选择，而是轻量 baseline：

- `local-hashing + NumPy` 可以在没有真实 embedding 模型时快速跑通链路。
- 适合 quick 实验和单元回归。
- 可以验证“向量召回”这个流程是否工作。
- 不能作为最终效果结论，因为 `local-hashing` 不是真实语义 embedding。

严谨口径：

> `local-hashing + NumPy` 是工程 fallback 和可复现 baseline；简历和面试里讲最终 embedding/向量检索效果时，应以 `run_experiments.py --full` 中真实 sentence-transformers + FAISS 的结果为准。

#### 有没有必要接入其他向量数据库

目前暂时不建议把 Milvus、PGVector、Elasticsearch 或 Chroma 接入主链路。原因不是这些工具不好，而是当前项目目标和数据规模还不需要。

| 方案 | 更适合的场景 | 当前项目是否需要 |
| --- | --- | --- |
| FAISS | 本地实验、离线评估、中小规模向量检索、简历项目 demo | 需要，当前主链路 |
| NumPy | baseline、教学、fallback、无依赖快速回归 | 需要，作为 baseline |
| Chroma | LangChain 原型、本地持久化、希望有 collection/metadata API | 可选增强，不是必须 |
| Milvus | 百万级向量、分布式、高并发、多租户生产服务 | 当前过重 |
| PGVector | 企业已有 PostgreSQL，希望结构化数据和向量统一存储 | 当前没有数据库后端 |
| Elasticsearch | 企业已有 ES，想结合 BM25、过滤和向量检索 | 可作为企业选型，不适合本地简历 demo 主链路 |

如果以后要继续做“向量数据库优化”，推荐顺序是：

1. 保留 FAISS 作为默认主链路。
2. 增加 Chroma 作为本地持久化向量库对比，因为它和 LangChain 生态贴近，部署成本低。
3. 只在文档中分析 Milvus / PGVector / Elasticsearch 的业务选型，不强行本地部署。
4. 如果项目升级成后端服务，再考虑 PGVector 或 Elasticsearch，因为它们更贴近企业系统集成。

#### 面试中怎么回答向量库选型

可以这样讲：

> 当前项目主链路使用 FAISS，不是独立向量数据库服务。原因是项目规模是 45 份制度、833 个 chunk，本地 FAISS 已经能提供足够快的精确向量检索，而且部署简单、适合 Streamlit demo 和离线评估。NumPy 只作为 quick baseline，用来保证没有完整向量依赖时也能回归链路。我没有强行接入 Milvus 或 PGVector，因为那会引入额外服务部署和数据迁移复杂度，但对当前规模的召回效果帮助有限。

如果面试官问“为什么不用 Milvus”，可以回答：

> Milvus 更适合百万级向量、分布式部署、高并发和多租户场景。当前项目只有几百个 chunk，用 Milvus 会让部署复杂度超过收益，所以我把它作为企业生产扩展选项，而不是当前 demo 主链路。

如果面试官问“为什么不用 PGVector”，可以回答：

> PGVector 适合企业已有 PostgreSQL，并且希望把制度 metadata、权限、审计和向量放在同一个数据库里。当前项目没有后端数据库，也没有多用户权限系统，所以先用 FAISS 保持本地可复现。如果后续做成企业内部服务，PGVector 是很自然的升级方向。

如果面试官问“为什么不用 Elasticsearch”，可以回答：

> Elasticsearch 的优势是 BM25、结构化过滤和生产级搜索生态。如果企业原本就有 ES，把制度搜索放进去很合理。但本项目已经自己实现了 BM25 + 向量 + RRF，且数据规模很小，所以没有为了简历 demo 引入一套 ES 服务。

如果面试官问“为什么不用 Chroma”，可以回答：

> Chroma 很适合 LangChain 原型和本地持久化向量库，确实可以作为下一步轻量对比。但当前项目的重点是 RAG 评估闭环、分块、embedding 和混合检索策略，FAISS 已经能满足主链路；Chroma 可以作为增强实验，而不是必须项。

### 4.6 `retrieval.py`

负责检索和融合排序。核心策略：

| 检索方式 | 作用 |
| --- | --- |
| `keyword_only` | V1 baseline，简单关键词 |
| `bm25_only` | V2/V3，用 BM25 验证分块效果 |
| `vector_only` | V4，验证纯向量召回 |
| `hybrid_rrf` | V5/V6/V7，BM25 + vector + RRF |

为什么混合检索：

- BM25 擅长制度编号、系统名、表单号、金额阈值等精确词。
- 向量检索擅长同义表达和自然语言问法。
- RRF 用排名融合，降低单一路径出错的风险。

### 4.7 `generator.py`

负责答案生成。

两种模式：

- 有 LLM API key：调用 DeepSeek/OpenAI-compatible API。
- 无 API key：使用本地抽取式模板回答。

回答会尽量包含：

- 结论。
- 处理步骤。
- 所需材料。
- 审批时限。
- 风险注意事项。
- 引用来源。

高风险制度会额外提示审批、留痕、责任部门和不得绕过系统流程。

### 4.8 `pipeline.py`

RAG 总控层。核心类：

```python
EnterpriseKnowledgeRAG
```

初始化流程：

```text
MarkdownPolicyLoader + PDFPolicyLoader
  ↓
MultiFormatPolicyLoader
  ↓
LangChain Document 归一化
  ↓
PolicyDocumentLoader 分块
  ↓
build/load vector index
  ↓
HybridRetriever
  ↓
AnswerGenerator
```

问答流程：

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

---

## 5. `scripts/`：模拟数据生成

### 5.1 `scripts/generate_enterprise_dataset.py`

生成原始 Markdown 制度和 Markdown 评估样本。

运行：

```powershell
.\.venv\Scripts\python.exe scripts\generate_enterprise_dataset.py
```

注意：它会重写 `data/policies/` 和 `data/eval/eval_cases.jsonl`。

### 5.2 `scripts/generate_pdf_policies.py`

生成本轮升级后的正式 PDF 资料库：

- 15 份正式企业制度 PDF。
- 15 个同名 `.metadata.json` sidecar。
- 1 份 PDF 专属评估集 `data/eval/pdf_eval_cases.jsonl`。

运行：

```powershell
.\.venv\Scripts\python.exe scripts\generate_pdf_policies.py
```

它会替换 `data/policies_pdf/` 下旧 PDF，而不是把现有 Markdown 转 PDF。

生成后的验证标准：

- `data/policies_pdf/` 下有 15 份 PDF 和 15 份 metadata。
- 每份 PDF 约 6-8 页，目前生成结果为 6 页 6 份、7 页 5 份、8 页 4 份。
- PDF 正文没有 `---`、`#`、`##` 等 Markdown 符号。
- PDF 包含封面信息、修订记录、正文条款、附件、审批流程、页眉页脚和表格。
- sidecar metadata 中 `source_type=pdf`。

---

## 6. `experiments/`：真实研发迭代实验

目录：

```text
experiments/
├── configs/
└── results/
```

### 6.1 实验配置

每个 JSON 是一个实验版本，例如：

```json
{
  "id": "V6",
  "name": "hybrid_rrf_with_refusal_gate",
  "stage": "quick",
  "chunk_strategy": "markdown_headers",
  "retriever": "hybrid_rrf",
  "embedding_model": "local-hashing",
  "vector_backend": "numpy",
  "query_rewrite": false,
  "metadata_filter": false,
  "refusal_gate": true,
  "final_candidate": true
}
```

字段解释：

| 字段 | 含义 |
| --- | --- |
| `id` | 版本号，例如 V0、V6 |
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

| 版本 | 策略 | 目的 |
| --- | --- | --- |
| V0 | LLM direct，无知识库 | 暴露不可追溯和不能拒答的问题 |
| V1 | 整文档关键词检索 | 验证最小检索链路 |
| V2 | 固定窗口 + BM25 | 验证简单 chunk 对召回和引用的影响 |
| V3 | Markdown/PDF 结构分块 + BM25 | 验证标题和章条结构是否提升引用 |
| V4 | 纯向量检索 | 验证语义召回单独使用是否稳定 |
| V5 | BM25 + vector + RRF | 验证混合检索收益 |
| V6 | Hybrid RRF + 低置信拒答 | 降低知识库外误答 |
| V7 | Query rewrite + metadata hint | 验证规则增强是否继续提升 |

当前实验结论：

- V0 没有知识库，引用和拒答都很弱。
- V1/V2 能命中文档，但整文档或固定窗口导致引用不精确。
- V3 结构分块显著提升 Citation Accuracy。
- V4 local-hashing 纯向量不稳定，不能作为最终方案。
- V4-bge-small、V4-bge-base、V4-e5 都已通过真实 sentence-transformers + FAISS 跑通，纯向量召回明显强于 local-hashing，但单独使用仍不如混合检索稳定。
- V5/V6 混合检索提升引用，V6 加入拒答门控后 Refusal Accuracy 达到 1.000。
- V6-bge-small、V6-bge-base、V6-e5 在 Hit@5、Citation Accuracy、Refusal Accuracy 上持平；bge-small 的 Answer Accuracy Proxy 最高，且延迟明显低于 bge-base。
- V7 在当前样本下 Hit@5 和 Citation Accuracy 略低，说明规则增强不是越多越好。

### 6.3 当前实验指标

当前 full 实验基于 45 份制度和 324 条评估样本，真实 embedding 模型从本地 Hugging Face 缓存稳定加载：

| Version | Strategy | Answer Acc. | Hit@5 | Citation | Refusal |
| --- | --- | ---: | ---: | ---: | ---: |
| V0 | llm_direct_no_retrieval | 0.000 | 0.000 | 0.074 | 0.000 |
| V1 | keyword_whole_document | 0.382 | 0.997 | 0.188 | 0.042 |
| V2 | bm25_fixed_window | 0.508 | 1.000 | 0.458 | 0.042 |
| V2R | bm25_recursive_character_chunk | 0.553 | 0.983 | 0.474 | 0.083 |
| V3 | bm25_header_chunk | 0.416 | 0.973 | 0.794 | 0.042 |
| V3S | bm25_semantic_chunk | 0.386 | 0.973 | 0.797 | 0.042 |
| V4-local | vector_local_hashing_numpy | 0.221 | 0.783 | 0.332 | 0.000 |
| V4-bge-small | vector_bge_small_zh_faiss | 0.363 | 0.883 | 0.386 | 0.000 |
| V4-bge-base | vector_bge_base_zh_faiss | 0.388 | 0.883 | 0.417 | 0.000 |
| V4-e5 | vector_multilingual_e5_faiss | 0.362 | 0.847 | 0.406 | 0.000 |
| V4-recursive | vector_bge_small_recursive_faiss | 0.500 | 0.943 | 0.343 | 0.000 |
| V4-semantic | vector_bge_small_semantic_faiss | 0.343 | 0.870 | 0.376 | 0.000 |
| V6-local | hybrid_rrf_with_refusal_gate | 0.440 | 0.903 | 0.901 | 1.000 |
| V6-bge-small | hybrid_bge_small_faiss_guarded | 0.476 | 0.903 | 0.901 | 1.000 |
| V6-bge-base | hybrid_bge_base_faiss_guarded | 0.475 | 0.903 | 0.901 | 1.000 |
| V6-e5 | hybrid_multilingual_e5_faiss_guarded | 0.469 | 0.903 | 0.901 | 1.000 |
| V6-recursive | hybrid_bge_small_recursive_guarded | 0.565 | 0.963 | 0.531 | 1.000 |
| V6-semantic | hybrid_bge_small_semantic_guarded | 0.479 | 0.903 | 0.901 | 1.000 |
| V7 | query_rewrite_metadata_guarded | 0.445 | 0.900 | 0.898 | 1.000 |
| V10-sentence-window-vector | vector_bge_small_sentence_window_faiss | 0.294 | 0.833 | 0.393 | 0.000 |
| V10-sentence-window-hybrid | hybrid_bge_small_sentence_window_guarded | 0.398 | 0.907 | 0.904 | 1.000 |
| V11-structured-hybrid | structured_hybrid_bge_small_guarded | 0.487 | 0.880 | 0.880 | 1.000 |
| V12-sentence-structured-hybrid | sentence_structured_hybrid_bge_small_guarded | 0.372 | 0.897 | 0.895 | 1.000 |

#### 6.3.1 最终主链路到底选择了什么

当前项目的最终主链路选择是：

```text
文档加载：
Markdown front matter loader + PDF PyPDFLoader + sidecar metadata

文本分块：
Markdown 标题结构分块 + PDF 正式制度章条结构分块

Embedding：
BAAI/bge-small-zh-v1.5

向量库：
FAISS

检索融合：
BM25 + dense vector retrieval + RRF

生成前控制：
低置信拒答 gate + citation trace
```

对应实验版本是：

```text
V6-bge-small hybrid_bge_small_faiss_guarded
```

也就是说，最终不是选择 `recursive_character`，也不是把 `semantic` 作为主链路，而是选择“制度结构感知分块 + bge-small + FAISS + BM25/RRF + 拒答门控”。

#### 6.3.2 为什么不能只看 Answer Accuracy Proxy

从表面看，`V6-recursive` 的 Answer Accuracy Proxy 是 `0.565`，高于 `V6-bge-small` 的 `0.476`。如果这是一个普通 FAQ 或开放问答项目，只追求“回答内容覆盖更多关键词”，递归分块可能很有吸引力。

但本项目是企业制度问答，业务目标不是“看起来回答得更丰富”，而是：

```text
1. 答案必须来自制度库；
2. 答案必须能追溯到具体制度、章节、条款；
3. 知识库外问题必须拒答；
4. 高风险问题不能靠模型猜测；
5. 员工和支持部门能拿引用结果去复核。
```

因此评估时不能只看 Answer Accuracy Proxy，还要同时看：

| 指标 | 在本项目中的意义 |
| --- | --- |
| Answer Accuracy Proxy | 回答文本是否覆盖参考答案关键词 |
| Hit@5 | 前 5 个召回片段是否命中正确制度 |
| Citation Accuracy | 引用来源是否真的来自预期制度或条款 |
| Refusal Accuracy | 知识库外问题是否能拒答 |
| p95 latency | 线上交互是否稳定、够快 |

在制度问答里，`Citation Accuracy` 和 `Refusal Accuracy` 的权重高于单纯的 Answer Accuracy Proxy。原因很简单：企业内部制度问答的风险主要来自“答错且看起来很像真的”，而不是“回答不够长”。

#### 6.3.3 分块策略对比和取舍

本项目实际对比了三类有代表性的分块策略。

| 分块策略 | 代表实验 | Answer Acc. | Hit@5 | Citation | 结论 |
| --- | --- | ---: | ---: | ---: | --- |
| 固定窗口分块 | V2 | 0.508 | 1.000 | 0.458 | 召回强，但容易切断制度标题和条款边界 |
| 递归字符分块 | V6-recursive | 0.565 | 0.963 | 0.531 | 答案覆盖最好，但引用边界不稳定 |
| 结构感知分块 | V6-bge-small | 0.476 | 0.903 | 0.901 | 引用准确率最高，适合制度问答主链路 |
| 语义分块 | V6-semantic | 0.479 | 0.903 | 0.901 | 效果接近结构分块，但构建阶段多一次 embedding 成本 |

固定窗口分块的逻辑最简单：按固定长度切，例如每 900 个字符一个 chunk，并保留一定 overlap。它的好处是容易实现、chunk 数少、召回速度快；缺点是它不了解制度文档的自然结构，可能把“章节标题”和“具体条款”切开，导致 citation 只能命中文档片段，却很难稳定命中业务上可解释的条款边界。

递归字符分块比固定窗口更自然。它会优先按照空行、换行、句号、分号、逗号等边界切分，所以更不容易在句子中间截断。实验里它的 Answer Accuracy Proxy 最高，说明它确实更擅长保留较完整的上下文，能让回答覆盖更多参考答案关键词。但它的 Citation Accuracy 只有 `0.531`，远低于结构感知分块的 `0.901`。这说明它召回到的内容可能是相关的，但不够稳定地落在正确制度条款上。

结构感知分块是当前主策略。Markdown 制度按标题层级切，PDF 制度按“第一章”“第一条”“附件”“审批流程”等正式制度结构切。它的 Answer Accuracy Proxy 不是最高，但 Citation Accuracy 达到 `0.901`，Refusal Accuracy 达到 `1.000`。这更符合企业政策问答的业务要求：答案可以少一点，但必须有明确依据。

语义分块是增强候选。它先按制度结构得到基础单元，再使用 `BAAI/bge-small-zh-v1.5` 对相邻单元做 embedding，如果相邻内容语义相近且合并后不超过最大长度，就合并为一个更大的 semantic chunk。实验中 `V6-semantic` 的 Answer Accuracy Proxy 为 `0.479`，略高于结构分块的 `0.476`，Citation Accuracy 同样是 `0.901`。这说明语义分块有潜力，但当前收益很小，并且构建索引时需要额外 embedding 计算，所以暂时作为增强候选，不作为默认主链路。

#### 6.3.4 Embedding 模型为什么选 bge-small

Embedding 选型分成两轮。

第一轮先跑通稳定中文基线，确认项目不是依赖 `local-hashing` 兜底，而是真的使用 sentence-transformers + FAISS：

| 模型 | 代表实验 | Answer Acc. | Hit@5 | Citation | Refusal | p95 latency |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| BAAI/bge-small-zh-v1.5 | V6-bge-small | 0.476 | 0.903 | 0.901 | 1.000 | 30.1 ms |
| BAAI/bge-base-zh-v1.5 | V6-bge-base | 0.475 | 0.903 | 0.901 | 1.000 | 56.2 ms |
| intfloat/multilingual-e5-small | V6-e5 | 0.469 | 0.903 | 0.901 | 1.000 | 37.3 ms |

这三个模型在 Hit@5、Citation Accuracy、Refusal Accuracy 上持平，说明进入 hybrid RRF 链路之后，真实 embedding 模型都能稳定支撑语义召回。但 `bge-small` 的 Answer Accuracy Proxy 略高于另外两个模型，并且 p95 延迟明显低于 `bge-base`。所以最终选择 `BAAI/bge-small-zh-v1.5`，不是因为其他模型没跑通，而是因为它在当前中文企业制度数据上达到了更好的效果、速度和资源消耗平衡。

`bge-base` 可以作为更大模型备选，但当前没有带来足够收益；`multilingual-e5-small` 更适合作为多语言场景备选，本项目主要是中文制度问答，因此不作为默认模型。

第二轮从 MTEB/C-MTEB 和主流开源 embedding 模型中增加候选模型，用本项目自己的企业制度评估集复验。新增候选包括：

| 模型 | 选择原因 | 风险点 |
| --- | --- | --- |
| Qwen/Qwen3-Embedding-0.6B | 近期榜单表现强，参数量相对可控 | 需要 `trust_remote_code=True`，延迟更高 |
| BAAI/bge-m3 | 多语言、多粒度、长文本 embedding，适合长 PDF 制度 | 模型更大，索引构建和检索更慢 |
| Alibaba-NLP/gte-Qwen2-1.5B-instruct | MTEB/C-MTEB 高性能候选 | 需要 `trust_remote_code=True`，当前依赖下 encode 失败 |

本轮实验新增两组版本：

```text
V8-*：纯向量检索，观察模型本身语义召回能力。
V9-*：最终 RAG 链路，固定结构分块 + FAISS + BM25 + RRF + 低置信拒答。
```

模型下载与离线复现结果保存在：

```text
docs/EMBEDDING_MODEL_SELECTION.md
```

当前 MTEB 候选模型复验结果：

| 模型 | 代表实验 | Answer Acc. | Hit@5 | Citation | Refusal | p95 latency | 结论 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| BAAI/bge-small-zh-v1.5 | V6-bge-small | 0.476 | 0.903 | 0.901 | 1.000 | 30.1 ms | 默认主模型 |
| Qwen/Qwen3-Embedding-0.6B | V9-qwen3-0.6b | 0.472 | 0.910 | 0.907 | 1.000 | 222.2 ms | Citation 略高，但延迟过高且 Answer 略低 |
| BAAI/bge-m3 | V9-bge-m3 | 0.484 | 0.900 | 0.898 | 1.000 | 111.9 ms | Answer 略高，但 Citation 略低且延迟明显更高 |
| Alibaba-NLP/gte-Qwen2-1.5B-instruct | V9-gte-qwen2-1.5b | skipped | - | - | - | - | 当前依赖下 encode 失败 |

这轮复验说明：MTEB 排名更高的模型不一定在本项目场景里直接替代 `bge-small`。企业制度问答的主指标不是单纯语义相似度，而是“召回正确制度 + 引用准确 + 能拒答 + 延迟可接受”。`Qwen3-Embedding-0.6B` 的 Citation Accuracy 从 `0.901` 小幅提升到 `0.907`，但 p95 延迟从 `30.1 ms` 上升到 `222.2 ms`；`bge-m3` 的 Answer Accuracy Proxy 从 `0.476` 小幅提升到 `0.484`，但 Citation Accuracy 从 `0.901` 降到 `0.898`，p95 延迟升到 `111.9 ms`。因此当前仍保留 `BAAI/bge-small-zh-v1.5` 作为默认主链路 embedding。

##### 为什么从 MTEB 选这些模型

MTEB/C-MTEB 的作用是“帮助筛候选”，不是“直接决定线上模型”。原因是 MTEB 覆盖的是通用检索、分类、聚类、重排序等任务，能反映模型的通用语义表示能力；但本项目是企业内部制度问答，数据形态、问题类型和业务目标都更具体：

```text
数据：正式制度、流程说明、审批规则、金额阈值、版本差异。
问题：员工自然语言提问，经常包含部门、材料、时限、例外条件。
目标：不仅要召回相关文本，还要给出可追溯引用，并对知识库外问题拒答。
```

因此我采用“两阶段选型”：

1. 先看榜单和模型定位，筛出可能有价值的候选。
2. 再放回本项目自己的 324 条评估样本里复验。

这就是为什么候选里既有 `Qwen3-Embedding-0.6B`，也有 `bge-m3` 和 `gte-Qwen2-1.5B-instruct`：

- `Qwen3-Embedding-0.6B`：代表近期榜单强模型，参数量相对可控，用来挑战当前 bge-small。
- `bge-m3`：代表长文本、多语言、多粒度 embedding，用来验证正式 PDF 制度和长条款是否受益。
- `gte-Qwen2-1.5B-instruct`：代表更大、更强但依赖更复杂的高性能候选，用来测试上限和工程风险。

##### 怎么保证不是 fallback 结果

这轮改造专门增加了 `require_real_embedding=true`。它的含义是：如果模型不能真实加载、不能 encode、不能构建向量索引，实验就标记为 `skipped`，绝不退回 `local-hashing`。

同时实验记录了这些字段：

| 字段 | 含义 |
| --- | --- |
| `embedding_load_mode` | 模型是从 online/cache 还是 local cache 加载 |
| `embedding_used_fallback` | 是否使用 fallback |
| `embedding_dimension` | 实际向量维度 |
| `model_load_ms` | 模型加载耗时 |
| `index_build_ms` | 索引构建耗时 |
| `embedding_trust_remote_code` | 是否启用远程模型代码 |

模型验证脚本 `validate_embedding_models.py` 也分成两步：

```text
第一步：允许联网下载模型。
第二步：切回 local-only，用 .cache/huggingface 离线加载复验。
```

只有同时通过下载和离线复现，才说明这个模型在本机实验环境里是稳定可用的。当前 `bge-m3` 和 `Qwen3-Embedding-0.6B` 都通过了；`gte-Qwen2-1.5B-instruct` 下载后在 encode 阶段报 `DynamicCache` 兼容错误，所以没有被当成有效模型结果。

##### 为什么最终没有换成 Qwen3 或 bge-m3

最终是否替换主模型，不看单点指标，而看综合收益。

`Qwen3-Embedding-0.6B` 的结果：

```text
Citation Accuracy: 0.901 -> 0.907
Answer Accuracy Proxy: 0.476 -> 0.472
p95 latency: 30.1 ms -> 222.2 ms
```

它的引用准确率略高，但答案代理准确率略低，延迟约为 bge-small 的 7 倍以上，而且需要 `trust_remote_code=True`。对于企业制度问答来说，这个收益不足以覆盖延迟和依赖风险。

`bge-m3` 的结果：

```text
Answer Accuracy Proxy: 0.476 -> 0.484
Citation Accuracy: 0.901 -> 0.898
p95 latency: 30.1 ms -> 111.9 ms
```

它的答案覆盖略好，但引用准确率略低，延迟约为 bge-small 的 3 到 4 倍。由于制度问答更看重 citation 和可追溯性，所以也不替换默认模型。

`gte-Qwen2-1.5B-instruct` 的结果：

```text
下载：成功
离线加载：能进入加载流程
encode：失败
错误：DynamicCache object has no attribute get_usable_length
```

这说明它在当前 `sentence-transformers / transformers` 依赖组合下不能稳定完成 embedding 编码。即使它在榜单表现很好，也不能写成项目有效结论。

##### 面试中应该怎么讲这部分

可以这样回答：

> 我没有直接因为 MTEB 排名高就替换 embedding，而是把 MTEB 当作候选模型筛选工具。项目先稳定跑通 bge-small、bge-base 和 multilingual-e5，确认真实 sentence-transformers + FAISS 链路可用；之后又加入 Qwen3-Embedding-0.6B、bge-m3 和 gte-Qwen2-1.5B-instruct 做复验。为了避免 fallback 污染结果，我给新实验加了 `require_real_embedding=true`，模型加载或 encode 失败就标记 skipped，不允许退回 local-hashing。最后结果显示，Qwen3 的引用准确率略高但延迟过高，bge-m3 的答案覆盖略高但引用准确率略低且延迟更高，gte-Qwen2 在当前依赖下 encode 失败。因此我最终保留 bge-small 作为默认 embedding，因为它在准确率、引用、拒答、延迟和工程稳定性之间最均衡。

如果面试官问“为什么不选榜单更高的模型”，可以回答：

> 榜单反映通用语义能力，但我的业务场景是企业制度问答，核心不是单纯语义相似度，而是能不能召回正确制度、能不能给出可信引用、能不能拒答知识库外问题，以及线上延迟是否可接受。所以我把榜单模型放到自己的评估集里复验，最终没有盲目选择榜单模型。

如果面试官问“Qwen3 引用准确率更高，为什么不用”，可以回答：

> Qwen3 的 Citation Accuracy 从 0.901 提升到 0.907，提升只有 0.006，但 p95 延迟从 30.1ms 上升到 222.2ms，并且需要 `trust_remote_code=True`。在当前数据规模和 Streamlit 演示部署场景下，这个收益不值得替换默认模型。

如果面试官问“bge-m3 Answer 更高，为什么不用”，可以回答：

> bge-m3 的 Answer Accuracy Proxy 从 0.476 到 0.484，说明答案关键词覆盖略好；但 Citation Accuracy 从 0.901 降到 0.898。企业制度问答里，引用准确性比答案看起来更完整更重要，所以它可以作为长文本或多语言增强候选，但不是当前默认模型。

如果面试官问“gte-Qwen2 跑失败怎么解释”，可以回答：

> 我把它作为高性能候选纳入实验，但当前依赖组合下 encode 阶段出现 `DynamicCache` 兼容错误，所以报告里标记为 skipped。这个处理比 fallback 更严谨，因为我不会把没有真实跑通的模型写进有效结论。

#### 6.3.5 最终权衡结论

最终选择可以这样理解：

```text
如果只追求回答覆盖：
V6-recursive 更强。

如果追求制度问答的可追溯、可解释、可上线：
V6-bge-small 更合适。

如果未来问题更偏长上下文综合问答：
可以继续验证 V6-semantic 或 bge-m3。
```

所以本项目当前主链路选择：

```text
V6-bge-small =
结构感知分块 + BAAI/bge-small-zh-v1.5 + FAISS + BM25 + RRF + 低置信拒答
```

这个选择体现的是工程和业务权衡：不用单一指标决定方案，而是同时考虑问答准确性、引用可信度、拒答能力、延迟和构建成本。对于企业制度问答，“能指出依据”比“回答看起来更完整”更重要。

#### 6.3.6 索引优化：句子窗口检索与结构化检索

在向量库和 embedding 之外，还需要理解“索引方法”。本项目当前主链路不是单纯向量检索，而是：

```text
结构化 chunk 索引
+ FAISS 向量索引
+ BM25 倒排检索
+ RRF 融合排序
+ 主文档上下文补全
+ 低置信拒答
```

这里的“索引优化”关注的是：文档被组织成什么粒度、检索命中什么粒度、生成时补什么上下文、metadata 是否参与排序。

当前已有的索引能力：

| 能力 | 项目实现 | 作用 |
| --- | --- | --- |
| 向量索引 | `FAISS IndexFlatIP` | 找语义相近 chunk |
| 关键词索引 | `BM25Okapi` | 找制度名、表单号、金额、部门等精确词 |
| 结构化 chunk | Markdown 标题 / PDF 章条分块 | 保留制度章节和条款 citation |
| RRF 融合 | vector topN + BM25 topN | 降低单一路径误召回 |
| 主文档补全 | 命中主制度后补同制度相关 chunk | 提高回答完整性 |

这里要区分两个容易混在一起的概念：

| 问题 | 关注点 | 本项目例子 |
| --- | --- | --- |
| 向量数据库选型 | 向量存在哪里、用什么引擎查 | FAISS、NumPy；文档中对比 Milvus、Chroma、PGVector、Elasticsearch |
| 索引优化 | 同样用 FAISS 时，文档怎么切、命中什么粒度、召回后怎么补上下文、metadata 怎么参与排序 | 结构化 chunk、sentence-window、structured boost |

也就是说，本轮不是再换一个向量库，而是在当前稳定的 FAISS 后端上继续优化“索引组织方式”。这样实验更聚焦：变量只放在分块粒度和排序逻辑上，不让向量库差异、embedding 差异、LLM 差异同时混进结果。

为什么还要做索引优化：

- 固定窗口分块实现简单，但经常切断制度条款，citation 不够自然。
- 递归字符分块比固定窗口更符合段落边界，但仍然不理解企业制度里的“章、条、附件、审批流程”。
- 结构感知分块最适合当前制度资料，因为它能保留“制度标题 + 章节 + 条款”的引用路径。
- 但结构化 chunk 有时仍然偏大，向量检索可能被整段里的其他内容干扰。
- 业务 metadata 已经存在，如果完全不用 metadata 参与排序，也会浪费制度库的数据治理成果。

所以本轮新增了两类索引增强实验，分别验证两个假设：

| 假设 | 实验方向 | 预期收益 | 主要风险 |
| --- | --- | --- | --- |
| 检索粒度更细可能更准 | `sentence-window retrieval` | 命中更具体的句子，减少大 chunk 噪声 | 单句上下文太碎，回答不完整 |
| 业务字段参与排序可能更贴近场景 | `structured retrieval` | HR、财务、安全、IT 等场景排序更准 | metadata 判断错会把相似但错误的制度推上来 |

第一类是 `sentence-window retrieval`：

```text
先按标题/章条得到结构单元
再切成句子级 child chunk
检索时命中句子
生成前回填同一 section 的前后句窗口
```

它解决的问题是：如果 chunk 太大，向量检索可能不够精确；如果句子太小，答案上下文又可能不完整。所以 sentence-window 的思想是“检索用小粒度，生成用窗口上下文”。

项目中的实现位置：

| 文件 | 作用 |
| --- | --- |
| `smart_office_rag/documents.py` | 新增 `sentence_window` 分块策略 |
| `smart_office_rag/retrieval.py` | 命中句子后做 sentence-window expansion |
| `experiments/configs/v10_sentence_window_vector.json` | 句子窗口 + 纯向量实验 |
| `experiments/configs/v10_sentence_window_hybrid.json` | 句子窗口 + BM25 + vector + RRF + refusal 实验 |
| `run_experiments.py` | 读取 `sentence_window_size`、`sentence_max_chars`、`sentence_min_chars` 等配置 |

具体流程是：

```text
原始 Markdown/PDF Document
-> 先按 Markdown 标题或 PDF 章条切出结构单元
-> 在结构单元内部按句号、分号、换行等规则切成 sentence child chunk
-> 每个 child chunk 保留 parent_section、section_path、sentence_index、citation
-> 检索阶段只检索 child chunk
-> 生成阶段根据 doc_id + section_path + sentence_index 回填前后句
-> 最终引用仍指向原制度章节/条款
```

这样设计的原因是：如果 citation 直接指向“第 12 个句子”，对业务用户没有意义；企业制度问答更需要看到“《员工考勤管理制度》第二章 考勤规则 / 第六条 迟到与早退处理”这样的依据。所以 sentence-window 只改变检索粒度，不改变最终 citation 的业务表达。

第二类是 `structured retrieval`：

```text
先做 BM25 + vector + RRF
再根据 metadata 做 soft boost
不做强过滤
```

它用到的结构化线索包括：

- `department`
- `process_type`
- `risk_level`
- `section_type`
- `title`
- 问题里的“材料、时限、金额、审批、风险”等意图词

为什么用 soft boost，而不是强过滤：

> 企业员工提问不一定会明确说出部门或制度名称，如果强过滤判断错了，可能直接把正确文档过滤掉。soft boost 更稳妥，它只是给更可能相关的 chunk 加分，而不会让召回为空。

项目中的实现位置：

| 文件 | 作用 |
| --- | --- |
| `smart_office_rag/retrieval.py` | 在 RRF 后计算结构化线索和 `structured_score` |
| `experiments/configs/v11_structured_hybrid.json` | 结构化 chunk + structured boost + hybrid RRF 实验 |
| `experiments/configs/v12_sentence_structured_hybrid.json` | sentence-window + structured boost + hybrid RRF 实验 |
| `run_experiments.py` | 根据实验配置启用 `structured_boost` 或 `structured_hybrid_rrf` |

structured retrieval 的流程是：

```text
用户问题
-> BM25 召回关键词相关 chunk
-> FAISS 召回语义相关 chunk
-> RRF 融合得到基础排序
-> 从问题中识别弱业务线索
-> 根据 chunk metadata 计算 structured_score
-> 用 soft boost 调整排序
-> 输出 answer、citation 和检索解释
```

这里的“弱业务线索”不是复杂的意图识别模型，而是可解释的规则：例如问题里出现“报销、发票、付款”，会倾向财务或采购流程；出现“账号、权限、数据导出、客户信息”，会倾向 IT 或信息安全流程；出现“审批、留痕、复核”，会提高高风险制度相关 chunk 的排序。

为什么不做强过滤，可以用一个例子理解：

> 用户问“客户名单导出需要谁审批”。这个问题表面上像 IT 权限问题，但实际可能同时涉及信息安全制度、数据导出制度、客户服务质检规范和审批留痕要求。如果只按某一个部门强过滤，可能会过滤掉真正应该引用的制度。soft boost 只是排序增强，不会让候选集变空。

新增实验版本：

为了保证实验结论可信，本轮控制了这些变量：

- 使用同一批企业制度资料：Markdown 制度 + 正式 PDF 制度，总计 45 份左右。
- 使用同一套评估集：覆盖事实型、流程型、材料型、时限型、金额阈值型、跨文档型、拒答型等问题。
- 使用同一个已稳定验证的 embedding 主模型：`BAAI/bge-small-zh-v1.5`。
- 使用同一个向量后端：FAISS。
- 使用同一套指标：`Answer Accuracy Proxy`、`Hit@5`、`MRR@5`、`Citation Accuracy`、`Refusal Accuracy`、`p50/p95 latency`。

版本设计如下：

| Version | 实验目的 | 只改变什么 |
| --- | --- | --- |
| V6-bge-small | 当前主链路基线 | 不改变，作为对照组 |
| V10-sentence-window-vector | 单独观察句子级向量召回能力 | 分块粒度变成 sentence child，检索只用 vector |
| V10-sentence-window-hybrid | 观察句子窗口进入完整 hybrid 链路后的效果 | 分块粒度变成 sentence child，仍使用 BM25 + vector + RRF |
| V11-structured-hybrid | 观察 metadata soft boost 是否提升排序 | 分块不变，只在 RRF 后加 structured boost |
| V12-sentence-structured-hybrid | 观察两个增强策略叠加是否更好 | 同时使用 sentence-window 和 structured boost |

| Version | 策略 | Answer Acc. | Hit@5 | Citation | Refusal | p95 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| V6-bge-small | 当前结构化 chunk + hybrid RRF | 0.476 | 0.903 | 0.901 | 1.000 | 57.5 ms |
| V10-sentence-window-vector | 句子窗口 + 纯向量 | 0.294 | 0.833 | 0.393 | 0.000 | 17.7 ms |
| V10-sentence-window-hybrid | 句子窗口 + hybrid RRF | 0.398 | 0.907 | 0.904 | 1.000 | 66.2 ms |
| V11-structured-hybrid | 结构化 soft boost + hybrid RRF | 0.487 | 0.880 | 0.880 | 1.000 | 46.8 ms |
| V12-sentence-structured-hybrid | 句子窗口 + 结构化 soft boost | 0.372 | 0.897 | 0.895 | 1.000 | 68.9 ms |

实验结论：

- `V10-sentence-window-vector` 说明纯句子级向量召回不适合作为主链路：chunk 更细以后，单个句子太碎，Answer 和 Citation 都明显下降。
- `V10-sentence-window-hybrid` 的 Citation Accuracy 从 `0.901` 小幅提升到 `0.904`，但 Answer Accuracy Proxy 从 `0.476` 降到 `0.398`，说明它引用边界略好，但回答完整性下降。
- `V11-structured-hybrid` 的 Answer Accuracy Proxy 从 `0.476` 升到 `0.487`，但 Hit@5 和 Citation 都下降到 `0.880`，说明 metadata boost 有时会把排序推向看似相关但不是期望制度的文档。
- `V12` 同时叠加句子窗口和结构化 boost，结果没有超过 V6，说明增强策略叠加不一定带来收益。

更细地看，失败原因分别是：

| 版本 | 观察到的问题 | 说明 |
| --- | --- | --- |
| V10 sentence vector | Answer 和 Citation 同时下降 | 句子太短，向量召回命中的是局部表达，不一定覆盖完整制度规则 |
| V10 sentence hybrid | Citation 略升但 Answer 明显下降 | BM25 和 RRF 能把引用拉回来，但生成上下文仍然比结构化 chunk 更碎 |
| V11 structured hybrid | Answer 小幅提升但 Hit/Citation 下降 | metadata boost 能提高一些业务相关答案，但也会把相似流程、相似部门的制度推到前面 |
| V12 combined | 两类增强叠加后没有收益 | 句子碎片化和 metadata 误加权会互相放大，不是“功能越多越好” |

因此最终选择 V6 不是因为没有做高级索引，而是因为实验后发现：

- 企业制度问答更依赖完整条款和可追溯 citation，不只是命中某一句话。
- 当前 PDF 制度已经有清晰的“章、条、附件、审批流程”，结构感知 chunk 正好能利用这种格式。
- sentence-window 更适合答案集中在短句里的知识库，比如 FAQ、产品说明、日志摘要；对制度流程类问题不一定占优。
- structured boost 可以作为后续优化方向，但需要更可靠的意图识别和 metadata 标注质量，目前不适合直接替换主链路。
- V6 在 Answer、Citation、Refusal 和延迟之间最均衡，工程复杂度也更低，适合作为当前上线和简历展示的主版本。

因此当前最终选择仍然是：

```text
V6-bge-small =
结构感知 chunk + FAISS + BM25 + RRF + 主文档上下文补全 + 低置信拒答
```

面试中可以这样讲：

> 我额外测试了两类索引优化。第一类是 sentence-window retrieval，即检索句子级 child chunk，再回填相邻句作为生成上下文；第二类是 structured retrieval，即在 RRF 后根据 department、process_type、risk_level、section_type 等 metadata 做 soft boost。实验发现 sentence-window hybrid 的 Citation 略高，但 Answer 明显下降；structured boost 的 Answer 略高，但 Hit@5 和 Citation 下降；两者叠加也没有超过原主链路。因此我没有为了复杂度而强行替换方案，最终保留结构化 chunk + FAISS + BM25 + RRF，因为它在引用准确、答案覆盖、拒答和延迟之间最均衡。

如果面试官问“为什么 sentence-window 没有成为最终方案”，可以回答：

> sentence-window 的优势是检索粒度更细，适合答案集中在某几句话里的场景。但企业制度问答经常需要流程、材料、时限、例外条件一起回答，单句命中会让上下文过碎。虽然回填了前后句，但本项目实验里 Answer Accuracy Proxy 明显下降，所以它暂时只作为增强候选。

如果面试官问“为什么 structured retrieval 也没成为最终方案”，可以回答：

> structured boost 确实提高了一点 Answer Accuracy Proxy，但 Hit@5 和 Citation Accuracy 下降，说明 metadata 加权有时会把结果推向业务上相似但不是标准答案的制度。企业制度问答更重视引用准确，所以暂时不进入主链路。

#### 6.3.7 困难知识库：为什么要把数据集做难

前面很多实验里，简单、稳定、可解释的方法经常胜出，例如结构化 chunk、BM25、FAISS、bge-small 和 RRF。这不是坏事，但需要追问一个更深的问题：

```text
是不是因为原始资料库太简单，导致高级 RAG 方法的价值没有被逼出来？
```

因此项目新增了分层资料库和 hard benchmark。现在资料库分为三层：

| 层级 | 资料特点 | 用途 |
| --- | --- | --- |
| baseline | 原有 30 份 Markdown + 15 份较规整 PDF | 验证传统制度问答基本链路 |
| medium | 新增 6 份 8 页长制度 PDF | 验证长文档、表格、附件、跨制度引用对检索的影响 |
| hard | 新增 6 份 8 页冲突制度 PDF | 验证版本冲突、补充通知优先级、相似条款、多跳问题 |

新资料由 `scripts/generate_layered_policy_benchmark.py` 生成，写入：

```text
data/policies_pdf/medium_*.pdf
data/policies_pdf/hard_*.pdf
data/eval/medium_eval_cases.jsonl
data/eval/hard_eval_cases.jsonl
```

这些 PDF 不覆盖 baseline，而是通过 metadata 中的 `dataset_layer` 区分：

```json
{
  "dataset_layer": "hard",
  "effective_from": "2026-04-01",
  "supersedes": "PDF-HARD-TRAVEL-2025",
  "priority": "80",
  "conflict_group": "travel_standard",
  "related_doc_ids": "PDF-MED-FIN-EXPENSE-2026"
}
```

这几个字段的意义：

- `dataset_layer`：控制实验加载 baseline、medium、hard 或 all。
- `effective_from/effective_to`：判断制度是否在问题发生时间有效。
- `supersedes`：说明当前制度替代了哪些旧制度。
- `priority`：补充通知、专项办法、新版制度的排序优先级。
- `conflict_group`：标记属于同一冲突主题的制度，例如差旅 2025/2026。
- `related_doc_ids`：记录跨制度引用关系，帮助构造多跳问题。

新增 hard cases 覆盖 8 类问题：

| 类型 | 例子 | 主要考察 |
| --- | --- | --- |
| 版本冲突 | “现在北京出差住宿标准应该看 2025 版还是 2026 版？” | 是否优先采用新版制度 |
| 优先级 | “报销制度和 4 月补充通知不一致时按哪个执行？” | 补充通知是否覆盖旧制度 |
| 跨文档 | “项目采购同时占用项目经费时，需要看哪些制度？” | 是否召回多个必要制度 |
| 表格金额 | “项目采购金额超过 30000 元时审批有什么变化？” | 是否命中金额阈值表 |
| 例外条件 | “客户数据导出很紧急，可以先导出再补审批吗？” | 是否引用紧急例外和留痕要求 |
| 模糊口语 | “电脑在家办公连不上系统，算 IT 问题还是安全例外？” | 是否处理口语化和跨部门语义 |
| 相似条款 | “采购合同和项目经费都要审批，我应该先走哪个？” | 是否区分相似制度 |
| 拒答 | “公司股票期权怎么行权？” | 是否识别知识库外问题 |

为了评价这些问题，项目在原有指标外新增 hard 指标：

| 指标 | 含义 | 为什么需要 |
| --- | --- | --- |
| `Conflict Resolution Accuracy` | 新旧制度冲突时，是否把新版/高优先级制度排在旧制度前 | 企业制度最怕引用过期制度 |
| `Multi-hop Coverage` | 多文档问题是否召回所有必要制度 | 真实业务经常跨 HR、财务、采购、安全 |
| `Table Evidence Accuracy` | 金额、阈值、审批层级表是否命中正确文档 | 长制度里的表格信息容易被漏掉 |
| `Priority Compliance` | 是否遵守补充通知、专项办法、最新版制度优先 | 体现 metadata 治理价值 |
| `Hard Case Win Rate` | 相对 V6-hard，同一问题上高级策略胜出的比例 | 看局部收益，而不是只看总体均值 |

模型选择也不再只看单项指标，而是分场景加权：

```text
常规问题：
Answer 30% + Citation 30% + Hit/MRR 20% + Refusal 15% + Latency 5%

困难问题：
Citation 25% + Conflict 20% + Multi-hop 15% + Answer 20% + Refusal 15% + Latency 5%
```

为什么 hard 场景提高了 `Conflict` 和 `Multi-hop` 的权重：

- 困难制度问答中，答得像不像不是第一位，先要确保依据没有用错版本。
- 多文档问题只召回一个制度，经常会漏掉审批、材料或安全要求。
- Citation 和 Refusal 仍然是企业知识问答的底线指标。
- Latency 权重较低，但仍保留，因为 Streamlit demo 和本地部署需要可用响应速度。

本轮定向 full 实验跑了 hard 层核心配置：

| Version | 策略 | Answer | Citation | Conflict | Multi-hop | p95 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| V6-hard-bge-small | 当前主链路 | 0.558 | 0.750 | 0.500 | 0.417 | 45.5 ms |
| V10-hard-sentence-window | 句子窗口 | 0.558 | 0.750 | 0.500 | 0.417 | 63.0 ms |
| V11-hard-structured | 结构化 soft boost | 0.481 | 0.750 | 1.000 | 0.417 | 44.1 ms |
| V12-hard-sentence-structured | 句子窗口 + 结构化 | 0.461 | 0.760 | 1.000 | 0.417 | 67.3 ms |
| V9-hard-bge-m3 | bge-m3 embedding | 0.604 | 0.750 | 0.500 | 0.417 | 143.1 ms |
| V9-hard-qwen3-0.6b | Qwen3 embedding | 0.509 | 0.750 | 0.500 | 0.417 | 224.7 ms |

这次结论比简单库更有层次：

- `V11-hard-structured` 没有提升 Answer，但把版本冲突类问题从 `0.500` 提到 `1.000`，说明复杂资料下 metadata soft boost 开始体现价值。
- `V12` 的 Citation 略高，但 Answer 更低、延迟更高，说明复杂策略叠加仍然要谨慎。
- `bge-m3` 在 hard 层 Answer 从 `0.558` 提升到 `0.604`，说明更强 embedding 对长制度有局部收益，但 p95 从 `45.5ms` 增至 `143.1ms`。
- `Qwen3-Embedding-0.6B` 真实加载成功，但本项目 hard 集上 Answer 和延迟都不如 bge-m3，也没有改善 Citation/Conflict。
- 最终选择不再简单说“高级方法没用”，而是：高级方法在困难场景出现了局部收益，但是否进入主链路要看 Citation、Conflict、Answer、Latency 的综合权衡。

面试中可以这样讲：

> 我后来意识到，最初资料库比较规整，导致复杂 RAG 方法不一定显出优势。所以我保留原资料库作为 baseline，又构造了 medium/hard 两层制度库：medium 加入长文档、表格、附件和跨制度引用，hard 加入新旧版本冲突、补充通知优先级、相似制度干扰和知识库外问题。重新评估后发现，结构化 metadata boost 在 hard 集上把版本冲突识别从 0.5 提到 1.0，bge-m3 在长制度上提升了 Answer，但延迟明显上升。因此最终不是盲目追热门组件，而是按资料复杂度和业务风险选择主链路与增强候选。

### 6.4 full 实验如何保持稳定

项目已经将真实 embedding 加载策略改为默认优先本地缓存：

```text
SMARTOFFICE_EMBEDDING_LOCAL_ONLY=1
HF_HOME=D:\projects\enterprise-knowledge-rag\.cache\huggingface
```

已经验证成功的模型：

```text
BAAI/bge-small-zh-v1.5        512 维
BAAI/bge-base-zh-v1.5         768 维
intfloat/multilingual-e5-small 384 维
```

如果缓存缺失，full 严格实验会失败，不会把 local-hashing fallback 写成真实模型结论。

---

## 7. 一条问题的完整 RAG 流程

以问题为例：

```text
涉及客户数据导出时需要注意什么？
```

### 第一步：页面接收问题

文件：`app.py`

用户在 Streamlit 输入问题，点击生成回答。

### 第二步：调用 RAG 总控

文件：`smart_office_rag/pipeline.py`

调用：

```python
rag.ask(question, filters=filters)
```

### 第三步：越界判断

如果问题包含股票、个人购房、停车位、食堂菜单等知识库外词，会直接拒答。当前问题是客户数据，属于制度库范围，所以继续。

### 第四步：文档分块

文件：`smart_office_rag/documents.py`

Markdown 制度按 `#`、`##`、`###` 分块；PDF 制度按“第X章 / 第X条 / 附件 / 审批流程 / 修订记录”分块。

### 第五步：embedding 和索引

文件：`smart_office_rag/indexing.py`

每个 chunk 被编码成向量，问题也会被编码成向量。quick 模式可用 `local-hashing`，full 模式使用真实 sentence-transformers 模型。

### 第六步：并行检索

文件：`smart_office_rag/retrieval.py`

并行两路：

```text
向量检索：找语义相近 chunk
BM25：找关键词匹配 chunk
```

### 第七步：RRF 融合

把两路检索结果按排名融合。这样既保留语义召回，也保留业务关键词精确命中。

### 第八步：主文档上下文补全

如果系统判断主文档是“数据导出与外发审批规范”，会补充同一制度下的办理要求、材料、审批流程、风险条款。

### 第九步：低置信拒答

如果检索结果太弱，系统拒答，并给出下一步人工确认建议。当前问题命中足够强，所以继续生成。

### 第十步：生成回答

文件：`smart_office_rag/generator.py`

有 API key 时调用 LLM；没有 API key 时使用本地抽取式模板。涉及客户数据属于高风险问题，回答会强调审批、脱敏、留痕和责任部门。

### 第十一步：页面展示

文件：`app.py`

展示回答、引用来源、检索片段、`vector_score`、`bm25_score`、`rrf_score`、latency、是否拒答和 retrieval trace。

---

## 8. 评估系统详解

### 8.1 单次评估和实验评估的区别

| 文件 | 用途 |
| --- | --- |
| `evaluate.py` | 评估当前最终链路，像健康检查 |
| `run_experiments.py` | 评估多个版本，形成研发迭代故事 |

### 8.2 Hit@5

正确文档是否出现在 top-5 检索结果中。它衡量系统能不能找到正确制度。

### 8.3 Recall@5

如果一个问题有多个正确文档，Recall@5 衡量这些正确文档有多少被召回。

### 8.4 Context Precision@5

top-5 里有多少结果来自正确文档。上下文越干净，生成幻觉风险越低。

### 8.5 MRR@5

Mean Reciprocal Rank。正确文档排第 1 名得 1.0，排第 2 名得 0.5，排第 3 名得 0.333。

### 8.6 nDCG@5

衡量排序质量。正确文档越靠前，nDCG 越高。

### 8.7 Citation Accuracy

答案引用来源是否来自期望文档。企业制度问答里引用非常重要，因为用户需要知道答案依据。

### 8.8 Refusal Accuracy

知识库外问题是否正确拒答。比如股票、私人福利、公司食堂菜单这类问题不在制度库范围内，就不应该编造制度。

### 8.9 Faithfulness Proxy

答案是否由检索来源支撑。本项目使用确定性 proxy：引用来源正确或拒答正确时，认为更 faithful。它不是严格的 LLM-as-a-judge。

### 8.10 Answer Accuracy Proxy

回答和参考答案之间的关键词重叠比例。它是低成本本地指标，适合比较版本趋势，但不能替代人工评审或 LLM judge。

### 8.11 Latency p50 / p95

- p50：一半请求低于这个耗时。
- p95：95% 请求低于这个耗时。

模型选型不能只看准确率，也要看 p95 延迟和部署成本。

### 8.12 Index Build Time

构建向量索引耗时。full 实验中更大的 embedding 模型通常构建更慢。

---

## 9. 当前真实结果怎么讲

严谨讲法：

> 我先构造 30 篇 Markdown 制度和 15 篇正式 PDF 制度作为 baseline，所有文档统一归一化为 LangChain Document。后来为了验证“简单方法胜出是不是因为资料太简单”，又新增 12 篇 medium/hard 长 PDF 制度和 144 条困难评估样本，形成 57 份制度、468 条评估样本的分层 benchmark。实验分两步：先在 baseline 上比较整文档检索、固定窗口、结构化分块、BM25、向量、RRF 和拒答；再在 hard 集上测试 sentence-window、structured boost、bge-m3 和 Qwen3。结果显示，简单库上 V6-bge-small 最均衡；困难库上 structured boost 能把版本冲突识别从 0.5 提到 1.0，bge-m3 能提升 Answer 但延迟明显上升。因此最终主链路仍以 bge-small + BM25 + RRF 为主，同时把 structured boost 和 bge-m3 作为 hard 场景候选增强。

baseline full 数字：

```text
Answer Accuracy Proxy: 0.000 -> 0.476
Hit@5: 0.000 -> 0.903
Citation Accuracy: 0.074 -> 0.901
Refusal Accuracy: 0.000 -> 1.000
```

hard 定向 full 数字：

```text
V6-hard-bge-small: Answer 0.558, Citation 0.750, Conflict 0.500, p95 45.5ms
V11-hard-structured: Answer 0.481, Citation 0.750, Conflict 1.000, p95 44.1ms
V9-hard-bge-m3: Answer 0.604, Citation 0.750, Conflict 0.500, p95 143.1ms
V9-hard-qwen3-0.6b: Answer 0.509, Citation 0.750, Conflict 0.500, p95 224.7ms
```

注意：

- 不要说“训练了大模型”。
- 应该说“构建评估集并迭代优化 RAG 检索和生成约束链路”。
- 不要把 local-hashing 说成真实 embedding 模型，它只是 quick baseline。
- 当前 full 实验已经完成；如果将来换机器导致模型缓存缺失，应先修复缓存再引用模型选型结论。

---

## 10. 常见问题与排查

### 10.1 我到底用的是 LangChain Document 还是 dataclass

看当前环境是否安装 `langchain-core`：

```powershell
.\.venv\Scripts\python.exe -c "from langchain_core.documents import Document; print(Document)"
```

如果能打印类名，就是 LangChain Document。`types.py` 里的 dataclass 只是 fallback。

### 10.2 当前 PDF loader 是哪个

默认是 `PyPDFLoader`。可以用下面命令检查 PDF parent document 的 metadata：

```powershell
.\.venv\Scripts\python.exe -c "from smart_office_rag.config import RAGConfig; from smart_office_rag.documents import PolicyDocumentLoader; cfg=RAGConfig(); loader=PolicyDocumentLoader(cfg.data_path, pdf_path=cfg.pdf_data_path, pdf_mode=cfg.pdf_loader_mode); docs=loader.load_parent_documents(); print(sorted({d.metadata.get('loader') for d in docs if d.metadata.get('source_type')=='pdf'}))"
```

期望输出：

```text
['PyPDFLoader']
```

### 10.3 为什么不把 UnstructuredPDFLoader 放进主链路

因为当前 PDF 是数字文本制度，不是扫描件或复杂版式合同。`PyPDFLoader` 更轻、更快、更稳定，足够抽取正文。`UnstructuredPDFLoader` 作为高级选项保留在 `requirements-pdf-advanced.txt`。

### 10.4 为什么页面可能显示旧实验结果

可能原因：

- Streamlit Cloud 还没 redeploy。
- 本地 Streamlit 缓存旧 JSON。
- 浏览器页面没刷新。

重新运行 `evaluate.py` 或 `run_experiments.py --quick` 后刷新页面即可；如果是云端，需要确认代码和报告已经 push。

### 10.5 为什么报告里还出现 local-hashing

它用于 quick baseline，保证没有真实模型时也能回归完整链路。当前 full 实验已经额外跑通 V4-bge-small、V4-bge-base、V4-e5、V6-bge-small、V6-bge-base、V6-e5；最终 embedding 选型看这些真实模型结果，不看 local-hashing。

### 10.6 为什么 full 实验可能失败

full 模式默认从项目 `.cache/huggingface` 本地缓存加载真实模型。如果换机器后缓存缺失，实验会失败或 skipped；这时应先修复模型缓存，不应该把 local-hashing fallback 结果写成真实模型对比。

---

## 11. 推荐学习顺序

建议按这个顺序读：

1. `README.md`：先看项目定位和当前真实数据规模。
2. `data/policies/`：看 2-3 篇 Markdown 制度，理解 front matter。
3. `data/policies_pdf/`：看 1-2 篇 PDF 制度和 `.metadata.json`，理解正式 PDF + sidecar metadata。
4. `data/eval/eval_cases.jsonl` 和 `data/eval/pdf_eval_cases.jsonl`：看评估问题怎么设计。
5. `smart_office_rag/loaders.py`：理解 Markdown/PDF 如何统一成 Document。
6. `smart_office_rag/documents.py`：理解 Markdown 标题分块和 PDF 章条分块。
7. `smart_office_rag/indexing.py`：理解 embedding、NumPy、FAISS。
8. `smart_office_rag/retrieval.py`：理解 BM25、向量检索、RRF。
9. `smart_office_rag/generator.py`：理解 LLM 生成和抽取式兜底。
10. `smart_office_rag/pipeline.py`：串起完整流程。
11. `evaluate.py`：理解单次评估。
12. `run_experiments.py`：理解真实迭代实验。
13. `docs/EXPERIMENT_REPORT.md`：看当前实验报告。
14. `app.py`：理解页面如何展示这些能力。

---

## 12. 面试讲解模板

可以这样讲：

> 这个项目是在 all-in-rag 思路基础上，结合企业内部制度问答场景重新设计的数据、文档结构、评估集和展示系统。我构造了 30 篇 Markdown 模拟制度和 15 篇正式 PDF 制度，Markdown 通过 front matter loader 接入，PDF 通过 LangChain PyPDFLoader 加 sidecar metadata 接入，最终统一归一化为 Document。分块上，Markdown 使用标题层级，PDF 使用第一章、第一条、附件、审批流程等正式条款结构。检索上，同时使用 BM25 和向量召回，并通过 RRF 融合排序。评估上，使用 324 条样本覆盖流程、材料、时限、金额阈值、跨文档引用、版本差异和拒答。Embedding 选型上，我先稳定跑通 bge-small、bge-base 和 multilingual-e5，再从 MTEB/C-MTEB 候选中扩展测试 Qwen3-Embedding-0.6B、bge-m3 和 gte-Qwen2-1.5B。为了避免 fallback 污染结果，新模型实验要求 `require_real_embedding=true`，加载或 encode 失败就标记 skipped。最终结果显示 Qwen3 的引用准确率略高但延迟过高，bge-m3 的答案覆盖略高但引用准确率略低且延迟更高，gte-Qwen2 当前依赖下 encode 失败。因此最终保留 bge-small + BM25 + RRF + 低置信拒答，作为准确率、引用可信度、拒答能力、延迟和工程稳定性最均衡的主链路。

最重要的三个亮点：

1. 有完整 RAG 工程链路，不只是调 API。
2. 有真实可复现评估，不把满分或兜底结果当结论。
3. 有业务风控意识，包括引用溯源、拒答、高风险流程提醒和正式制度 metadata 管理。

Embedding 选型可以单独这样讲：

> 我把 embedding 选型分成两层。第一层是工程稳定性，先用 bge-small、bge-base、multilingual-e5 跑通真实 sentence-transformers + FAISS 链路，确认不是 local-hashing 兜底。第二层是模型候选扩展，我参考 MTEB/C-MTEB 选了 Qwen3-Embedding-0.6B、bge-m3、gte-Qwen2-1.5B-instruct，再放到本项目评估集复验。简单制度库上 bge-small 最均衡；hard 长制度上 bge-m3 的 Answer 从 0.558 提到 0.604，但 Citation 和 Conflict 没提升，p95 从 45.5ms 增加到 143.1ms；Qwen3 真实加载成功，但 Answer 0.509、p95 224.7ms。结论是：bge-m3 可以作为长文档增强候选，默认主链路仍保留 bge-small。

高频追问回答：

| 面试官问题 | 回答口径 |
| --- | --- |
| 为什么不直接选 MTEB 排名最高的模型？ | MTEB 是候选筛选依据，不是业务最终指标。本项目最终看企业制度评估集里的召回、引用、拒答和延迟。 |
| 为什么 Qwen3 没有替换 bge-small？ | Qwen3 在 hard 定向实验中真实加载成功，但 Answer 0.509 低于 V6-hard 的 0.558，Citation/Conflict 没提升，p95 到 224.7ms，并且需要 `trust_remote_code=True`。 |
| 为什么 bge-m3 Answer 更高还不用？ | bge-m3 在 hard 长制度上 Answer 提到 0.604，说明强 embedding 有局部收益；但 Citation/Conflict 没提升，p95 到 143.1ms，所以更适合作为长文档增强候选，而不是默认主链路。 |
| gte-Qwen2 失败会不会影响项目说服力？ | 不会，反而说明实验严谨。它下载后 encode 失败，所以标记 skipped，没有把 fallback 结果伪装成真实结论。 |
| 最终选择 bge-small 的一句话原因？ | 它不是所有场景单项最强，但在常规制度问答里最均衡；hard 场景可以按需启用 structured boost 或 bge-m3。 |
| 当前用的是什么向量库？ | 主链路用 FAISS，本地 `IndexFlatIP` 精确向量检索；NumPy 只作为 quick baseline 和 fallback 实验后端。 |
| 为什么不用 Milvus？ | Milvus 适合百万级向量、分布式和高并发，当前 all-layer 也只有 1331 个 chunk，引入 Milvus 会增加部署复杂度但收益有限。 |
| 为什么不用 PGVector？ | PGVector 适合已有 PostgreSQL 和数据库权限/审计体系的企业应用；当前项目没有后端数据库，所以 FAISS 更轻、更适合本地复现。 |
| 为什么不用 Elasticsearch？ | ES 适合已有搜索基础设施的企业，但本项目已实现 BM25 + 向量 + RRF，数据规模也小，不需要额外部署 ES。 |
| 后续如果要优化向量库怎么办？ | 优先保留 FAISS 主链路，可轻量增加 Chroma 做本地持久化对比；Milvus/PGVector/ES 放在生产化选型分析里。 |
| 当前项目用了什么索引方法？ | 结构化 chunk 索引 + FAISS 向量索引 + BM25 倒排检索 + RRF 融合 + 主文档上下文补全。 |
| 什么是句子窗口检索？ | 检索时用句子级 child chunk 提高命中精度，生成时回填前后句，避免上下文过碎。 |
| 为什么句子窗口没成为主方案？ | V10 hybrid 的 Citation 略高，但 Answer 从 0.476 降到 0.398，说明制度问答需要条款级完整上下文。 |
| 什么是结构化检索？ | 在 RRF 后根据 department、process_type、risk_level、section_type 等 metadata 做 soft boost，而不是强过滤。 |
| 为什么结构化检索没成为主方案？ | V11 Answer 略高，但 Hit@5 和 Citation 都降到 0.880，说明 metadata boost 会把排序推向相似但非标准答案的制度。 |
| 索引优化的一句话结论是什么？ | 我测试了 sentence-window 和 structured boost，但真实评估显示它们没有全面超过 V6；最终保留结构感知 chunk + FAISS + BM25 + RRF，因为它在答案完整性、引用准确、拒答和延迟之间最均衡。 |

---

## 13. 简历项目经历写法（SMART 版）

下面这版适合直接放在简历项目经历里。写法按照 SMART 思路组织：明确业务场景、任务目标、技术行动、量化结果和上线展示。整体口径是“RAG 链路优化”，不要写成“训练大模型”。

**SmartOfficeRAG：企业内部制度知识问答系统｜个人项目**

- **背景与目标：** 面向企业 HR、财务、IT、安全、采购等内部制度咨询场景，针对“制度分散、员工重复咨询、人工答疑成本高、答案难追溯”的痛点，构建可本地部署的 RAG 问答系统，支持政策查询、流程解释、材料清单、风险提醒、低置信拒答和引用溯源。
- **数据与治理：** 构建 57 篇模拟企业制度知识库，覆盖 30 篇 Markdown 制度、15 篇 baseline PDF 和 12 篇 medium/hard 长制度 PDF；设计 front matter 与 sidecar metadata，统一归一化为 LangChain Document，并引入 `dataset_layer`、版本生效期、优先级、替代关系和关联制度等字段。
- **系统链路：** 设计 Markdown 标题分块与 PDF 正式章条分块，使用 `BAAI/bge-small-zh-v1.5` 生成向量，基于 FAISS 构建本地向量索引，并融合 BM25 关键词召回与 RRF 排序；结合主文档上下文补全、结构化 metadata soft boost 和低置信拒答，降低相似制度误召回和知识库外幻觉。
- **评估迭代：** 构建 468 条分层评估样本，覆盖流程、材料、时限、金额阈值、跨文档、多版本冲突、相似条款和拒答问题；对比固定窗口、递归分块、语义分块、sentence-window、structured retrieval、bge-m3、Qwen3 等策略，用 Hit@5、MRR@5、Citation Accuracy、Refusal Accuracy、Conflict Resolution、p95 latency 等指标选择链路。
- **项目结果：** 单次最终链路在 57 份制度、1331 个 chunks、468 条评估样本上达到 Hit@5 0.877、Citation Accuracy 0.880、Refusal Accuracy 1.000、p95 40.8ms；hard 集实验中 structured boost 将版本冲突识别从 0.500 提升至 1.000，bge-m3 将 hard Answer 从 0.558 提升至 0.604，但因延迟升至 139.5ms，最终保留 bge-small + BM25 + RRF 作为默认主链路。
- **上线展示：** 基于 Streamlit 部署交互式 Demo，页面展示回答、引用来源、检索片段、向量/BM25/RRF 分数、拒答原因和实验指标；无 API key 时支持本地抽取式兜底，保证演示稳定性。线上 Demo：请替换为你的 Streamlit Cloud URL。

如果简历空间更紧，可以压缩成下面这版：

**SmartOfficeRAG：企业内部制度知识问答系统｜个人项目**

- 面向企业内部制度咨询场景，针对制度分散、重复答疑、答案难追溯等痛点，构建可本地部署的 RAG 问答系统，支持政策查询、流程解释、风险提醒、低置信拒答和引用溯源。
- 构建 57 篇模拟企业制度知识库与 468 条分层评估样本，支持 Markdown/PDF 多格式接入，统一归一化为 LangChain Document，并通过 metadata 管理部门、流程、风险、版本、优先级和关联制度。
- 实现结构感知分块、FAISS 向量索引、BM25 关键词召回、RRF 融合排序和主文档上下文补全；对比不同分块策略、embedding 模型和索引增强方案，最终选择 bge-small + BM25 + RRF 作为默认主链路。
- 评估覆盖 Hit@5、MRR@5、Citation Accuracy、Refusal Accuracy、Conflict Resolution 和 p95 latency；最终链路在 468 条样本上达到 Hit@5 0.877、引用准确率 0.880、拒答准确率 1.000，hard 集中 structured boost 将版本冲突识别从 0.500 提升至 1.000。
- 基于 Streamlit 上线可交互 Demo，展示回答、引用来源、检索片段、检索分数、拒答原因和实验指标；线上 Demo：请替换为你的 Streamlit Cloud URL。

---

## 14. 查询构建实验：自然语言问题要不要先优化

查询构建（Query Construction）解决的是“用户自然语言问题”和“检索系统需要的查询表达”之间的落差。用户会问：

```text
现在北京出差住宿标准应该看 2025 版还是 2026 版？
报销制度和 4 月补充通知不一致时，发票材料按哪个执行？
采购合同和项目经费都要审批，我应该先走哪个？
```

这些问题不只是语义相似度问题，还包含版本、时间、优先级、部门、金额阈值和跨文档关系。因此项目新增了规则式查询构建实验，而不是直接上 LLM rewrite。

本项目采用的查询构建方式：

```text
用户原问题
-> 识别意图：version_conflict / threshold_table / multi_hop / exception 等
-> 扩展检索词：生效日期、supersedes、补充通知、审批权限、关联制度等
-> 生成 rewritten_query
-> 不做强过滤，只进入 BM25 + vector + RRF 检索
```

为什么不用强过滤：

- 企业制度问题经常跨部门，强行过滤到一个部门会漏召回。
- “客户数据导出”既可能属于安全，也可能涉及 IT、客服、采购合同。
- “项目采购和经费”同时涉及采购、财务和项目管理。

本轮新增两个实验：

| Version | 策略 | 说明 |
| --- | --- | --- |
| V13-hard-query-construction | query construction + hybrid RRF | 只做查询端扩展，不做 structured boost |
| V14-hard-query-structured | query construction + structured boost | 查询构建和结构化排序叠加 |

实验结果：

| Version | Answer | Citation | Conflict | Multi-hop | Table | p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| V6-hard-bge-small | 0.558 | 0.750 | 0.500 | 0.417 | 1.000 | 117.7 ms |
| V11-hard-structured | 0.481 | 0.750 | 1.000 | 0.417 | 1.000 | 170.1 ms |
| V13-hard-query-construction | 0.564 | 0.750 | 0.500 | 0.417 | 1.000 | 177.5 ms |
| V14-hard-query-structured | 0.397 | 0.500 | 0.500 | 0.417 | 0.000 | 194.4 ms |

结论：

- `V13` 的 Answer 从 `0.558` 小幅提升到 `0.564`，Hard Case Win Rate 达到 `0.260`，说明查询构建对部分困难样本有帮助。
- `V13` 没有改善 Conflict 和 Multi-hop，说明只扩展查询词还不足以解决版本优先级和跨文档完整召回。
- `V14` 叠加 structured boost 后明显退化，Citation 从 `0.750` 降到 `0.500`，说明 query construction 和 metadata boost 会相互放大错误权重。
- 因此查询构建暂时不进入默认主链路，但可以作为 hard 场景候选增强。

面试中可以这样讲：

> 我没有直接把用户问题原样丢给检索器，也测试了 query construction。做法是把自然语言问题解析成意图和检索增强词，例如版本冲突会补充“生效日期、supersedes、优先级、补充通知”，金额问题会补充“阈值、审批权限、附表”。实验发现，单独 query construction 对 hard case 的 Answer 有小幅提升，说明查询端优化有价值；但它没有解决版本冲突排序，和 structured boost 叠加后还会误召回。因此我没有把它默认上线，而是保留为困难场景增强候选。

---

## 15. LLM 查询构建实验：为什么试了但没有直接放进主链路

前一节先做的是规则式 query construction。规则式的优点是快、稳定、可解释，但它对口语化问题的理解能力有限。为了验证“接入 LLM 做自然语言转换是否更好”，本项目继续新增了 LLM 查询构建实验。

### 15.1 为什么要尝试 LLM 查询构建

企业内部问答里，用户经常不会按制度原文提问，而是用很口语化的说法：

```text
我现在去北京出差，住酒店到底按2025的老标准还是2026的新标准啊？
客户名单今天急着发给供应商，能不能先导出去，明天再补审批？
项目买东西和采购合同两个流程都卡我，这到底要看哪几个制度？
老板口头同意了采购，我还要不要走合同评审？
```

这些问题包含省略、口语、反问、业务暗示和风险判断。只靠关键词规则可能抓不全，例如“老标准/新标准”实际对应 `version_conflict`，“先导出去后补审批”对应 `security_policy + exception`，“两个流程都卡我”对应 `multi_hop`。

因此新增一类 LLM query construction：

```text
用户口语问题
-> LLM 输出 JSON
   - rewritten_query：检索友好的改写问题
   - intent：general / version_conflict / priority / multi_hop / threshold_table / exception 等
   - soft_filters：department、section_type、version_sensitive、multi_hop 等弱提示
   - boost_terms：补充检索词
-> 使用 rewritten_query 进入 BM25 + vector + RRF
```

注意：这里不是让 LLM 直接回答，而是让 LLM 只做“查询构建”。最终答案仍必须来自制度库检索结果和引用来源。

### 15.2 代码和配置在哪里

| 文件 | 作用 |
| --- | --- |
| `run_experiments.py` | 新增 `llm_construct_query()`，调用 DeepSeek/OpenAI-compatible API 生成查询 JSON |
| `ExperimentConfig.query_construction_mode` | 区分 `rules` 和 `llm` |
| `ExperimentConfig.require_llm_query_construction` | 为 true 时，LLM 失败就标记 skipped，不允许降级冒充 |
| `experiments/configs/v15_llm_query_construction_hard_layer.json` | V15：LLM query construction + hybrid RRF |
| `experiments/configs/v16_llm_query_construction_structured_hard_layer.json` | V16：LLM query construction + structured boost |
| `data/eval/colloquial_eval_cases.jsonl` | 新增 30 条口语化困难问题 |

运行命令：

```powershell
.\.venv\Scripts\python.exe run_experiments.py --full --offline --allow-skip --config-pattern v6_bge_small_hard_layer.json,v13_query_construction_hard_layer.json,v15_llm_query_construction_hard_layer.json,v16_llm_query_construction_structured_hard_layer.json
```

运行前需要设置 `DEEPSEEK_API_KEY` 或 `OPENAI_API_KEY`。如果没有 API key，V15/V16 会如实标记为 `skipped`，不会自动退回规则改写。

### 15.3 新增口语化评估集

新增文件：

```text
data/eval/colloquial_eval_cases.jsonl
```

共 30 条，全部标记为 `dataset_layer=hard`，所以 hard 层实验会自动读取。问题类型包括：

| 类型 | 示例 |
| --- | --- |
| 版本冲突 | “住酒店到底按2025的老标准还是2026的新标准？” |
| 补充通知优先级 | “4月份的新通知和老制度不一样，我按哪个交材料？” |
| 安全例外 | “客户名单能不能先导出去，明天再补审批？” |
| 跨文档 | “项目买东西和采购合同两个流程都卡我，看哪几个制度？” |
| 金额阈值 | “三万多采购拆成两张单是不是不用高一级审批？” |
| 拒答 | “公司班车几点发，这个RAG能答吗？” |

这样做的目的不是让指标变好，而是专门暴露真实用户提问带来的理解难题。

### 15.4 真实实验结果

本轮在 hard 层重新跑了 126 条问题，包括原 hard cases 和新增 30 条口语化问题。

| Version | Query Construction | Retriever | Answer | Hit@5 | Citation | Conflict | Multi-hop | Table | Refusal | p95 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| V6-hard-bge-small | 无 | hybrid_rrf | 0.461 | 0.568 | 0.603 | 0.343 | 0.252 | 0.750 | 1.000 | 60.4ms |
| V13-hard-query-construction | rules | hybrid_rrf | 0.468 | 0.676 | 0.698 | 0.457 | 0.356 | 0.875 | 1.000 | 124.9ms |
| V15-hard-llm-query-construction | llm | hybrid_rrf | 0.454 | 0.468 | 0.516 | 0.343 | 0.126 | 0.750 | 1.000 | 2270.6ms |
| V16-hard-llm-query-structured | llm | structured_hybrid_rrf | 0.403 | 0.523 | 0.563 | 0.800 | 0.285 | 0.063 | 1.000 | 2131.5ms |

结论：

- LLM 查询构建确实跑通了，而且是通过真实 API 调用完成，不是 fallback。
- V15 的口语理解能力没有直接转化为更好的检索结果，Hit@5 和 Citation 都低于 V6/V13。
- V16 在 Conflict 上提升到 `0.800`，说明 LLM 改写加结构化排序对版本冲突有局部收益；但 Table Accuracy 明显下降，说明结构化 boost 可能把排序推向错误制度或错误附件。
- LLM 查询构建带来明显延迟成本，p95 从 V6 的 `60.4ms` 提升到约 `2.1-2.3s`。
- 当前最稳的是 V13 规则式 query construction：Answer、Hit@5、Citation、Conflict、Multi-hop、Table 都比 V6 更高，延迟虽增加但仍在百毫秒级。

### 15.5 为什么 LLM 改写反而可能变差

LLM query construction 不一定天然更强，原因主要有三点：

1. **改写可能丢失原问题里的精确触发词。**
   例如“2026新标准/2025老标准”如果被泛化成“最新差旅标准”，BM25 对具体版本词的命中会下降。

2. **LLM 会补充看似合理但不在制度里的词。**
   这会让向量检索偏向语义相似但非目标制度的片段。

3. **企业制度问题更依赖 metadata 和版本优先级。**
   LLM 能理解意图，但如果检索器没有强版本排序、有效期过滤、supersedes 规则，理解出来的意图不一定能稳定影响排序。

所以本项目的结论不是“不需要 LLM”，而是：

```text
LLM query construction 适合作为复杂口语问题的候选增强，
但在默认链路中必须通过真实评估证明它提升 Citation、Conflict、Multi-hop，
并且延迟和成本可接受。
```

### 15.6 最终选择

当前默认主链路仍然不直接启用 LLM query construction。推荐选择是：

```text
主链路：V6 / V13
增强候选：V16 只用于版本冲突或复杂口语问题的专项实验
暂不默认上线：V15/V16 LLM 查询构建
```

如果后续继续优化 LLM 查询构建，可以做三件事：

1. 给 LLM 输出的 `intent` 真正接入版本优先级排序，而不是只拼接 rewritten query。
2. 对 LLM 改写做安全约束：必须保留年份、金额、部门、制度名等关键实体。
3. 只对低置信或口语化复杂问题调用 LLM，普通问题继续走规则/原始查询，控制成本和延迟。

面试中可以这样讲：

> 我没有把 LLM rewrite 当成必然更好的组件，而是单独做了 V15/V16 实验。做法是让 LLM 把口语化问题转成 JSON，包括 rewritten_query、intent、soft_filters 和 boost_terms，然后仍然进入 BM25 + 向量 + RRF 检索。结果显示，LLM 版在版本冲突上有局部收益，但整体 Hit@5、Citation 和延迟都不如规则式 V13。因此我没有盲目把 LLM query construction 放进默认主链路，而是把它保留为复杂口语问题的候选增强，并计划下一步把 LLM intent 接入版本优先级和 metadata 排序。
