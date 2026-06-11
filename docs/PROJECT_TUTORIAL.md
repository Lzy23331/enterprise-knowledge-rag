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
| 制度文档 | 45 |
| Markdown 制度 | 30 |
| PDF 制度 | 15 |
| chunk | 833 |
| 评估样本 | 324 |
| 知识库内检索样本 | 300 |
| 知识库外拒答样本 | 24 |

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

负责 embedding 和向量索引。

支持：

- `local-hashing`：轻量可复现 baseline，不是真实语义模型。
- `BAAI/bge-small-zh-v1.5`：中文场景常用轻量 embedding。
- `BAAI/bge-base-zh-v1.5`：更大模型，质量可能更高但成本更高。
- `intfloat/multilingual-e5-small`：多语言 embedding 对比。

向量后端：

- NumPy：轻量、零服务依赖，适合 quick 实验和 Streamlit。
- FAISS：本地向量检索库，适合 full 实验和更真实的向量体验。

严谨口径：

> `local-hashing` 只是 fallback baseline。简历里如果写 embedding 模型选型，必须基于 `run_experiments.py --full` 成功跑出的真实模型对比。

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

> 我先构造 30 篇 Markdown 制度和 15 篇正式 PDF 制度，所有文档统一归一化为 LangChain Document。Markdown 走 front matter loader，PDF 走 PyPDFLoader + sidecar metadata。然后基于 324 条评估样本，从无检索 baseline 开始，比较整文档检索、固定窗口分块、结构化分块、纯向量、BM25、RRF 混合检索和低置信拒答。full 实验已经稳定跑通 bge-small、bge-base 和 multilingual-e5 三个真实 embedding 模型，结果显示结构化分块显著提升引用准确率，BM25+向量+RRF 能稳定召回，低置信拒答把知识库外拒答准确率提升到 1.0，最终选择 bge-small 作为中文制度问答主 embedding。

当前 full 数字：

```text
Answer Accuracy Proxy: 0.000 -> 0.476
Hit@5: 0.000 -> 0.903
Citation Accuracy: 0.074 -> 0.901
Refusal Accuracy: 0.000 -> 1.000
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

> 这个项目是在 all-in-rag 思路基础上，结合企业内部制度问答场景重新设计的数据、文档结构、评估集和展示系统。我构造了 30 篇 Markdown 模拟制度和 15 篇正式 PDF 制度，Markdown 通过 front matter loader 接入，PDF 通过 LangChain PyPDFLoader 加 sidecar metadata 接入，最终统一归一化为 Document。分块上，Markdown 使用标题层级，PDF 使用第一章、第一条、附件、审批流程等正式条款结构。检索上，同时使用 BM25 和向量召回，并通过 RRF 融合排序。评估上，使用 324 条样本覆盖流程、材料、时限、金额阈值、跨文档引用、版本差异和拒答。full 实验稳定跑通 bge-small、bge-base 和 multilingual-e5，发现三者在 Hit@5、Citation Accuracy、Refusal Accuracy 上持平，bge-small 的 Answer Accuracy Proxy 最高且延迟明显低于 bge-base，因此最终选用 bge-small + BM25 + RRF + 低置信拒答。

最重要的三个亮点：

1. 有完整 RAG 工程链路，不只是调 API。
2. 有真实可复现评估，不把满分或兜底结果当结论。
3. 有业务风控意识，包括引用溯源、拒答、高风险流程提醒和正式制度 metadata 管理。
