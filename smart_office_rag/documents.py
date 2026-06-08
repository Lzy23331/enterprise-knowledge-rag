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
    def __init__(self, data_path: Path):
        self.data_path = Path(data_path)

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
            split_docs = self._split_markdown_by_headers(parent.page_content)

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
