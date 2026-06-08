import json
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

import streamlit as st


st.set_page_config(page_title="SmartOfficeRAG", page_icon="🏢", layout="wide")

PROJECT_ROOT = Path(__file__).resolve().parent
POLICY_DIR = PROJECT_ROOT / "data" / "policies"
EVAL_REPORT_PATH = PROJECT_ROOT / "eval_report.json"
APP_VERSION = "cloud-lite-v2"

FRONT_MATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
HEADER_PATTERN = re.compile(r"^(#{1,3})\s+(.+?)\s*$", re.MULTILINE)


EXAMPLE_QUESTIONS = {
    "HR / 财务": [
        "员工请年假需要提前多久申请？",
        "办理报销申请需要哪些材料？",
        "绩效申诉需要在多久内提交？",
    ],
    "IT / 安全": [
        "新员工如何申请邮箱和 VPN 权限？",
        "访问生产系统需要走什么审批？",
        "涉及客户数据导出时需要注意什么？",
    ],
    "法务 / 采购 / 审计": [
        "合同评审应该在哪个系统提交？",
        "供应商准入需要哪些材料？",
        "内审问题整改的时限是什么？",
    ],
    "拒答测试": [
        "公司股票什么时候可以买入？",
        "员工停车位摇号规则是什么？",
    ],
}

OUT_OF_SCOPE_TERMS = (
    "股票",
    "子女",
    "入学",
    "宠物",
    "购房",
    "健身卡",
    "永久居留",
    "团建",
    "购车",
    "宿舍装修",
    "食堂菜单",
    "投资供应商",
    "宠物医疗",
    "婚礼礼金",
    "未公开财报",
    "旅游签证",
    "咖啡券",
    "停车位",
    "内推奖金",
    "年会抽奖",
    "生日礼物",
    "水电费",
)


def parse_front_matter(text: str) -> Tuple[Dict[str, str], str]:
    match = FRONT_MATTER_PATTERN.match(text)
    if not match:
        return {}, text

    metadata: Dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"')
    return metadata, text[match.end():]


def split_markdown(content: str) -> List[Dict[str, str]]:
    matches = list(HEADER_PATTERN.finditer(content))
    if not matches:
        return [{"section": "正文", "content": content.strip()}]

    chunks = []
    current_sections: Dict[int, str] = {}
    for index, match in enumerate(matches):
        level = len(match.group(1))
        title = match.group(2).strip()
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        text = content[start:end].strip()
        if not text:
            continue

        current_sections[level] = title
        for deeper_level in range(level + 1, 4):
            current_sections.pop(deeper_level, None)

        section = current_sections.get(3) or current_sections.get(2) or current_sections.get(1) or title
        chunks.append({"section": section, "content": text})
    return chunks


def tokens(text: str) -> Counter:
    result = []
    result.extend(re.findall(r"[A-Za-z0-9_]+", text.lower()))
    for run in re.findall(r"[\u4e00-\u9fff]+", text):
        if len(run) == 1:
            result.append(run)
        else:
            result.extend(run[index : index + 2] for index in range(len(run) - 1))
            result.extend(run[index : index + 3] for index in range(len(run) - 2))
    return Counter(result)


@st.cache_data(show_spinner="正在加载企业知识库...")
def load_knowledge_base() -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    parents: List[Dict[str, str]] = []
    chunks: List[Dict[str, str]] = []

    for path in sorted(POLICY_DIR.glob("*.md")):
        raw_text = path.read_text(encoding="utf-8")
        metadata, content = parse_front_matter(raw_text)
        doc_id = metadata.get("doc_id") or path.stem
        title = metadata.get("title", path.stem)
        parent = {
            **metadata,
            "doc_id": doc_id,
            "title": title,
            "source_file": path.name,
        }
        parents.append(parent)

        for index, chunk in enumerate(split_markdown(content)):
            citation = f"《{title}》{chunk['section']}"
            chunk_record = {
                **parent,
                "chunk_id": f"{doc_id}-{index + 1}",
                "chunk_index": index,
                "section": chunk["section"],
                "citation": citation,
                "content": chunk["content"],
            }
            chunk_record["search_text"] = " ".join(
                str(chunk_record.get(key, ""))
                for key in ("title", "department", "process_type", "risk_level", "section", "content")
            )
            chunks.append(chunk_record)

    return parents, chunks


@st.cache_data
def load_eval_summary() -> dict:
    if not EVAL_REPORT_PATH.exists():
        return {}
    try:
        return json.loads(EVAL_REPORT_PATH.read_text(encoding="utf-8")).get("summary", {})
    except Exception:
        return {}


