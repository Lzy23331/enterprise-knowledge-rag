import re
from pathlib import Path
from typing import Dict, List

from .loaders import MultiFormatPolicyLoader
from .types import Document


HEADER_PATTERN = re.compile(r"^(#{1,3})\s+(.+?)\s*$", re.MULTILINE)
FORMAL_SECTION_PATTERN = re.compile(
    r"^\s*(第[一二三四五六七八九十百0-9]+章\s+.+?|第[一二三四五六七八九十百0-9]+条\s*.*|附件[一二三四五六七八九十百0-9]+.*|附表[一二三四五六七八九十百0-9]+.*|修订记录|审批流程|制度目录|典型场景与处理口径|监督检查矩阵|解释权归属)\s*$",
    re.MULTILINE,
)
CHAPTER_NO_PATTERN = re.compile(r"^第([一二三四五六七八九十百0-9]+)章")
ARTICLE_NO_PATTERN = re.compile(r"^第([一二三四五六七八九十百0-9]+)条")


class PolicyDocumentLoader:
    def __init__(
        self,
        data_path: Path,
        pdf_path: Path | None = None,
        pdf_mode: str = "pypdf",
        chunk_strategy: str = "markdown_headers",
        fixed_chunk_size: int = 900,
        fixed_chunk_overlap: int = 120,
        semantic_embedding_model: str = "BAAI/bge-small-zh-v1.5",
        semantic_similarity_threshold: float = 0.72,
        semantic_max_chunk_size: int = 1200,
    ):
        self.data_path = Path(data_path)
        self.pdf_path = Path(pdf_path) if pdf_path else None
        self.pdf_mode = pdf_mode
        self.chunk_strategy = chunk_strategy
        self.fixed_chunk_size = fixed_chunk_size
        self.fixed_chunk_overlap = fixed_chunk_overlap
        self.semantic_embedding_model = semantic_embedding_model
        self.semantic_similarity_threshold = semantic_similarity_threshold
        self.semantic_max_chunk_size = semantic_max_chunk_size

    def load_parent_documents(self) -> List[Document]:
        if not self.data_path.exists():
            raise FileNotFoundError(f"Policy data path not found: {self.data_path}")

        return MultiFormatPolicyLoader(
            markdown_path=self.data_path,
            pdf_path=self.pdf_path,
            pdf_mode=self.pdf_mode,
        ).load()

    def split_documents(self, documents: List[Document]) -> List[Document]:
        chunks: List[Document] = []
        for parent in documents:
            if self.chunk_strategy == "whole_document":
                split_docs = [Document(page_content=parent.page_content, metadata={"section_1": parent.metadata.get("title", "全文")})]
            elif self.chunk_strategy == "fixed_window":
                split_docs = self._split_fixed_window(
                    parent.page_content,
                    chunk_size=self.fixed_chunk_size,
                    overlap=self.fixed_chunk_overlap,
                )
            elif self.chunk_strategy == "recursive_character":
                split_docs = self._split_recursive_character(
                    parent.page_content,
                    chunk_size=self.fixed_chunk_size,
                    overlap=self.fixed_chunk_overlap,
                )
            elif self.chunk_strategy == "markdown_headers":
                if parent.metadata.get("source_type") == "pdf":
                    split_docs = self._split_formal_policy(parent.page_content)
                else:
                    split_docs = self._split_markdown_by_headers(parent.page_content)
            elif self.chunk_strategy == "semantic":
                split_docs = self._split_semantic(parent)
            else:
                raise ValueError(f"Unsupported chunk strategy: {self.chunk_strategy}")

            for index, chunk in enumerate(split_docs):
                section = (
                    chunk.metadata.get("section_path")
                    or chunk.metadata.get("section_3")
                    or chunk.metadata.get("section_2")
                    or chunk.metadata.get("section_1")
                    or parent.metadata.get("title", "未知章节")
                )
                child_id = f"{parent.metadata['doc_id']}-{index + 1}"
                chunk.metadata.update(parent.metadata)
                chunk.metadata.update(
                    {
                        "chunk_id": child_id,
                        "chunk_type": "child",
                        "chunk_index": index,
                        "section": section,
                        "citation": f"《{parent.metadata.get('title', '未知文档')}》{section}",
                        "chunk_size": len(chunk.page_content),
                    }
                )
                chunks.append(chunk)
        return chunks

    def _split_semantic(self, parent: Document) -> List[Document]:
        if parent.metadata.get("source_type") == "pdf":
            base_units = self._split_formal_policy(parent.page_content)
        else:
            base_units = self._split_markdown_by_headers(parent.page_content)
        base_units = [unit for unit in base_units if unit.page_content.strip()]
        if len(base_units) <= 1:
            return base_units

        from .indexing import EmbeddingModel

        embeddings = EmbeddingModel(self.semantic_embedding_model)
        vectors = embeddings.embed_documents([unit.page_content for unit in base_units])

        documents: List[Document] = []
        group_units: List[Document] = [base_units[0]]
        group_start = 0

        def flush(end_index: int) -> None:
            if not group_units:
                return
            content = "\n\n".join(unit.page_content for unit in group_units).strip()
            first_section = self._unit_section(group_units[0])
            last_section = self._unit_section(group_units[-1])
            section = first_section if first_section == last_section else f"{first_section} -> {last_section}"
            documents.append(
                Document(
                    page_content=content,
                    metadata={
                        "section_1": f"语义片段 {len(documents) + 1}",
                        "section_path": section,
                        "section_type": "semantic",
                        "semantic_start_unit": group_start,
                        "semantic_end_unit": end_index,
                        "semantic_unit_count": len(group_units),
                        "semantic_embedding_model": self.semantic_embedding_model,
                        "semantic_similarity_threshold": self.semantic_similarity_threshold,
                    },
                )
            )

        for index in range(1, len(base_units)):
            previous_vector = vectors[index - 1]
            current_vector = vectors[index]
            similarity = float(previous_vector @ current_vector)
            candidate_size = sum(len(unit.page_content) for unit in group_units) + len(base_units[index].page_content)
            if similarity >= self.semantic_similarity_threshold and candidate_size <= self.semantic_max_chunk_size:
                group_units.append(base_units[index])
            else:
                flush(index - 1)
                group_units = [base_units[index]]
                group_start = index
        flush(len(base_units) - 1)
        return documents

    @staticmethod
    def _unit_section(unit: Document) -> str:
        return (
            unit.metadata.get("section_path")
            or unit.metadata.get("section_3")
            or unit.metadata.get("section_2")
            or unit.metadata.get("section_1")
            or "语义片段"
        )

    @staticmethod
    def _split_markdown_by_headers(text: str) -> List[Document]:
        matches = list(HEADER_PATTERN.finditer(text))
        if not matches:
            return [Document(page_content=text.strip(), metadata={})]

        documents: List[Document] = []
        current_sections: Dict[int, str] = {}
        for index, match in enumerate(matches):
            level = len(match.group(1))
            title = match.group(2).strip()
            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            content = text[start:end].strip()
            if not content:
                continue

            current_sections[level] = title
            for deeper_level in range(level + 1, 4):
                current_sections.pop(deeper_level, None)

            metadata = {}
            if 1 in current_sections:
                metadata["section_1"] = current_sections[1]
            if 2 in current_sections:
                metadata["section_2"] = current_sections[2]
            if 3 in current_sections:
                metadata["section_3"] = current_sections[3]
            documents.append(Document(page_content=content, metadata=metadata))
        return documents

    @staticmethod
    def _split_formal_policy(text: str) -> List[Document]:
        matches = list(FORMAL_SECTION_PATTERN.finditer(text))
        if not matches:
            return [Document(page_content=text.strip(), metadata={})]

        documents: List[Document] = []
        current_chapter = ""
        current_article = ""
        for index, match in enumerate(matches):
            title = PolicyDocumentLoader._normalize_formal_section_title(match.group(1))
            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            content = text[start:end].strip()
            if not content:
                continue

            section_type = PolicyDocumentLoader._section_type(title)
            if section_type == "chapter":
                current_chapter = title
                current_article = ""
                metadata = {"section_1": title, "section_type": section_type}
                chapter_no = PolicyDocumentLoader._match_no(CHAPTER_NO_PATTERN, title)
                if chapter_no:
                    metadata["chapter_no"] = chapter_no
            elif section_type == "article":
                current_article = title
                metadata = {"section_1": current_chapter or "正文条款", "section_2": title, "section_type": section_type}
                chapter_no = PolicyDocumentLoader._match_no(CHAPTER_NO_PATTERN, current_chapter)
                article_no = PolicyDocumentLoader._match_no(ARTICLE_NO_PATTERN, title)
                if chapter_no:
                    metadata["chapter_no"] = chapter_no
                if article_no:
                    metadata["article_no"] = article_no
            else:
                current_article = title
                metadata = {"section_1": title, "section_type": section_type}

            if current_chapter and current_article and current_article != current_chapter:
                metadata["section_path"] = f"{current_chapter} / {current_article}"
            elif current_chapter:
                metadata["section_path"] = current_chapter
            else:
                metadata["section_path"] = title
            documents.append(Document(page_content=content, metadata=metadata))
        return documents

    @staticmethod
    def _normalize_formal_section_title(title: str) -> str:
        title = re.sub(r"\s+", " ", title).strip()
        if "条" in title and len(title) > 28:
            return title[:28].rstrip("，。；、：")
        return title

    @staticmethod
    def _section_type(title: str) -> str:
        if title == "修订记录":
            return "revision_record"
        if title == "审批流程":
            return "approval_flow"
        if title == "制度目录":
            return "directory"
        if title == "典型场景与处理口径":
            return "scenario_notes"
        if title == "监督检查矩阵":
            return "control_matrix"
        if title == "解释权归属":
            return "explanation"
        if title.startswith("附件"):
            return "appendix"
        if title.startswith("附表"):
            return "appendix_table"
        if CHAPTER_NO_PATTERN.match(title):
            return "chapter"
        if ARTICLE_NO_PATTERN.match(title):
            return "article"
        return "section"

    @staticmethod
    def _match_no(pattern: re.Pattern, title: str) -> str:
        match = pattern.match(title or "")
        return match.group(1) if match else ""

    @staticmethod
    def _split_fixed_window(text: str, chunk_size: int = 900, overlap: int = 120) -> List[Document]:
        cleaned = "\n".join(line.rstrip() for line in text.splitlines()).strip()
        if not cleaned:
            return []
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive.")
        if overlap < 0 or overlap >= chunk_size:
            raise ValueError("overlap must be non-negative and smaller than chunk_size.")

        documents: List[Document] = []
        start = 0
        index = 1
        while start < len(cleaned):
            end = min(len(cleaned), start + chunk_size)
            content = cleaned[start:end].strip()
            if content:
                documents.append(
                    Document(
                        page_content=content,
                        metadata={
                            "section_1": f"固定窗口片段 {index}",
                            "window_start": start,
                            "window_end": end,
                        },
                    )
                )
            if end >= len(cleaned):
                break
            start = end - overlap
            index += 1
        return documents

    @staticmethod
    def _split_recursive_character(text: str, chunk_size: int = 900, overlap: int = 120) -> List[Document]:
        cleaned = "\n".join(line.rstrip() for line in text.splitlines()).strip()
        if not cleaned:
            return []
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive.")
        if overlap < 0 or overlap >= chunk_size:
            raise ValueError("overlap must be non-negative and smaller than chunk_size.")

        pieces = PolicyDocumentLoader._recursive_split_text(
            cleaned,
            separators=["\n\n", "\n", "。", "；", "，", " ", ""],
            chunk_size=chunk_size,
        )
        chunks: List[str] = []
        current = ""
        for piece in pieces:
            candidate = f"{current}{piece}" if not current else f"{current}{piece}"
            if len(candidate) <= chunk_size:
                current = candidate
            else:
                if current.strip():
                    chunks.append(current.strip())
                current = piece
        if current.strip():
            chunks.append(current.strip())

        documents: List[Document] = []
        for index, content in enumerate(chunks, 1):
            if overlap and documents:
                previous_tail = documents[-1].page_content[-overlap:]
                content = f"{previous_tail}\n{content}".strip()
            documents.append(
                Document(
                    page_content=content,
                    metadata={
                        "section_1": f"递归字符片段 {index}",
                        "section_type": "recursive_character",
                        "chunking_strategy": "recursive_character",
                    },
                )
            )
        return documents

    @staticmethod
    def _recursive_split_text(text: str, separators: List[str], chunk_size: int) -> List[str]:
        if len(text) <= chunk_size:
            return [text]
        separator = separators[0]
        if separator == "":
            return [text[index : index + chunk_size] for index in range(0, len(text), chunk_size)]

        pieces = text.split(separator)
        if len(pieces) == 1:
            return PolicyDocumentLoader._recursive_split_text(text, separators[1:], chunk_size)

        results: List[str] = []
        for index, piece in enumerate(pieces):
            if not piece:
                continue
            piece = piece + (separator if index < len(pieces) - 1 else "")
            if len(piece) <= chunk_size:
                results.append(piece)
            else:
                results.extend(PolicyDocumentLoader._recursive_split_text(piece, separators[1:], chunk_size))
        return results
