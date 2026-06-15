import os
import re
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
        if os.getenv("SMARTOFFICE_DISABLE_LLM", "0") == "1":
            return None

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
            return self.generate_no_evidence(question, [])

        if self.client is None:
            return self._extractive_answer(question, docs)

        context = self._format_context(docs)
        prompt = ANSWER_TEMPLATE.format(question=question, context=context)
        prompt += (
            "\n\n证据判定规则：如果检索资料中已经出现直接回答用户问题的时限、金额、条件、步骤或材料清单，"
            "应优先基于该资料给出结论；不要因为资料没有覆盖所有可能例外情况，就回答没有明确依据。"
            "可以在注意事项中说明例外或需进一步确认的边界。"
        )
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            content = response.choices[0].message.content or ""
            if self._looks_like_false_no_evidence(content, question, docs):
                return (
                    self._extractive_answer(question, docs)
                    + "\n\n"
                    + "> 已检测到检索片段包含直接制度依据，自动使用本地抽取式回答替代保守拒答。"
                )
            return content or self._extractive_answer(question, docs)
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
    def _looks_like_false_no_evidence(answer: str, question: str, docs: List[Document]) -> bool:
        if not answer or not docs:
            return False
        no_evidence_terms = (
            "没有检索到明确依据",
            "没有明确依据",
            "未检索到明确依据",
            "无法形成明确依据",
        )
        if not any(term in answer for term in no_evidence_terms):
            return False

        question_terms = ("多久", "提前", "时限", "SLA", "几天", "工作日")
        evidence_terms = ("提前", "工作日", "自然日", "时限", "SLA", "至少", "超过")
        if any(term in question for term in question_terms):
            evidence_text = "\n".join(doc.page_content for doc in docs[:5])
            return any(term in evidence_text for term in evidence_terms)
        return False

    @staticmethod
    def _direct_evidence_sentence(question: str, docs: List[Document]) -> str:
        time_question_terms = ("多久", "提前", "时限", "SLA", "几天", "什么时候", "来得及")
        if not any(term in question for term in time_question_terms):
            return ""

        evidence_terms = ("提前", "工作日", "自然日", "时限", "SLA", "至少", "超过", "标准时限")
        best_sentence = ""
        best_score = 0
        for doc in docs[:5]:
            cleaned_text = " ".join(
                line.strip()
                for line in doc.page_content.splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            )
            sentences = re.split(r"(?<=[。！？；;])\s*", cleaned_text)
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                score = sum(1 for term in evidence_terms if term in sentence)
                if "年假" in question and "年假" in sentence:
                    score += 2
                if "请假" in question and "请假" in sentence:
                    score += 1
                if score > best_score:
                    best_score = score
                    best_sentence = sentence
        return best_sentence if best_score >= 2 else ""

    @staticmethod
    def generate_no_evidence(question: str, docs: List[Document], reason: str = "no_evidence") -> str:
        reason_text = {
            "out_of_scope": "问题不属于当前模拟企业制度知识库覆盖范围。",
            "low_confidence": "系统检索到的片段相关度不足，无法形成可靠制度依据。",
            "no_evidence": "当前知识库没有检索到明确制度依据。",
        }.get(reason, "当前知识库没有检索到明确制度依据。")

        nearby = []
        for doc in docs[:3]:
            citation = doc.metadata.get("citation", "未知来源")
            department = doc.metadata.get("department", "未知部门")
            risk_level = doc.metadata.get("risk_level", "未知")
            if citation not in nearby:
                nearby.append(f"- {citation}（{department}，风险等级：{risk_level}）")
        nearby_text = "\n".join(nearby) if nearby else "- 未检索到可引用来源。"

        return (
            "结论：\n"
            f"{reason_text}建议联系对应负责部门确认，不应基于模型猜测直接办理。\n\n"
            "办理/处理步骤：\n"
            "1. 先确认问题所属部门、流程类型和是否涉及资金、合同、客户数据或生产系统。\n"
            "2. 联系 HR、财务、IT、信息安全、法务、采购、行政或内审等对应制度负责人。\n"
            "3. 如果属于紧急事项，先保留沟通记录，再按制度负责人要求补充审批或留痕。\n\n"
            "所需材料：\n"
            "- 暂无明确制度材料要求；建议准备问题背景、申请人、所属部门、期望完成时间和相关截图/合同/清单。\n\n"
            "注意事项：\n"
            "- 低置信或知识库外问题不会调用 LLM 继续生成，避免编造政策。\n"
            "- 涉及高风险权限、客户信息、付款、合同、印章或监管报送时，必须由制度负责人确认。\n\n"
            "引用来源：\n"
            f"{nearby_text}"
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
            text = " ".join(
                line.strip()
                for line in doc.page_content.splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            )
            snippets.append(text[:360])

        citations = []
        for doc in answer_docs[:4]:
            citation = doc.metadata.get("citation", "未知来源")
            if citation not in citations:
                citations.append(citation)

        direct_evidence = AnswerGenerator._direct_evidence_sentence(question, answer_docs)
        if direct_evidence:
            conclusion = f"根据《{primary.metadata.get('title', '未知文档')}》，{direct_evidence}"
        else:
            conclusion = (
                f"根据知识库，最相关的制度是《{primary.metadata.get('title', '未知文档')}》，"
                f"问题主要涉及{primary.metadata.get('process_type', '相关流程')}。"
            )

        return (
            "结论：\n"
            f"{conclusion}\n\n"
            "办理/处理步骤：\n"
            + "\n".join(f"{index + 1}. {snippet}" for index, snippet in enumerate(snippets[:3]))
            + "\n\n所需材料：\n"
            "- 请参考下方引用来源中的“所需材料”章节。\n"
            "- 若涉及高风险流程，请补充主管、系统负责人或信息安全审批记录。\n\n"
            "注意事项：\n"
            f"- 风险等级：{primary.metadata.get('risk_level', '未知')}。\n"
            + AnswerGenerator._business_guardrail(primary)
            + "- 该回答由本地抽取式模板生成；配置 LLM API key 后可获得更自然的总结。\n\n"
            "引用来源：\n"
            + "\n".join(f"- {citation}" for citation in citations)
        )

    @staticmethod
    def _business_guardrail(primary: Document) -> str:
        risk_level = str(primary.metadata.get("risk_level", ""))
        process_type = str(primary.metadata.get("process_type", ""))
        title = str(primary.metadata.get("title", ""))
        high_risk_terms = ("数据", "生产", "合同", "付款", "印章", "监管", "权限", "审计")
        if risk_level == "高" or any(term in process_type + title for term in high_risk_terms):
            return (
                "- 该问题涉及高风险或合规敏感流程，需保留系统流水、审批意见和执行证据；"
                "不得用口头确认替代系统审批。\n"
            )
        return ""

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
