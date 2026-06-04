from dataclasses import dataclass
from collections import Counter
import re
from typing import Dict, List, Optional

from langchain_core.documents import Document

from .config import DEFAULT_CONFIG, RAGConfig
from .documents import PolicyDocumentLoader
from .generator import AnswerGenerator
from .indexing import VectorIndex
from .retrieval import HybridRetriever
from .retrieval import KeywordRetriever


@dataclass
class RAGResponse:
    answer: str
    sources: List[Dict[str, str]]
    chunks: List[Document]


class EnterpriseKnowledgeRAG:
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
        "食堂菜谱",
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

    def __init__(self, config: RAGConfig = DEFAULT_CONFIG):
        self.config = config
        self.loader = PolicyDocumentLoader(config.data_path)
        self.parents: List[Document] = []
        self.chunks: List[Document] = []
        self.index = None
        self.retriever: Optional[HybridRetriever] = None
        self.generator = AnswerGenerator(
            model_name=config.llm_model,
            base_url=config.llm_base_url,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    def initialize(self, rebuild_index: bool = False) -> None:
        self.parents = self.loader.load_parent_documents()
        self.chunks = self.loader.split_documents(self.parents)

        if not self.config.use_vector_index:
            self.retriever = KeywordFallbackRetriever(self.chunks, default_k=self.config.top_k)
            return

        try:
            self.index = VectorIndex(self.config.embedding_model, self.config.index_path)
            vectorstore = None if rebuild_index else self.index.load(self.chunks)
            if vectorstore is None:
                vectorstore = self.index.build(self.chunks)
                self.index.save()
            self.retriever = HybridRetriever(vectorstore, self.chunks, default_k=self.config.top_k)
        except Exception as exc:
            print(f"Vector index is unavailable, falling back to keyword retrieval: {exc}")
            self.retriever = KeywordFallbackRetriever(self.chunks, default_k=self.config.top_k)

    def ask(self, question: str, filters: Optional[Dict[str, str]] = None) -> RAGResponse:
        if self.retriever is None:
            self.initialize()

        assert self.retriever is not None
        if self._is_out_of_scope(question):
            answer = self.generator.generate(question, [])
            return RAGResponse(answer=answer, sources=[], chunks=[])
        chunks = self.retriever.search(question, top_k=self.config.top_k, filters=filters)
        if self._is_low_confidence(question, chunks):
            answer = self.generator.generate(question, [])
            return RAGResponse(answer=answer, sources=[], chunks=[])
        answer = self.generator.generate(question, chunks)
        source_chunks = self._answer_source_chunks(question, chunks)
        return RAGResponse(answer=answer, sources=self._build_sources(source_chunks), chunks=chunks)

    def _answer_source_chunks(self, question: str, chunks: List[Document]) -> List[Document]:
        if not chunks:
            return []
        primary_doc_id = chunks[0].metadata.get("doc_id")
        primary_chunks = [doc for doc in chunks if doc.metadata.get("doc_id") == primary_doc_id]
        process_type = str(chunks[0].metadata.get("process_type", ""))
        return self.generator._prioritize_answer_docs(question, primary_chunks, process_type)

    @classmethod
    def _is_out_of_scope(cls, question: str) -> bool:
        return any(term in question for term in cls.OUT_OF_SCOPE_TERMS)

    @staticmethod
    def _is_low_confidence(question: str, chunks: List[Document]) -> bool:
        if not chunks:
            return True
        question_terms = KeywordRetriever._terms(question)
        max_overlap = 0
        for doc in chunks:
            doc_terms = KeywordRetriever._terms(doc.page_content + " " + " ".join(str(v) for v in doc.metadata.values()))
            max_overlap = max(max_overlap, sum((question_terms & doc_terms).values()))
        return max_overlap < 3

    @staticmethod
    def _build_sources(chunks: List[Document]) -> List[Dict[str, str]]:
        seen = set()
        sources: List[Dict[str, str]] = []
        for doc in chunks:
            citation = doc.metadata.get("citation", "未知来源")
            if citation in seen:
                continue
            seen.add(citation)
            sources.append(
                {
                    "doc_id": doc.metadata.get("doc_id", "未知ID"),
                    "citation": citation,
                    "title": doc.metadata.get("title", "未知文档"),
                    "section": doc.metadata.get("section", "未知章节"),
                    "department": doc.metadata.get("department", "未知"),
                    "process_type": doc.metadata.get("process_type", "未知"),
                    "risk_level": doc.metadata.get("risk_level", "未知"),
                    "updated_at": doc.metadata.get("updated_at", "未知"),
                    "source_file": doc.metadata.get("source_file", "未知文件"),
                }
            )
        return sources

    def get_filter_options(self) -> Dict[str, List[str]]:
        if not self.chunks:
            self.parents = self.loader.load_parent_documents()
            self.chunks = self.loader.split_documents(self.parents)

        options = {"department": ["全部"], "process_type": ["全部"], "risk_level": ["全部"]}
        for key in options:
            values = sorted({str(doc.metadata.get(key)) for doc in self.chunks if doc.metadata.get(key)})
            options[key].extend(values)
        return options


class KeywordFallbackRetriever:
    def __init__(self, chunks: List[Document], default_k: int = 4):
        self.chunks = chunks
        self.default_k = default_k

    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, str]] = None,
    ) -> List[Document]:
        query_terms = self._terms(query)
        scored = []
        for doc in self.chunks:
            if filters and not self._matches_filters(doc, filters):
                continue
            doc_terms = self._terms(doc.page_content + " " + " ".join(str(v) for v in doc.metadata.values()))
            overlap = sum((query_terms & doc_terms).values())
            if overlap:
                doc.metadata["rrf_score"] = overlap
                scored.append((overlap, doc))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [doc for _, doc in scored[: top_k or self.default_k]]

    @staticmethod
    def _terms(text: str) -> Counter:
        terms = []
        terms.extend(re.findall(r"[A-Za-z0-9_]+", text.lower()))
        chinese_runs = re.findall(r"[\u4e00-\u9fff]+", text)
        for run in chinese_runs:
            if len(run) == 1:
                terms.append(run)
            else:
                terms.extend(run[index : index + 2] for index in range(len(run) - 1))
                terms.extend(run[index : index + 3] for index in range(len(run) - 2))
        return Counter(terms)

    @staticmethod
    def _matches_filters(doc: Document, filters: Dict[str, str]) -> bool:
        for key, value in filters.items():
            if not value or value == "全部":
                continue
            if str(doc.metadata.get(key, "")) != value:
                return False
        return True
