from collections import Counter
from collections import defaultdict
import re
from typing import Dict, Iterable, List, Optional

from rank_bm25 import BM25Okapi

from .types import Document


class QueryExpander:
    COLLOQUIAL_MARKERS = (
        "放年假",
        "休年假",
        "放假",
        "咋",
        "怎么弄",
        "咋办",
        "能不能",
        "可以吗",
        "行不行",
        "来得及",
        "打款",
        "盖章",
        "系统进不去",
        "登录不了",
        "客户名单",
    )

    DOMAIN_EXPANSIONS = (
        (
            ("年假", "休假", "放假", "请假", "假期"),
            ("员工请假与休假管理制度", "请假申请", "年假申请", "审批 SLA", "提前", "工作日"),
        ),
        (
            ("报销", "发票", "打款", "付款", "费用"),
            ("费用报销", "报销申请", "财务审批", "所需材料", "发票", "付款"),
        ),
        (
            ("VPN", "远程", "账号", "权限", "系统进不去", "登录不了"),
            ("IT 权限申请", "VPN 权限", "账号权限", "信息安全", "审批流程"),
        ),
        (
            ("合同", "法务", "盖章", "用印", "供应商"),
            ("合同评审", "法务审核", "采购流程", "印章审批", "归档"),
        ),
        (
            ("数据", "导出", "客户名单", "外发", "脱敏"),
            ("数据导出", "客户数据", "信息安全", "审批", "留痕", "高风险"),
        ),
    )

    INTENT_EXPANSIONS = (
        (("提前", "多久", "几天", "什么时候", "来得及"), ("时限", "审批 SLA", "工作日", "至少", "超过")),
        (("怎么办", "怎么弄", "怎么申请", "咋办", "在哪"), ("办理步骤", "流程", "系统提交", "申请")),
        (("要什么", "哪些材料", "材料", "资料"), ("所需材料", "附件", "证明", "表单")),
        (("能不能", "可以吗", "行不行", "是否可以"), ("适用范围", "注意事项", "例外流程", "审批")),
    )

    @classmethod
    def expand(cls, query: str) -> str:
        if not cls.should_expand(query):
            return query
        additions: List[str] = []
        for triggers, expansions in cls.DOMAIN_EXPANSIONS + cls.INTENT_EXPANSIONS:
            if any(trigger in query for trigger in triggers):
                additions.extend(term for term in expansions if term not in query)
        if not additions:
            return query
        deduped = list(dict.fromkeys(additions))
        return f"{query} {' '.join(deduped)}"

    @classmethod
    def should_expand(cls, query: str) -> bool:
        if any(marker in query for marker in cls.COLLOQUIAL_MARKERS):
            return True
        chinese_chars = re.findall(r"[\u4e00-\u9fff]", query)
        asks_permission = any(term in query for term in ("可以", "能", "行不行"))
        asks_time = any(term in query for term in ("几天", "多久", "什么时候", "提前"))
        domain_hint = any(term in query for term in ("年假", "报销", "权限", "合同", "数据"))
        return len(chinese_chars) <= 14 and domain_hint and (asks_permission or asks_time)