def filter_options(chunks: List[Dict[str, str]]) -> Dict[str, List[str]]:
    options = {"department": ["全部"], "process_type": ["全部"], "risk_level": ["全部"]}
    for key in options:
        values = sorted({str(chunk.get(key)) for chunk in chunks if chunk.get(key)})
        options[key].extend(values)
    return options


def matches_filters(chunk: Dict[str, str], filters: Dict[str, str]) -> bool:
    for key, value in filters.items():
        if not value or value == "全部":
            continue
        if str(chunk.get(key, "")) != value:
            return False
    return True


def search(question: str, chunks: List[Dict[str, str]], filters: Dict[str, str], top_k: int = 5) -> List[Dict[str, str]]:
    query_terms = tokens(question)
    scored = []
    for chunk in chunks:
        if not matches_filters(chunk, filters):
            continue
        chunk_terms = tokens(chunk["search_text"])
        overlap = sum((query_terms & chunk_terms).values())
        title_bonus = 8 if chunk.get("title") and chunk["title"] in question else 0
        process_bonus = 4 if chunk.get("process_type") and chunk["process_type"] in question else 0
        section_bonus = 2 if any(term in chunk.get("section", "") for term in ("办理步骤", "所需材料", "审批 SLA", "注意事项")) else 0
        score = overlap + title_bonus + process_bonus + section_bonus
        if score > 0:
            scored.append((score, chunk))

    scored.sort(
        key=lambda item: (
            item[0],
            item[1].get("title", "") in question,
            -int(item[1].get("chunk_index", 0)),
        ),
        reverse=True,
    )
    results = []
    for rank, (score, chunk) in enumerate(scored[:top_k], 1):
        result = dict(chunk)
        result["keyword_score"] = score
        result["rank"] = rank
        results.append(result)
    return results


def prioritize_answer_chunks(question: str, chunks: List[Dict[str, str]]) -> List[Dict[str, str]]:
    def section_score(chunk: Dict[str, str]) -> int:
        section = chunk.get("section", "")
        value = int(chunk.get("keyword_score", 0))
        if "办理步骤" in section and any(term in question for term in ("步骤", "流程", "怎么办", "如何", "哪个系统", "系统提交")):
            value += 40
        if "所需材料" in section and any(term in question for term in ("材料", "资料", "需要哪些")):
            value += 40
        if "审批 SLA" in section and any(term in question for term in ("时限", "多久", "提前", "SLA")):
            value += 40
        if "注意事项" in section and any(term in question for term in ("风险", "注意", "合规")):
            value += 40
        return value

    return sorted(chunks, key=section_score, reverse=True)


def no_evidence_answer() -> str:
    return (
        "结论：\n"
        "当前知识库没有检索到明确依据，建议联系对应负责部门确认。\n\n"
        "办理/处理步骤：\n"
        "1. 确认问题所属部门。\n"
        "2. 联系 HR、财务、IT、信息安全或对应制度负责人。\n\n"
        "所需材料：\n"
        "- 暂无明确依据。\n\n"
        "注意事项：\n"
        "- 不建议在没有制度依据的情况下自行处理。\n\n"
        "引用来源：\n"
        "- 未检索到可引用来源。"
    )


def clean_snippet_text(text: str, max_chars: int = 360) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        stripped = re.sub(r"^#{1,6}\s*", "", stripped)
        lines.append(stripped)
    return " ".join(lines)[:max_chars]


def generate_answer(question: str, retrieved: List[Dict[str, str]]) -> str:
    if not retrieved or any(term in question for term in OUT_OF_SCOPE_TERMS):
        return no_evidence_answer()

    primary_doc_id = retrieved[0].get("doc_id")
    same_doc_chunks = [chunk for chunk in retrieved if chunk.get("doc_id") == primary_doc_id] or retrieved[:1]
    answer_chunks = prioritize_answer_chunks(question, same_doc_chunks)

    snippets = []
    for chunk in answer_chunks[:3]:
        snippets.append(clean_snippet_text(chunk["content"]))

    citations = []
    for chunk in answer_chunks[:4]:
        citation = chunk.get("citation", "未知来源")
        if citation not in citations:
            citations.append(citation)

    primary = retrieved[0]
    return (
        "结论：\n"
        f"根据知识库，最相关的制度是《{primary.get('title', '未知文档')}》，"
        f"问题主要涉及{primary.get('process_type', '相关流程')}。\n\n"
        "办理/处理步骤：\n"
        + "\n".join(f"{index + 1}. {snippet}" for index, snippet in enumerate(snippets))
        + "\n\n所需材料：\n"
        "- 请参考下方引用来源中的“所需材料”章节。\n"
        "- 若涉及高风险流程，请补充主管、系统负责人或信息安全审批记录。\n\n"
        "注意事项：\n"
        f"- 风险等级：{primary.get('risk_level', '未知')}。\n"
        "- 公开演示站点使用轻量本地检索与抽取式回答；完整项目代码保留了向量索引、混合检索和评估模块。\n\n"
        "引用来源：\n"
        + "\n".join(f"- {citation}" for citation in citations)
    )


