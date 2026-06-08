import os
from typing import Iterable, List, Optional

from openai import OpenAI

from .types import Document


ANSWER_TEMPLATE = """你是企业员工服务知识库助手。请只基于给定资料回答问题，不要编造制度。
如果资料中没有明确依据，请回答“当前知识库没有检索到明确依据，建议联系对应负责部门确认”，并说明已经检索到的相近资料。
请严格使用以下格式：

结论：
...

办理/处理步骤：
1. ...

所需材料：
- ...

注意事项：
- ...

引用来源：
- ...

用户问题：
{question}

检索资料：
{context}

回答："""


class AnswerGenerator:
    def __init__(
        self,
        model_name: str,
        base_url: str,
        temperature: float = 0.1,
        max_tokens: int = 1600,
    ):
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = None
        api_key = self._get_api_key()
        if api_key:
            self.client = OpenAI(api_key=api_key, base_url=base_url)

    @staticmethod
    def _get_api_key() -> Optional[str]:
        api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
        if api_key:
            return api_key

        try:
            import streamlit as st

            return st.secrets.get("DEEPSEEK_API_KEY") or st.secrets.get("OPENAI_API_KEY")
        except Exception:
            return None

    def generate(self, question: str, docs: List[Document]) -> str:
        if not docs:
            return self._no_evidence_answer()

        if self.client is None:
            return self._extractive_answer(question, docs)

        context = self._format_context(docs)
        prompt = ANSWER_TEMPLATE.format(question=question, context=context)
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            return response.choices[0].message.content or self._extractive_answer(question, docs)
        except Exception as exc:
            return (
                self._extractive_answer(question, docs)
                + "\n\n"
                + f"> LLM 生成不可用，已自动切换为本地抽取式回答。错误类型：{type(exc).__name__}"
            )

    @staticmethod
    def _format_context(docs: Iterable[Document]) -> str:
        parts = []
        for index, doc in enumerate(docs, 1):
            metadata = doc.metadata
            parts.append(
                "\n".join(
                    [
                        f"[资料 {index}]",
                        f"标题：{metadata.get('title', '未知文档')}",
                        f"章节：{metadata.get('section', '未知章节')}",
                        f"部门：{metadata.get('department', '未知')}",
                        f"流程类型：{metadata.get('process_type', '未知')}",
                        f"风险等级：{metadata.get('risk_level', '未知')}",
                        f"更新时间：{metadata.get('updated_at', '未知')}",
                        f"引用：{metadata.get('citation', '未知来源')}",
                        f"内容：{doc.page_content}",
                    ]
                )
            )
        return "\n\n".join(parts)

    @staticmethod
    def _no_evidence_answer() -> str:
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

    @staticmethod
    def _extractive_answer(question: str, docs: List[Document]) -> str:
        primary = docs[0]
        primary_doc_id = primary.metadata.get("doc_id")
        answer_docs = [doc for doc in docs if doc.metadata.get("doc_id") == primary_doc_id] or docs[:1]
        answer_docs = AnswerGenerator._prioritize_answer_docs(
            question,
            answer_docs,
            primary.metadata.get("process_type", ""),
        )
        snippets = []
        for doc in answer_docs[:3]:
            text = " ".join(line.strip() for line in doc.page_content.splitlines() if line.strip())
            snippets.append(text[:360])

        citations = []
        for doc in answer_docs[:4]:
            citation = doc.metadata.get("citation", "未知来源")
            if citation not in citations:
                citations.append(citation)

        return (
            "结论：\n"
            f"根据知识库，最相关的制度是《{primary.metadata.get('title', '未知文档')}》，"
            f"问题主要涉及{primary.metadata.get('process_type', '相关流程')}。\n\n"
            "办理/处理步骤：\n"
            + "\n".join(f"{index + 1}. {snippet}" for index, snippet in enumerate(snippets[:3]))
            + "\n\n所需材料：\n"
            "- 请参考下方引用来源中的“所需材料”章节。\n"
            "- 若涉及高风险流程，请补充主管、系统负责人或信息安全审批记录。\n\n"
            "注意事项：\n"
            f"- 风险等级：{primary.metadata.get('risk_level', '未知')}。\n"
            "- 该回答由本地抽取式模板生成；配置 LLM API key 后可获得更自然的总结。\n\n"
            "引用来源：\n"
            + "\n".join(f"- {citation}" for citation in citations)
        )

    @staticmethod
    def _prioritize_answer_docs(question: str, docs: List[Document], process_type: str) -> List[Document]:
        if not docs:
            return docs

        def score(doc: Document) -> int:
            section = str(doc.metadata.get("section", ""))
            text = doc.page_content
            value = 0
            if "办理步骤" in section and any(
                term in question for term in ("步骤", "流程", "怎么办", "如何", "哪个系统", "系统提交", "哪里提交")
            ):
                value += 40
            if "所需材料" in section and any(term in question for term in ("材料", "资料", "需要哪些")):
                value += 40
            if "审批 SLA" in section and any(term in question for term in ("时限", "多久", "提前", "SLA")):
                value += 40
            if "注意事项" in section and any(term in question for term in ("风险", "注意", "合规")):
                value += 40
            if "办理步骤" in section:
                value += 10
            if "所需材料" in section:
                value += 8
            if "审批 SLA" in section:
                value += 6
            if "注意事项" in section:
                value += 4
            if process_type and process_type in text:
                value += 5
            return value

        return sorted(docs, key=score, reverse=True)
