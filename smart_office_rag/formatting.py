import re
from typing import Dict, List

from .types import Document


SECTION_NAMES = ("结论", "办理/处理步骤", "所需材料", "注意事项", "引用来源")


class AnswerFormatter:
    @classmethod
    def build(
        cls,
        question: str,
        answer: str,
        docs: List[Document],
        sources: List[Dict[str, str]],
        refused: bool,
        refusal_reason: str = "",
    ) -> Dict[str, object]:
        sections = cls._parse_sections(answer)
        answer_type = cls._classify(question, refused)
        highlights = cls._extract_highlights(question, answer, docs)
        citations = cls._citation_items(sources, sections.get("引用来源", ""))
        confidence = cls._confidence(refused, docs, highlights)
        payload = {
            "answer_type": answer_type,
            "refused": refused,
            "refusal_reason": refusal_reason,
            "confidence": confidence,
            "conclusion": cls._clean_section(sections.get("结论", "")),
            "steps": cls._list_items(sections.get("办理/处理步骤", "")),
            "materials": cls._list_items(sections.get("所需材料", "")),
            "notes": cls._list_items(sections.get("注意事项", "")),
            "citations": citations,
            "highlights": highlights,
            "raw_answer": answer,
        }
        if not payload["conclusion"]:
            payload["conclusion"] = cls._first_non_empty_line(answer)
        return payload

    @classmethod
    def to_markdown(cls, payload: Dict[str, object]) -> str:
        lines = ["结论：", str(payload.get("conclusion", "")).strip(), ""]
        highlights = payload.get("highlights") or []
        if highlights:
            lines.extend(["关键信息：", *[f"- {item}" for item in highlights], ""])
        for label, key in (
            ("办理/处理步骤", "steps"),
            ("所需材料", "materials"),
            ("注意事项", "notes"),
            ("引用来源", "citations"),
        ):
            items = payload.get(key) or []
            if not items:
                continue
            lines.append(f"{label}：")
            for index, item in enumerate(items, 1):
                text = cls._item_text(item)
                if label == "办理/处理步骤":
                    lines.append(f"{index}. {text}")
                else:
                    lines.append(f"- {text}")
            lines.append("")
        return "\n".join(lines).strip()

    @staticmethod
    def _classify(question: str, refused: bool) -> str:
        if refused:
            return "refusal"
        if any(term in question for term in ("多久", "提前", "时限", "SLA", "几天", "什么时候", "来得及")):
            return "time_limit"
        if any(term in question for term in ("材料", "资料", "要什么", "哪些", "附件", "证明")):
            return "materials"
        if any(term in question for term in ("怎么", "如何", "流程", "步骤", "哪里", "系统", "提交")):
            return "process"
        if any(term in question for term in ("能不能", "可以", "是否", "行不行", "能否")):
            return "eligibility"
        return "general"

    @staticmethod
    def _parse_sections(answer: str) -> Dict[str, str]:
        sections: Dict[str, str] = {}
        pattern = re.compile(r"(?m)^(结论|办理/处理步骤|所需材料|注意事项|引用来源)：?\s*$")
        matches = list(pattern.finditer(answer or ""))
        if not matches:
            return sections
        for index, match in enumerate(matches):
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(answer)
            sections[match.group(1)] = answer[start:end].strip()
        return sections

    @staticmethod
    def _clean_section(text: str) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return " ".join(lines).strip()

    @staticmethod
    def _first_non_empty_line(text: str) -> str:
        for line in (text or "").splitlines():
            line = line.strip()
            if line:
                return line
        return ""

    @staticmethod
    def _list_items(text: str) -> List[str]:
        items: List[str] = []
        for line in (text or "").splitlines():
            line = line.strip()
            if not line:
                continue
            line = re.sub(r"^[-*]\s*", "", line)
            line = re.sub(r"^\d+[.、]\s*", "", line)
            if line:
                items.append(line)
        if not items and text.strip():
            items.append(AnswerFormatter._clean_section(text))
        return items

    @staticmethod
    def _citation_items(sources: List[Dict[str, str]], citation_text: str) -> List[Dict[str, str]]:
        if sources:
            return [
                {
                    "citation": str(source.get("citation", "")),
                    "doc_id": str(source.get("doc_id", "")),
                    "department": str(source.get("department", "")),
                    "process_type": str(source.get("process_type", "")),
                    "risk_level": str(source.get("risk_level", "")),
                }
                for source in sources
            ]
        return [{"citation": item, "doc_id": "", "department": "", "process_type": "", "risk_level": ""} for item in AnswerFormatter._list_items(citation_text)]

    @staticmethod
    def _extract_highlights(question: str, answer: str, docs: List[Document]) -> List[str]:
        text = " ".join([answer] + [doc.page_content for doc in docs[:3]])
        patterns = [
            r"(?:至少)?提前[一二三四五六七八九十\d]+个?工作日",
            r"连续超过[一二三四五六七八九十\d]+个?工作日",
            r"[一二三四五六七八九十\d]+个?工作日",
            r"\d+(?:\.\d+)?\s*(?:元|万元|%)",
            r"[A-Z]{2,}-F-\d+",
        ]
        highlights: List[str] = []
        for pattern in patterns:
            for match in re.findall(pattern, text):
                if match not in highlights:
                    highlights.append(match)
        highlights = AnswerFormatter._drop_contained_highlights(highlights)
        if any(term in question for term in ("多久", "提前", "几天", "时限")):
            time_highlights = [item for item in highlights if "工作日" in item or "自然日" in item or "时限" in item]
            return time_highlights[:4]
        return highlights[:3]

    @staticmethod
    def _drop_contained_highlights(highlights: List[str]) -> List[str]:
        ordered = sorted(highlights, key=len, reverse=True)
        kept: List[str] = []
        for item in ordered:
            if any(item != other and item in other for other in kept):
                continue
            kept.append(item)
        return sorted(kept, key=lambda item: highlights.index(item))

    @staticmethod
    def _confidence(refused: bool, docs: List[Document], highlights: List[str]) -> str:
        if refused:
            return "refused"
        if highlights:
            return "high"
        if docs:
            return "medium"
        return "low"

    @staticmethod
    def _item_text(item) -> str:
        if isinstance(item, dict):
            citation = item.get("citation", "")
            doc_id = item.get("doc_id", "")
            return f"{citation} ({doc_id})" if doc_id else str(citation)
        return str(item)
