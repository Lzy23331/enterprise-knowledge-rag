import json
import hashlib
import re
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

from .types import Document


FRONT_MATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
REQUIRED_SIDECAR_FIELDS = (
    "doc_id",
    "title",
    "department",
    "process_type",
    "risk_level",
    "owner",
    "system",
    "form_id",
    "approval_sla",
    "version",
    "effective_date",
    "source_type",
)


def parse_front_matter(text: str) -> Tuple[Dict[str, str], str]:
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


def stable_doc_id(relative_path: str) -> str:
    return hashlib.md5(relative_path.encode("utf-8")).hexdigest()


def normalize_dataset_layers(dataset_layers: Sequence[str] | str | None) -> set[str]:
    if not dataset_layers or dataset_layers == "all":
        return {"all"}
    if isinstance(dataset_layers, str):
        values = [dataset_layers]
    else:
        values = list(dataset_layers)
    normalized = {str(value).strip().lower() for value in values if str(value).strip()}
    return normalized or {"all"}


def layer_allowed(metadata: Dict[str, str], dataset_layers: set[str]) -> bool:
    if "all" in dataset_layers:
        return True
    return str(metadata.get("dataset_layer", "baseline")).lower() in dataset_layers


class MarkdownPolicyLoader:
    def __init__(self, data_path: Path, dataset_layers: Sequence[str] | str | None = None):
        self.data_path = Path(data_path)
        self.dataset_layers = normalize_dataset_layers(dataset_layers)

    def load(self) -> List[Document]:
        documents: List[Document] = []
        for path in sorted(self.data_path.rglob("*.md")):
            raw_text = path.read_text(encoding="utf-8")
            metadata, content = parse_front_matter(raw_text)
            relative_path = path.relative_to(self.data_path).as_posix()
            doc_id = metadata.get("doc_id") or stable_doc_id(relative_path)
            metadata.update(
                {
                    "doc_id": doc_id,
                    "source_path": str(path),
                    "source_file": relative_path,
                    "source_type": "markdown",
                    "dataset_layer": metadata.get("dataset_layer", "baseline"),
                    "loader": "MarkdownPolicyLoader",
                    "chunk_type": "parent",
                }
            )
            if layer_allowed(metadata, self.dataset_layers):
                documents.append(Document(page_content=content.strip(), metadata=metadata))
        return documents


class PDFPolicyLoader:
    def __init__(self, data_path: Path, mode: str = "pypdf", dataset_layers: Sequence[str] | str | None = None):
        self.data_path = Path(data_path)
        self.mode = mode
        self.dataset_layers = normalize_dataset_layers(dataset_layers)

    def load(self) -> List[Document]:
        documents: List[Document] = []
        if not self.data_path.exists():
            return documents

        for path in sorted(self.data_path.rglob("*.pdf")):
            loaded, actual_loader = self._load_pdf(path)
            documents.extend(self._merge_pages(path, loaded, actual_loader))
        return documents

    def _load_pdf(self, path: Path) -> Tuple[List[Document], str]:
        if self.mode == "unstructured":
            try:
                from langchain_community.document_loaders import UnstructuredPDFLoader

                return UnstructuredPDFLoader(str(path), mode="elements").load(), "UnstructuredPDFLoader"
            except Exception as exc:
                print(f"UnstructuredPDFLoader unavailable for {path.name}, falling back to PyPDFLoader: {exc}")

        try:
            from langchain_community.document_loaders import PyPDFLoader

            return PyPDFLoader(str(path)).load(), "PyPDFLoader"
        except Exception as exc:
            raise RuntimeError(
                "PDF loading requires `pypdf` and `langchain-community`. "
                "Install full dependencies with `pip install -r requirements-full.txt`."
            ) from exc

    def _merge_pages(self, path: Path, loaded_docs: List[Document], actual_loader: str) -> List[Document]:
        if not loaded_docs:
            return []

        first_text = loaded_docs[0].page_content or ""
        metadata, stripped_first = parse_front_matter(first_text)
        sidecar_metadata = self._load_sidecar_metadata(path)
        metadata.update(sidecar_metadata)
        relative_path = path.relative_to(self.data_path).as_posix()
        doc_id = metadata.get("doc_id") or stable_doc_id(relative_path)

        page_texts = []
        page_numbers = []
        raw_text_length = 0
        for index, doc in enumerate(loaded_docs, 1):
            text = doc.page_content or ""
            if index == 1 and metadata:
                text = stripped_first
            text = text.strip()
            raw_text_length += len(text)
            if text:
                page_texts.append(text)
            page = doc.metadata.get("page", index - 1)
            try:
                page_numbers.append(int(page) + 1)
            except Exception:
                page_numbers.append(index)

        merged_text = "\n\n".join(page_texts).strip()
        missing_required = [field for field in REQUIRED_SIDECAR_FIELDS if not metadata.get(field)]
        metadata.update(
            {
                "doc_id": doc_id,
                "title": metadata.get("title", path.stem),
                "dataset_layer": metadata.get("dataset_layer", "baseline"),
                "source_path": str(path),
                "source_file": relative_path,
                "source_type": "pdf",
                "loader": actual_loader,
                "page_numbers": ",".join(str(number) for number in sorted(set(page_numbers))),
                "page_count": str(len(loaded_docs)),
                "extracted_page_count": str(len(page_texts)),
                "text_length": str(len(merged_text)),
                "avg_chars_per_page": f"{(raw_text_length / max(len(loaded_docs), 1)):.1f}",
                "has_sidecar_metadata": str(bool(sidecar_metadata)).lower(),
                "missing_required_metadata": ",".join(missing_required),
                "extraction_quality": self._assess_extraction_quality(len(loaded_docs), len(page_texts), len(merged_text), missing_required),
                "chunk_type": "parent",
            }
        )
        if not layer_allowed(metadata, self.dataset_layers):
            return []
        return [Document(page_content=merged_text, metadata=metadata)]

    def _load_sidecar_metadata(self, path: Path) -> Dict[str, str]:
        for sidecar in (path.with_suffix(".metadata.json"), path.with_suffix(path.suffix + ".json")):
            if not sidecar.exists():
                continue
            payload = json.loads(sidecar.read_text(encoding="utf-8"))
            return {str(key): str(value) for key, value in payload.items()}
        return {}

    @staticmethod
    def _assess_extraction_quality(page_count: int, extracted_page_count: int, text_length: int, missing_required: List[str]) -> str:
        if page_count == 0 or extracted_page_count == 0 or text_length == 0:
            return "empty_text"
        if missing_required:
            return "metadata_incomplete"
        if extracted_page_count / max(page_count, 1) < 0.8:
            return "partial_text"
        if text_length / max(page_count, 1) < 250:
            return "low_text_density"
        return "ok"


class MultiFormatPolicyLoader:
    def __init__(
        self,
        markdown_path: Path,
        pdf_path: Path | None = None,
        pdf_mode: str = "pypdf",
        dataset_layers: Sequence[str] | str | None = None,
    ):
        self.markdown_path = Path(markdown_path)
        self.pdf_path = Path(pdf_path) if pdf_path else None
        self.pdf_mode = pdf_mode
        self.dataset_layers = dataset_layers

    def load(self) -> List[Document]:
        documents = MarkdownPolicyLoader(self.markdown_path, dataset_layers=self.dataset_layers).load()
        if self.pdf_path:
            documents.extend(PDFPolicyLoader(self.pdf_path, mode=self.pdf_mode, dataset_layers=self.dataset_layers).load())
        return documents
