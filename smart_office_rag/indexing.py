import hashlib
import pickle
import re
from pathlib import Path
from typing import List, Optional

import numpy as np

from .types import Document

SentenceTransformer = None

try:
    import faiss
except Exception:
    faiss = None


class EmbeddingModel:
    def __init__(self, model_name: str, fallback_dim: int = 512):
        self.model_name = model_name
        self.fallback_dim = fallback_dim
        self.model = None
        self.used_fallback = model_name == "local-hashing"
        if model_name == "local-hashing":
            return
        global SentenceTransformer
        if SentenceTransformer is None:
            try:
                from sentence_transformers import SentenceTransformer as LoadedSentenceTransformer

                SentenceTransformer = LoadedSentenceTransformer
            except Exception as exc:
                print(f"Embedding library is unavailable, falling back to local hashing vectors: {exc}")
                self.used_fallback = True
                return
        if SentenceTransformer is not None:
            try:
                self.model = SentenceTransformer(model_name)
            except Exception as exc:
                print(f"Embedding model is unavailable, falling back to local hashing vectors: {exc}")
                self.used_fallback = True

    def embed_documents(self, texts: List[str]) -> np.ndarray:
        if self.model is not None:
            return np.array(
                self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False),
                dtype=np.float32,
            )
        return np.vstack([self._hash_embed(text) for text in texts]).astype(np.float32)

    def embed_query(self, text: str) -> np.ndarray:
        if self.model is not None:
            return np.array(
                self.model.encode([text], normalize_embeddings=True, show_progress_bar=False)[0],
                dtype=np.float32,
            )
        return self._hash_embed(text).astype(np.float32)

    def _hash_embed(self, text: str) -> np.ndarray:
        vector = np.zeros(self.fallback_dim, dtype=np.float32)
        for token in self._tokens(text):
            digest = hashlib.md5(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "little") % self.fallback_dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = np.linalg.norm(vector)
        if norm:
            vector /= norm
        return vector

    @staticmethod
    def _tokens(text: str) -> List[str]:
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


class VectorStore:
    def __init__(self, embeddings: EmbeddingModel, documents: List[Document], vectors: np.ndarray):
        self.embeddings = embeddings
        self.documents = documents
        self.vectors = vectors
        self.index = None
        if faiss is not None and len(vectors):
            self.index = faiss.IndexFlatIP(vectors.shape[1])
            self.index.add(vectors)

    def as_retriever(self, search_kwargs: Optional[dict] = None):
        return VectorRetriever(self, (search_kwargs or {}).get("k", 8))


class VectorRetriever:
    def __init__(self, vectorstore: VectorStore, k: int):
        self.vectorstore = vectorstore
        self.k = k

    def invoke(self, query: str) -> List[Document]:
        query_vector = self.vectorstore.embeddings.embed_query(query)
        if self.vectorstore.index is not None:
            scores, indices = self.vectorstore.index.search(query_vector.reshape(1, -1), self.k)
            ranked_indices = indices[0]
            ranked_scores = scores[0]
        else:
            scores = self.vectorstore.vectors @ query_vector
            ranked_indices = np.argsort(scores)[::-1][: self.k]
            ranked_scores = scores[ranked_indices]

        results: List[Document] = []
        for index, score in zip(ranked_indices, ranked_scores):
            if int(index) < 0:
                continue
            doc = self.vectorstore.documents[int(index)]
            doc.metadata["vector_score"] = round(float(score), 6)
            results.append(doc)
        return results


class VectorIndex:
    def __init__(self, model_name: str, index_path: Path):
        self.model_name = model_name
        self.index_path = Path(index_path)
        self.embeddings = EmbeddingModel(model_name)
        self.vectorstore: Optional[VectorStore] = None

    def load(self, documents: Optional[List[Document]] = None):
        vectors_path = self.index_path / "vectors.npy"
        metadata_path = self.index_path / "documents.pkl"
        if documents is None or not vectors_path.exists():
            return None

        vectors = np.load(vectors_path)
        if metadata_path.exists():
            try:
                with metadata_path.open("rb") as handle:
                    documents = pickle.load(handle)
            except Exception:
                pass
        self.vectorstore = VectorStore(self.embeddings, documents, vectors)
        return self.vectorstore

    def build(self, documents: List[Document]):
        if not documents:
            raise ValueError("Cannot build a vector index with no documents.")
        vectors = self.embeddings.embed_documents([doc.page_content for doc in documents])
        self.vectorstore = VectorStore(self.embeddings, documents, vectors)
        return self.vectorstore

    def save(self) -> None:
        if self.vectorstore is None:
            raise ValueError("No vectorstore to save.")
        self.index_path.mkdir(parents=True, exist_ok=True)
        np.save(self.index_path / "vectors.npy", self.vectorstore.vectors)
        with (self.index_path / "documents.pkl").open("wb") as handle:
            pickle.dump(self.vectorstore.documents, handle)
