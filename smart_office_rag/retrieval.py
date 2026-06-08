from collections import Counter
from collections import defaultdict
import re
from typing import Dict, Iterable, List, Optional

from rank_bm25 import BM25Okapi

from .types import Document


class HybridRetriever:
    def __init__(self, vectorstore, chunks: List[Document], default_k: int = 4):
        self.vectorstore = vectorstore
        self.chunks = chunks
        self.default_k = default_k
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
        vector_docs = self.vector_retriever.invoke(query)
        bm25_docs = self.bm25_retriever.invoke(query)
        for rank, doc in enumerate(vector_docs, 1):
            doc.metadata["vector_rank"] = rank
        for rank, doc in enumerate(bm25_docs, 1):
            doc.metadata["bm25_rank"] = rank
        reranked = self._rrf(vector_docs, bm25_docs)
        if filters:
            reranked = [doc for doc in reranked if self._matches_filters(doc, filters)]
        ordered = self._doc_aware_order(query, reranked)
        return self._expand_primary_doc_context(query, ordered)[:k]

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
        for doc in docs:
            doc_id = str(doc.metadata.get("doc_id", ""))
            doc_scores[doc_id] += float(doc.metadata.get("rrf_score", 0.0))

        for doc in docs:
            doc_id = str(doc.metadata.get("doc_id", ""))
            title = str(doc.metadata.get("title", ""))
            process_type = str(doc.metadata.get("process_type", ""))
            if title and title in query:
                doc_scores[doc_id] += 1.0
            if process_type and process_type in query:
                doc_scores[doc_id] += 0.25

        return sorted(
            docs,
            key=lambda doc: (
                doc_scores[str(doc.metadata.get("doc_id", ""))],
                float(doc.metadata.get("rrf_score", 0.0)),
            ),
            reverse=True,
        )

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
