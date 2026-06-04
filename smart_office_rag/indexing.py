from pathlib import Path
from typing import List, Optional

from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
import numpy as np

try:
    from langchain_community.vectorstores import FAISS
except Exception:
    FAISS = None


class LocalVectorStore:
    def __init__(self, embeddings: HuggingFaceEmbeddings, documents: List[Document], vectors: np.ndarray):
        self.embeddings = embeddings
        self.documents = documents
        self.vectors = vectors

    def as_retriever(self, search_kwargs: Optional[dict] = None):
        return LocalVectorRetriever(self, (search_kwargs or {}).get("k", 8))


class LocalVectorRetriever:
    def __init__(self, vectorstore: LocalVectorStore, k: int):
        self.vectorstore = vectorstore
        self.k = k

    def invoke(self, query: str) -> List[Document]:
        query_vector = np.array(self.vectorstore.embeddings.embed_query(query), dtype=np.float32)
        query_norm = np.linalg.norm(query_vector)
        if query_norm:
            query_vector = query_vector / query_norm

        scores = self.vectorstore.vectors @ query_vector
        ranked = np.argsort(scores)[::-1][: self.k]
        results: List[Document] = []
        for index in ranked:
            doc = self.vectorstore.documents[int(index)]
            doc.metadata["vector_score"] = round(float(scores[int(index)]), 6)
            results.append(doc)
        return results


class VectorIndex:
    def __init__(self, model_name: str, index_path: Path):
        self.model_name = model_name
        self.index_path = Path(index_path)
        self.embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        self.vectorstore = None

    def load(self, documents: Optional[List[Document]] = None):
        if not self.index_path.exists():
            return None
        if FAISS is None:
            return self._load_local(documents)

        try:
            self.vectorstore = FAISS.load_local(
                str(self.index_path),
                self.embeddings,
                allow_dangerous_deserialization=True,
            )
            return self.vectorstore
        except ImportError:
            return self._load_local(documents)

    def build(self, documents: List[Document]):
        if not documents:
            raise ValueError("Cannot build a vector index with no documents.")
        if FAISS is None:
            return self._build_local(documents)

        try:
            self.vectorstore = FAISS.from_documents(documents, self.embeddings)
            return self.vectorstore
        except ImportError:
            return self._build_local(documents)

    def save(self) -> None:
        if self.vectorstore is None:
            raise ValueError("No vectorstore to save.")
        self.index_path.mkdir(parents=True, exist_ok=True)
        if isinstance(self.vectorstore, LocalVectorStore):
            np.save(self.index_path / "local_vectors.npy", self.vectorstore.vectors)
            return

        self.vectorstore.save_local(str(self.index_path))

    def _load_local(self, documents: Optional[List[Document]] = None):
        vectors_path = self.index_path / "local_vectors.npy"
        if documents is None or not vectors_path.exists():
            return None
        vectors = np.load(vectors_path)
        self.vectorstore = LocalVectorStore(self.embeddings, documents, vectors)
        return self.vectorstore

    def _build_local(self, documents: List[Document]) -> LocalVectorStore:
        vectors = np.array(self.embeddings.embed_documents([doc.page_content for doc in documents]), dtype=np.float32)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        vectors = np.divide(vectors, norms, out=np.zeros_like(vectors), where=norms != 0)
        self.vectorstore = LocalVectorStore(self.embeddings, documents, vectors)
        return self.vectorstore
