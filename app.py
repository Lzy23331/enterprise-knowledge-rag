import json
import os
from pathlib import Path

import streamlit as st

from smart_office_rag.pipeline import EnterpriseKnowledgeRAG


st.set_page_config(page_title="SmartOfficeRAG", page_icon="🏢", layout="wide")

PROJECT_ROOT = Path(__file__).resolve().parent
EVAL_REPORT_PATH = PROJECT_ROOT / "eval_report.json"
EXPERIMENT_REPORT_PATH = PROJECT_ROOT / "experiments" / "results" / "experiment_report.json"
APP_VERSION = "portfolio-rag-v3"


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
        "公司是否报销私人健身卡？",
    ],
}


@st.cache_resource(show_spinner="正在加载完整 RAG 知识库...")
def load_rag() -> EnterpriseKnowledgeRAG:
    rag = EnterpriseKnowledgeRAG()
    rag.initialize()
    return rag


@st.cache_data
def load_eval_report() -> dict:
    if not EVAL_REPORT_PATH.exists():
        return {}
    try:
        return json.loads(EVAL_REPORT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


@st.cache_data
def load_experiment_report(report_mtime: float = 0.0) -> dict:
    if not EXPERIMENT_REPORT_PATH.exists():
        return {}
    try:
        return json.loads(EXPERIMENT_REPORT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def normalize_filter(value: str) -> str:
    return "" if value == "全部" else value


def render_strategy_report(report: dict) -> None:
    strategies = report.get("strategy_comparison", [])
    if not strategies:
        st.info("尚未生成检索策略对比。运行 `python evaluate.py` 后会显示 BM25、向量、混合检索与 LLM 直答基线。")
        return

    rows = []
    for item in strategies:
        rows.append(
            {
                "策略": item.get("strategy"),
                "Hit@5": round(item.get("hit_at_5", 0), 3),
                "MRR@5": round(item.get("mrr_at_5", 0), 3),
                "引用准确": round(item.get("citation_accuracy", 0), 3),
                "拒答准确": round(item.get("refusal_accuracy", 0), 3),
                "p95(ms)": round(item.get("latency_p95_ms", 0), 1),
            }
        )
    st.dataframe(rows, hide_index=True, use_container_width=True)


def render_experiment_report(report: dict) -> None:
    results = report.get("results", [])
    selected = report.get("selected_summary", {})
    if not results:
        st.info("尚未生成实验历程报告。运行 `python run_experiments.py --quick` 或 `python run_experiments.py --full` 后会显示。")
        return

    if selected:
        cols = st.columns(4)
        selected_label = selected.get("id", "N/A")
        embedding = selected.get("embedding_model")
        if embedding:
            selected_label = f"{selected_label} / {embedding}"
        cols[0].metric("选定版本", selected_label)
        cols[1].metric("Answer Acc.", f"{selected.get('answer_accuracy_proxy', 0):.3f}")
        cols[2].metric("Citation Acc.", f"{selected.get('citation_accuracy', 0):.3f}")
        cols[3].metric("Refusal Acc.", f"{selected.get('refusal_accuracy', 0):.3f}")

    rows = []
    for result in results:
        config = result.get("config", {})
        summary = result.get("summary", {})
        rows.append(
            {
                "版本": config.get("id"),
                "实验": config.get("name"),
                "状态": result.get("status"),
                "分块": config.get("chunk_strategy"),
                "Embedding": config.get("embedding_model"),
                "检索": config.get("retriever"),
                "Answer Acc.": round(summary.get("answer_accuracy_proxy", 0), 3) if summary else None,
                "Hit@5": round(summary.get("hit_at_5", 0), 3) if summary else None,
                "引用准确": round(summary.get("citation_accuracy", 0), 3) if summary else None,
                "拒答准确": round(summary.get("refusal_accuracy", 0), 3) if summary else None,
                "p95(ms)": round(summary.get("latency_p95_ms", 0), 1) if summary else None,
            }
        )
    st.dataframe(rows, hide_index=True, use_container_width=True)


def render_chunk(index: int, doc) -> None:
    title = doc.metadata.get("citation", "未知来源")
    with st.expander(f"{index}. {title}"):
        st.write(doc.page_content)
        st.json(
            {
                "doc_id": doc.metadata.get("doc_id"),
                "source_type": doc.metadata.get("source_type"),
                "loader": doc.metadata.get("loader"),
                "section": doc.metadata.get("section"),
                "section_type": doc.metadata.get("section_type"),
                "chapter_no": doc.metadata.get("chapter_no"),
                "article_no": doc.metadata.get("article_no"),
                "department": doc.metadata.get("department"),
                "process_type": doc.metadata.get("process_type"),
                "risk_level": doc.metadata.get("risk_level"),
                "page_count": doc.metadata.get("page_count"),
                "extraction_quality": doc.metadata.get("extraction_quality"),
                "missing_required_metadata": doc.metadata.get("missing_required_metadata"),
                "vector_rank": doc.metadata.get("vector_rank"),
                "vector_score": doc.metadata.get("vector_score"),
                "bm25_rank": doc.metadata.get("bm25_rank"),
                "bm25_score": doc.metadata.get("bm25_score"),
                "keyword_score": doc.metadata.get("keyword_score"),
                "rrf_score": doc.metadata.get("rrf_score"),
                "source_file": doc.metadata.get("source_file"),
            }
        )


def main() -> None:
    st.title("SmartOfficeRAG：企业内部制度知识问答系统")
    st.caption("面向 HR、财务、IT、安全、法务、采购、行政、审计等制度咨询场景的可评估 RAG Demo")

    if "question" not in st.session_state:
        st.session_state["question"] = EXAMPLE_QUESTIONS["HR / 财务"][0]

    rag = load_rag()
    report = load_eval_report()
    experiment_report_mtime = EXPERIMENT_REPORT_PATH.stat().st_mtime if EXPERIMENT_REPORT_PATH.exists() else 0.0
    experiment_report = load_experiment_report(experiment_report_mtime)
    summary = report.get("summary", {})
    filter_options = rag.get_filter_options()

    cols = st.columns(6)
    cols[0].metric("制度文档", len(rag.parents))
    cols[1].metric("检索片段", len(rag.chunks))
    cols[2].metric("评估问题", summary.get("total", 0) or "N/A")
    cols[3].metric("Hit@5", f"{summary.get('hit_at_5', 0):.3f}" if summary else "N/A")
    cols[4].metric("引用准确", f"{summary.get('citation_accuracy', 0):.3f}" if summary else "N/A")
    cols[5].metric("p95 延迟", f"{summary.get('latency_p95_ms', 0):.1f} ms" if summary else "N/A")

    st.caption(
        f"版本：{APP_VERSION} | 检索链路：向量召回 + BM25 + RRF + 低置信拒答 | "
        f"LLM：{'已配置' if os.getenv('DEEPSEEK_API_KEY') or os.getenv('OPENAI_API_KEY') else '未配置，使用本地抽取式兜底'}"
    )

    with st.sidebar:
        if st.button("重新加载知识库", use_container_width=True):
            st.cache_resource.clear()
            st.cache_data.clear()
            st.rerun()

        st.header("业务目标")
        st.write("减少重复制度咨询，提升政策答案可追溯性，并用拒答机制降低知识库外幻觉。")

        st.divider()
        st.header("检索过滤")
        department = st.selectbox("部门", filter_options["department"])
        process_type = st.selectbox("流程类型", filter_options["process_type"])
        risk_level = st.selectbox("风险等级", filter_options["risk_level"])

        st.divider()
        st.header("示例问题")
        for group, questions in EXAMPLE_QUESTIONS.items():
            with st.expander(group, expanded=group == "HR / 财务"):
                for sample_question in questions:
                    if st.button(sample_question, use_container_width=True):
                        st.session_state["question"] = sample_question

    question = st.text_area("请输入员工问题", key="question", height=110)

    filters = {
        "department": normalize_filter(department),
        "process_type": normalize_filter(process_type),
        "risk_level": normalize_filter(risk_level),
    }
    filters = {key: value for key, value in filters.items() if value}

    if st.button("生成回答", type="primary"):
        with st.spinner("正在执行 metadata 过滤、混合检索、RRF 融合和可信生成..."):
            response = rag.ask(question, filters=filters)

        answer_col, trace_col = st.columns([2, 1])
        with answer_col:
            st.subheader("回答")
            st.markdown(response.answer)

        with trace_col:
            st.subheader("链路状态")
            st.metric("端到端耗时", f"{response.latency_ms:.1f} ms")
            st.metric("召回片段", len(response.chunks))
            st.metric("是否拒答", "是" if response.refused else "否")
            if response.refusal_reason:
                st.warning(response.refusal_reason)
            st.json(response.retrieval_trace)

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

        st.subheader("检索片段与分数")
        for index, doc in enumerate(response.chunks, 1):
            render_chunk(index, doc)

    st.divider()
    with st.expander("离线评估与策略对比", expanded=False):
        render_strategy_report(report)
        failures = report.get("failure_cases", [])
        if failures:
            st.write("Top failure cases")
            st.dataframe(
                [
                    {
                        "id": case.get("id"),
                        "type": case.get("question_type"),
                        "question": case.get("question"),
                        "expected": ", ".join(case.get("expected_doc_ids", [])),
                        "retrieved": ", ".join(case.get("retrieved_doc_ids", [])),
                    }
                    for case in failures[:10]
                ],
                hide_index=True,
                use_container_width=True,
            )

    with st.expander("研发迭代实验历程", expanded=False):
        render_experiment_report(experiment_report)


if __name__ == "__main__":
    main()