class HybridRetriever:
    def __init__(
        self,
        vectorstore,
        chunks: List[Document],
        default_k: int = 4,
        sentence_window_size: int = 0,
        structured_boost: bool = False,
    ):
        self.vectorstore = vectorstore
        self.chunks = chunks
        self.default_k = default_k
        self.sentence_window_size = sentence_window_size
        self.structured_boost = structured_boost
        candidate_k = max(default_k * 4, 20)
        self.vector_retriever = vectorstore.as_retriever(search_kwargs={"k": candidate_k})
        self.bm25_retriever = BM25TextRetriever(chunks, k=candidate_k)

    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, str]] = None,
    ) -> List[Document]:
        k = top_k or self.default_k
        expanded_query = QueryExpander.expand(query)
        vector_docs = self.vector_retriever.invoke(query)
        bm25_docs = self.bm25_retriever.invoke(query)
        ranked_lists: List[Iterable[Document]] = [vector_docs, bm25_docs]
        if expanded_query != query:
            expanded_vector_docs = self.vector_retriever.invoke(expanded_query)
            expanded_bm25_docs = self.bm25_retriever.invoke(expanded_query)
            ranked_lists.extend([expanded_vector_docs, expanded_bm25_docs])
            for rank, doc in enumerate(expanded_vector_docs, 1):
                doc.metadata["expanded_vector_rank"] = rank
                doc.metadata["expanded_query"] = expanded_query
            for rank, doc in enumerate(expanded_bm25_docs, 1):
                doc.metadata["expanded_bm25_rank"] = rank
                doc.metadata["expanded_query"] = expanded_query
        for rank, doc in enumerate(vector_docs, 1):
            doc.metadata["vector_rank"] = rank
            doc.metadata["expanded_query"] = expanded_query
        for rank, doc in enumerate(bm25_docs, 1):
            doc.metadata["bm25_rank"] = rank
            doc.metadata["expanded_query"] = expanded_query
        reranked = self._rrf(*ranked_lists)
        if filters:
            reranked = [doc for doc in reranked if self._matches_filters(doc, filters)]
        ordered = self._doc_aware_order(expanded_query, reranked)
        if self.structured_boost:
            ordered = self._structured_order(expanded_query, ordered)
        if self.sentence_window_size > 0:
            ordered = self._expand_sentence_window(ordered)
        return self._expand_primary_doc_context(expanded_query, ordered)[:k]

    @staticmethod
    def _matches_filters(doc: Document, filters: Dict[str, str]) -> bool:
        for key, value in filters.items():
            if not value or value == "全部":
                continue
            if str(doc.metadata.get(key, "")) != value:
                return False
        return True

    @staticmethod
    def _doc_key(doc: Document) -> str:
        return str(doc.metadata.get("chunk_id") or hash(doc.page_content))

    def _rrf(self, *ranked_lists: Iterable[Document], rrf_k: int = 60) -> List[Document]:
        scores = defaultdict(float)
        docs_by_key = {}
        for ranked_docs in ranked_lists:
            for rank, doc in enumerate(ranked_docs):
                key = self._doc_key(doc)
                docs_by_key[key] = doc
                scores[key] += 1.0 / (rrf_k + rank + 1)

        ordered_keys = sorted(scores, key=scores.get, reverse=True)
        results: List[Document] = []
        for key in ordered_keys:
            doc = docs_by_key[key]
            doc.metadata["rrf_score"] = round(scores[key], 6)
            results.append(doc)
        return results

    @staticmethod
    def _doc_aware_order(query: str, docs: List[Document]) -> List[Document]:
        doc_scores = defaultdict(float)
        best_bm25_rank: Dict[str, int] = {}
        for doc in docs:
            doc_id = str(doc.metadata.get("doc_id", ""))
            doc_scores[doc_id] += float(doc.metadata.get("rrf_score", 0.0))
            bm25_rank = doc.metadata.get("bm25_rank")
            if bm25_rank:
                rank = int(bm25_rank)
                best_bm25_rank[doc_id] = min(rank, best_bm25_rank.get(doc_id, rank))

        for doc in docs:
            doc_id = str(doc.metadata.get("doc_id", ""))
            title = str(doc.metadata.get("title", ""))
            process_type = str(doc.metadata.get("process_type", ""))
            if title and title in query:
                doc_scores[doc_id] += 1.0
            if process_type and process_type in query:
                doc_scores[doc_id] += 0.25

        for doc_id, rank in best_bm25_rank.items():
            doc_scores[doc_id] += 2.0 / rank

        return sorted(
            docs,
            key=lambda doc: (
                doc_scores[str(doc.metadata.get("doc_id", ""))],
                float(doc.metadata.get("rrf_score", 0.0)),
            ),
            reverse=True,
        )

    def _structured_order(self, query: str, docs: List[Document]) -> List[Document]:
        hints = self._structured_hints(query)
        for doc in docs:
            score = float(doc.metadata.get("rrf_score", 0.0))
            metadata_text = " ".join(str(value) for value in doc.metadata.values())
            title = str(doc.metadata.get("title", ""))
            process_type = str(doc.metadata.get("process_type", ""))
            section_type = str(doc.metadata.get("section_type", ""))
            try:
                priority = float(str(doc.metadata.get("priority", "50") or "50").split(",")[0])
            except ValueError:
                priority = 50.0
            if title and title in query:
                score += 0.08
            if process_type and process_type in query:
                score += 0.06
            if hints.get("department") and str(doc.metadata.get("department")) == hints["department"]:
                score += 0.08
            if hints.get("risk_level") and str(doc.metadata.get("risk_level")) == hints["risk_level"]:
                score += 0.05
            for term in hints.get("terms", []):
                if term in metadata_text or term in doc.page_content:
                    score += 0.025
            if hints.get("section_type") and section_type == hints["section_type"]:
                score += 0.04
            if hints.get("version_sensitive"):
                score += min(priority, 100.0) / 1000.0
                if str(doc.metadata.get("supersedes", "")):
                    score += 0.05
            doc.metadata["structured_score"] = round(score, 6)
        return sorted(
            docs,
            key=lambda doc: (
                float(doc.metadata.get("structured_score", 0.0)),
                float(doc.metadata.get("rrf_score", 0.0)),
            ),
            reverse=True,
        )

    @staticmethod
    def _structured_hints(query: str) -> Dict[str, object]:
        hints: Dict[str, object] = {"terms": []}
        department_terms = {
            "HR": ("请假", "休假", "考勤", "绩效", "入职", "离职", "员工"),
            "Finance": ("报销", "发票", "付款", "预算", "备用金", "金额"),
            "IT": ("账号", "VPN", "系统", "权限", "电脑", "变更"),
            "Security": ("数据", "客户信息", "导出", "安全", "账号"),
            "Legal": ("合同", "法务", "归档", "保密"),
            "Procurement": ("采购", "供应商", "招标", "验收"),
            "Admin": ("印章", "会议室", "出差", "访客"),
        }
        for department, terms in department_terms.items():
            if any(term in query for term in terms):
                hints["department"] = department
                hints["terms"].extend(terms)
                break
        if any(term in query for term in ("高风险", "生产", "客户数据", "付款", "合同", "印章", "权限")):
            hints["risk_level"] = "高"
        if any(term in query for term in ("材料", "附件", "提交", "票据", "证明")):
            hints["section_type"] = "appendix"
            hints["terms"].extend(["材料", "附件", "清单", "证明"])
        if any(term in query for term in ("审批", "流程", "步骤", "办理")):
            hints["terms"].extend(["审批", "流程", "步骤", "办理"])
        if any(term in query for term in ("时限", "多久", "提前", "SLA")):
            hints["terms"].extend(["时限", "工作日", "提前", "SLA"])
        if any(term in query for term in ("金额", "额度", "阈值", "超过")):
            hints["terms"].extend(["金额", "额度", "阈值", "超过"])
        return hints

    @staticmethod
    def _structured_hints(query: str) -> Dict[str, object]:
        hints: Dict[str, object] = {"terms": []}
        department_terms = {
            "HR": ("请假", "休假", "考勤", "绩效", "入职", "离职", "员工"),
            "Finance": ("报销", "发票", "付款", "预算", "备用金", "金额", "经费"),
            "IT": ("账号", "VPN", "系统", "权限", "电脑", "远程", "办公"),
            "Security": ("数据", "客户信息", "导出", "安全", "外发"),
            "Legal": ("合同", "法务", "归档", "保密"),
            "Procurement": ("采购", "供应商", "招标", "验收"),
            "Admin": ("印章", "会议室", "出差", "差旅", "住宿"),
        }
        for department, terms in department_terms.items():
            if any(term in query for term in terms):
                hints["department"] = department
                hints["terms"].extend(terms)
                break
        if any(term in query for term in ("高风险", "生产", "客户数据", "付款", "合同", "印章", "权限")):
            hints["risk_level"] = "high"
        if any(term in query for term in ("材料", "附件", "提交", "票据", "证明")):
            hints["section_type"] = "appendix"
            hints["terms"].extend(["材料", "附件", "清单", "证明"])
        if any(term in query for term in ("审批", "流程", "步骤", "办理")):
            hints["terms"].extend(["审批", "流程", "步骤", "办理"])
        if any(term in query for term in ("时限", "多久", "提前", "SLA")):
            hints["terms"].extend(["时限", "工作日", "提前", "SLA"])
        if any(term in query for term in ("金额", "额度", "阈值", "超过")):
            hints["terms"].extend(["金额", "额度", "阈值", "超过"])
        if any(term in query for term in ("版本", "新版", "旧版", "补充通知", "优先", "冲突", "2025", "2026")):
            hints["version_sensitive"] = True
            hints["terms"].extend(["版本", "生效", "优先级", "补充通知", "supersedes"])
        return hints

    def _expand_sentence_window(self, docs: List[Document]) -> List[Document]:
        if not docs:
            return []
        by_position = {}
        for doc in self.chunks:
            if doc.metadata.get("chunk_type") != "sentence_child":
                continue
            key = (
                doc.metadata.get("doc_id"),
                doc.metadata.get("section_path"),
                int(doc.metadata.get("sentence_index", -1)),
            )
            by_position[key] = doc

        expanded: List[Document] = []
        seen = set()
        for doc in docs:
            if doc.metadata.get("chunk_type") != "sentence_child":
                key = self._doc_key(doc)
                if key not in seen:
                    expanded.append(doc)
                    seen.add(key)
                continue
            doc_id = doc.metadata.get("doc_id")
            section_path = doc.metadata.get("section_path")
            sentence_index = int(doc.metadata.get("sentence_index", 0))
            for index in range(sentence_index - self.sentence_window_size, sentence_index + self.sentence_window_size + 1):
                neighbor = by_position.get((doc_id, section_path, index))
                if not neighbor:
                    continue
                key = self._doc_key(neighbor)
                if key in seen:
                    continue
                neighbor.metadata["sentence_window_hit"] = doc.metadata.get("chunk_id")
                neighbor.metadata["sentence_window_center"] = sentence_index
                expanded.append(neighbor)
                seen.add(key)
        return expanded

    def _expand_primary_doc_context(self, query: str, docs: List[Document]) -> List[Document]:
        if not docs:
            return []

        primary_doc_id = docs[0].metadata.get("doc_id")
        seen = {self._doc_key(doc) for doc in docs}
        primary_docs = [doc for doc in docs if doc.metadata.get("doc_id") == primary_doc_id]
        other_docs = [doc for doc in docs if doc.metadata.get("doc_id") != primary_doc_id]
        query_terms = KeywordRetriever._terms(query)

        supplemental = []
        for doc in self.chunks:
            if doc.metadata.get("doc_id") != primary_doc_id:
                continue
            if self._doc_key(doc) in seen:
                continue
            doc_terms = KeywordRetriever._terms(doc.page_content + " " + " ".join(str(v) for v in doc.metadata.values()))
            overlap = sum((query_terms & doc_terms).values())
            doc.metadata["keyword_score"] = overlap
            supplemental.append((overlap, int(doc.metadata.get("chunk_index", 0)), doc))

        supplemental.sort(key=lambda item: (item[0], -item[1]), reverse=True)
        return primary_docs + [doc for _, _, doc in supplemental] + other_docs