def main() -> None:
    st.title("SmartOfficeRAG 企业员工服务知识库助手")
    st.caption("面向 HR、财务、IT、安全、行政、法务、采购、审计与运营流程的可溯源 RAG Demo")

    if "question" not in st.session_state:
        st.session_state["question"] = EXAMPLE_QUESTIONS["HR / 财务"][0]

    parents, chunks = load_knowledge_base()
    eval_summary = load_eval_summary()
    options = filter_options(chunks)

    status_cols = st.columns(5)
    status_cols[0].metric("制度文档", len(parents))
    status_cols[1].metric("检索片段", len(chunks))
    status_cols[2].metric("评估问题", eval_summary.get("total", 0) if eval_summary else 0)
    status_cols[3].metric("Hit@5", f"{eval_summary.get('hit_at_5', 0):.3f}" if eval_summary else "N/A")
    status_cols[4].metric("拒答准确", f"{eval_summary.get('refusal_accuracy', 0):.3f}" if eval_summary else "N/A")
    st.caption(f"版本：{APP_VERSION} | 云端模式：轻量检索 Demo | 入口文件：app.py")

    with st.sidebar:
        if st.button("重新加载知识库", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.divider()
        st.header("知识库概览")
        st.metric("制度文档", len(parents))
        st.metric("检索片段", len(chunks))
        if eval_summary:
            st.metric("评估问题", eval_summary.get("total", 0))
            col_a, col_b = st.columns(2)
            col_a.metric("Hit@5", f"{eval_summary.get('hit_at_5', 0):.3f}")
            col_b.metric("MRR@5", f"{eval_summary.get('mrr_at_5', 0):.3f}")
            col_c, col_d = st.columns(2)
            col_c.metric("引用准确", f"{eval_summary.get('citation_accuracy', 0):.3f}")
            col_d.metric("拒答准确", f"{eval_summary.get('refusal_accuracy', 0):.3f}")

        st.divider()
        st.header("检索过滤")
        department = st.selectbox("部门", options["department"])
        process_type = st.selectbox("流程类型", options["process_type"])
        risk_level = st.selectbox("风险等级", options["risk_level"])

        st.divider()
        st.write("示例问题")
        for group, questions in EXAMPLE_QUESTIONS.items():
            with st.expander(group, expanded=group == "HR / 财务"):
                for sample_question in questions:
                    if st.button(sample_question, use_container_width=True):
                        st.session_state["question"] = sample_question

    question = st.text_area(
        "请输入员工问题",
        key="question",
        height=100,
    )

    filters = {
        "department": department,
        "process_type": process_type,
        "risk_level": risk_level,
    }

    if st.button("生成回答", type="primary"):
        retrieved = search(question, chunks, filters=filters, top_k=5)
        answer = generate_answer(question, retrieved)

        st.subheader("回答")
        st.markdown(answer)

        st.subheader("引用来源")
        if retrieved and not any(term in question for term in OUT_OF_SCOPE_TERMS):
            seen = set()
            for chunk in retrieved:
                citation = chunk.get("citation", "未知来源")
                if citation in seen:
                    continue
                seen.add(citation)
                st.markdown(
                    f"- **{citation}** | {chunk.get('department', '未知')} | "
                    f"{chunk.get('process_type', '未知')} | {chunk.get('doc_id', '未知ID')} | "
                    f"风险等级：{chunk.get('risk_level', '未知')} | 更新时间：{chunk.get('updated_at', '未知')}"
                )
        else:
            st.info("没有检索到可引用来源。")

        st.subheader("检索片段")
        for index, chunk in enumerate(retrieved, 1):
            with st.expander(f"{index}. {chunk.get('citation', '未知来源')}"):
                st.write(chunk["content"])
                st.json(
                    {
                        "department": chunk.get("department"),
                        "process_type": chunk.get("process_type"),
                        "risk_level": chunk.get("risk_level"),
                        "doc_id": chunk.get("doc_id"),
                        "section": chunk.get("section"),
                        "keyword_score": chunk.get("keyword_score"),
                        "rank": chunk.get("rank"),
                        "source_file": chunk.get("source_file"),
                    }
                )


if __name__ == "__main__":
    main()
