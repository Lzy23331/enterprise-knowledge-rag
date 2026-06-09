import hashlib
import re
from pathlib import Path
from typing import Dict, List, Tuple

from .types import Document


FRONT_MATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
HEADER_PATTERN = re.compile(r"^(#{1,3})\s+(.+?)\s*$", re.MULTILINE)


def _parse_front_matter(text: str) -> Tuple[Dict[str, str], str]:
    match = FRONT_MATTER_PATTERN.match(text)
    if not match:
        return {}, text

    metadata: Dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"')
    return metadata, text[match.end():]


class PolicyDocumentLoader:
    def __init__(
        self,
        data_path: Path,
        chunk_strategy: str = "markdown_headers",
        fixed_chunk_size: int = 900,
        fixed_chunk_overlap: int = 120,
    ):
        self.data_path = Path(data_path)
        self.chunk_strategy = chunk_strategy
        self.fixed_chunk_size = fixed_chunk_size
        self.fixed_chunk_overlap = fixed_chunk_overlap

    def load_parent_documents(self) -> List[Document]:
        if not self.data_path.exists():
            raise FileNotFoundError(f"Policy data path not found: {self.data_path}")

        documents: List[Document] = []
        for path in sorted(self.data_path.rglob("*.md")):
            raw_text = path.read_text(encoding="utf-8")
            metadata, content = _parse_front_matter(raw_text)
            relative_path = path.relative_to(self.data_path).as_posix()
            doc_id = metadata.get("doc_id") or hashlib.md5(relative_path.encode("utf-8")).hexdigest()
            metadata.update(
                {
                    "doc_id": doc_id,
                    "source_path": str(path),
                    "source_file": relative_path,
                    "chunk_type": "parent",
                }
            )
            documents.append(Document(page_content=content.strip(), metadata=metadata))
        return documents

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
            elif self.chunk_strategy == "markdown_headers":
                split_docs = self._split_markdown_by_headers(parent.page_content)
            else:
                raise ValueError(f"Unsupported chunk strategy: {self.chunk_strategy}")

            for index, chunk in enumerate(split_docs):
                section = (
                    chunk.metadata.get("section_3")
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