class KeywordRetriever:
    def __init__(self, chunks: List[Document], k: int = 8):
        self.chunks = chunks
        self.k = k

    def invoke(self, query: str) -> List[Document]:
        query_terms = self._terms(query)
        scored = []
        for doc in self.chunks:
            doc_terms = self._terms(doc.page_content + " " + " ".join(str(v) for v in doc.metadata.values()))
            overlap = sum((query_terms & doc_terms).values())
            if overlap:
                doc.metadata["keyword_score"] = overlap
                scored.append((overlap, doc))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [doc for _, doc in scored[: self.k]]

    @staticmethod
    def _terms(text: str) -> Counter:
        return Counter(KeywordRetriever.tokens(text))

    @staticmethod
    def tokens(text: str) -> List[str]:
        terms = []
        terms.extend(re.findall(r"[A-Za-z0-9_]+", text.lower()))
        chinese_runs = re.findall(r"[\u4e00-\u9fff]+", text)
        for run in chinese_runs:
            if len(run) == 1:
                terms.append(run)
            else:
                terms.extend(run[index : index + 2] for index in range(len(run) - 1))
                terms.extend(run[index : index + 3] for index in range(len(run) - 2))
        return terms


class BM25TextRetriever:
    def __init__(self, chunks: List[Document], k: int = 8):
        self.chunks = chunks
        self.k = k
        self.corpus_tokens = [
            KeywordRetriever.tokens(doc.page_content + " " + " ".join(str(v) for v in doc.metadata.values()))
            for doc in chunks
        ]
        self.bm25 = BM25Okapi(self.corpus_tokens)

    def invoke(self, query: str) -> List[Document]:
        query_tokens = KeywordRetriever.tokens(query)
        scores = self.bm25.get_scores(query_tokens)
        ranked = sorted(range(len(scores)), key=lambda index: scores[index], reverse=True)[: self.k]
        results: List[Document] = []
        for index in ranked:
            if scores[index] <= 0:
                continue
            doc = self.chunks[index]
            doc.metadata["bm25_score"] = round(float(scores[index]), 6)
            results.append(doc)
        return results
