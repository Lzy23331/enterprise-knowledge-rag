import hashlib
import os
import pickle
import re
import time
from pathlib import Path
from typing import List, Optional

import numpy as np

from .types import Document

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("HF_HOME", str(PROJECT_ROOT / ".cache" / "huggingface"))
if os.getenv("SMARTOFFICE_EMBEDDING_LOCAL_ONLY", "1") == "1":
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

SentenceTransformer = None

try:
    import faiss
except Exception:
    faiss = None


class EmbeddingModel:
    def __init__(
        self,
        model_name: str,
        fallback_dim: int = 512,
        trust_remote_code: bool = False,
        query_instruction: str = "",
        document_instruction: str = "",
        normalize_embeddings: bool = True,
        max_seq_length: Optional[int] = None,
        require_real_embedding: bool = False,
    ):
        self.model_name = model_name
        self.fallback_dim = fallback_dim
        self.trust_remote_code = trust_remote_code
        self.query_instruction = query_instruction
        self.document_instruction = document_instruction
        self.normalize_embeddings = normalize_embeddings
        self.max_seq_length = max_seq_length
        self.require_real_embedding = require_real_embedding
        self.model = None
        self.load_mode = "local-hashing" if model_name == "local-hashing" else "uninitialized"
        self.used_fallback = model_name == "local-hashing"
        self.model_load_ms = 0.0
        self.embedding_dimension = fallback_dim if model_name == "local-hashing" else 0
        if model_name == "local-hashing":
            return
        started = time.perf_counter()
        global SentenceTransformer
        if SentenceTransformer is None:
            try:
                from sentence_transformers import SentenceTransformer as LoadedSentenceTransformer

                SentenceTransformer = LoadedSentenceTransformer
            except Exception as exc:
                self._handle_unavailable(f"Embedding library is unavailable: {exc}")
                return
        if SentenceTransformer is not None:
            try:
                local_only = os.getenv("SMARTOFFICE_EMBEDDING_LOCAL_ONLY", "1") == "1"
                if local_only:
                    os.environ.setdefault("HF_HUB_OFFLINE", "1")
                    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
                self.model = SentenceTransformer(
                    model_name,
                    local_files_only=local_only,
                    trust_remote_code=trust_remote_code,
                )
                if max_seq_length:
                    self.model.max_seq_length = max_seq_length
                if hasattr(self.model, "get_sentence_embedding_dimension"):
                    self.embedding_dimension = int(self.model.get_sentence_embedding_dimension() or 0)
                self.load_mode = "local_cache" if local_only else "online_or_cache"
            except Exception as exc:
                self._handle_unavailable(f"Embedding model is unavailable: {exc}")
            finally:
                self.model_load_ms = (time.perf_counter() - started) * 1000

    def _handle_unavailable(self, message: str) -> None:
        if self.require_real_embedding:
            raise RuntimeError(message)
        print(f"{message}, falling back to local hashing vectors.")
        self.load_mode = "fallback"
        self.used_fallback = True
        self.embedding_dimension = self.fallback_dim

    def embed_documents(self, texts: List[str]) -> np.ndarray:
        if self.model is not None:
            encoded_texts = [self._with_instruction(text, self.document_instruction) for text in texts]
            return np.array(
                self.model.encode(encoded_texts, normalize_embeddings=self.normalize_embeddings, show_progress_bar=False),
                dtype=np.float32,
            )
        return np.vstack([self._hash_embed(text) for text in texts]).astype(np.float32)

    def embed_query(self, text: str) -> np.ndarray:
        if self.model is not None:
            encoded_text = self._with_instruction(text, self.query_instruction)
            return np.array(
                self.model.encode([encoded_text], normalize_embeddings=self.normalize_embeddings, show_progress_bar=False)[0],
                dtype=np.float32,
            )
        return self._hash_embed(text).astype(np.float32)

    @staticmethod
    def _with_instruction(text: str, instruction: str) -> str:
        if not instruction:
            return text
        return instruction + text

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
    def __init__(
        self,
        model_name: str,
        index_path: Path,
        trust_remote_code: bool = False,
        query_instruction: str = "",
        document_instruction: str = "",
        normalize_embeddings: bool = True,
        max_seq_length: Optional[int] = None,
        require_real_embedding: bool = False,
    ):
        self.model_name = model_name
        self.index_path = Path(index_path)
        self.embeddings = EmbeddingModel(
            model_name,
            trust_remote_code=trust_remote_code,
            query_instruction=query_instruction,
            document_instruction=document_instruction,
            normalize_embeddings=normalize_embeddings,
            max_seq_length=max_seq_length,
            require_real_embedding=require_real_embedding,
        )
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
