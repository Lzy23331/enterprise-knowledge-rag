import json
import os
from pathlib import Path

import streamlit as st

from smart_office_rag.pipeline import EnterpriseKnowledgeRAG


st.set_page_config(page_title="SmartOfficeRAG", page_icon="🏢", layout="wide")

PROJECT_ROOT = Path(__file__).resolve().parent
EVAL_REPORT_PATH = PROJECT_ROOT / "eval_report.json"
APP_VERSION = "enterprise-eval-v2"


@st.cache_resource(show_spinner="正在加载企业知识库...")
def load_rag() -> EnterpriseKnowledgeRAG:
    rag = EnterpriseKnowledgeRAG()
    rag.initialize()
    return rag


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


def load_eval_summary() -> dict:
    if not EVAL_REPORT_PATH.exists():
        return {}
    try:
        return json.loads(EVAL_REPORT_PATH.read_text(encoding="utf-8")).get("summary", {})
    except Exception:
        return {}


def main() -> None:
    st.title("SmartOfficeRAG 企业员工服务知识库助手")
    st.caption("面向 HR、财务、IT、安全、行政、法务、采购、审计与运营流程的可溯源 RAG Demo")

    rag = load_rag()
    filter_options = rag.get_filter_options()
    eval_summary = load_eval_summary()

    status_cols = st.columns(5)
    status_cols[0].metric("制度文档", len(rag.parents))
    status_cols[1].metric("检索片段", len(rag.chunks))
    status_cols[2].metric("评估问题", eval_summary.get("total", 0) if eval_summary else 0)
    status_cols[3].metric("Hit@5", f"{eval_summary.get('hit_at_5', 0):.3f}" if eval_summary else "N/A")
    status_cols[4].metric("拒答准确", f"{eval_summary.get('refusal_accuracy', 0):.3f}" if eval_summary else "N/A")
    st.caption(
        f"版本：{APP_VERSION} | 向量检索：{os.getenv('SMARTOFFICE_USE_VECTOR', '0')} | "
        f"HF_HOME：{os.getenv('HF_HOME', '未设置')}"
    )

    with st.sidebar:
        if st.button("重新加载知识库", use_container_width=True):
            st.cache_resource.clear()
            st.rerun()

        st.divider()
        st.header("知识库概览")
        st.metric("制度文档", len(rag.parents))
        st.metric("检索片段", len(rag.chunks))
        if eval_summary:
            st.metric("评估问题", eval_summary.get("total", 0))
            col_a, col_b = st.columns(2)
            col_a.metric("Hit@5", f"{eval_summary.get('hit_at_5', 0):.3f}")
            col_b.metric("MRR@5", f"{eval_summary.get('mrr_at_5', 0):.3f}")
            col_c, col_d = st.columns(2)
            col_c.metric("引用准确", f"{eval_summary.get('citation_accuracy', 0):.3f}")
            col_d.metric("拒答准确", f"{eval_summary.get('refusal_accuracy', 0):.3f}")
            st.caption(
                f"p95 延迟：{eval_summary.get('latency_p95_ms', 0):.0f} ms | "
                f"索引构建：{eval_summary.get('index_build_ms', 0):.0f} ms"
            )
        else:
            st.info("运行 evaluate.py 后显示评估指标。")

        st.divider()
        st.header("检索过滤")
        department = st.selectbox("部门", filter_options["department"])
        process_type = st.selectbox("流程类型", filter_options["process_type"])
        risk_level = st.selectbox("风险等级", filter_options["risk_level"])
        st.divider()
        st.write("示例问题")
        for group, questions in EXAMPLE_QUESTIONS.items():
            with st.expander(group, expanded=group == "HR / 财务"):
                for question in questions:
                    if st.button(question, use_container_width=True):
                        st.session_state["question"] = question

    question = st.text_area(
        "请输入员工问题",
        value=st.session_state.get("question", EXAMPLE_QUESTIONS["HR / 财务"][0]),
        height=100,
    )

    filters = {
        "department": department,
        "process_type": process_type,
        "risk_level": risk_level,
    }

    if st.button("生成回答", type="primary"):
        with st.spinner("正在检索知识库并生成回答..."):
            response = rag.ask(question, filters=filters)

        st.subheader("回答")
        st.markdown(response.answer)

        st.subheader("引用来源")
        if response.sources:
            for source in response.sources:
                st.markdown(
                    f"- **{source['citation']}** | {source['department']} | "
                    f"{source['process_type']} | {source['doc_id']} | 风险等级：{source['risk_level']} | "
                    f"更新时间：{source['updated_at']}"
                )
        else:
            st.info("没有检索到可引用来源。")

        st.subheader("检索片段")
        for index, doc in enumerate(response.chunks, 1):
            with st.expander(f"{index}. {doc.metadata.get('citation', '未知来源')}"):
                st.write(doc.page_content)
                st.json(
                    {
                        "department": doc.metadata.get("department"),
                        "process_type": doc.metadata.get("process_type"),
                        "risk_level": doc.metadata.get("risk_level"),
                        "doc_id": doc.metadata.get("doc_id"),
                        "section": doc.metadata.get("section"),
                        "vector_rank": doc.metadata.get("vector_rank"),
                        "bm25_rank": doc.metadata.get("bm25_rank"),
                        "keyword_score": doc.metadata.get("keyword_score"),
                        "rrf_score": doc.metadata.get("rrf_score"),
                        "source_file": doc.metadata.get("source_file"),
                    }
                )


if __name__ == "__main__":
    main()
