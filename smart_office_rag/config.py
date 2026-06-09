from dataclasses import dataclass
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("HF_HOME", str(PROJECT_ROOT / ".cache" / "huggingface"))


@dataclass
class RAGConfig:
    data_path: Path = PROJECT_ROOT / "data" / "policies"
    pdf_data_path: Path = PROJECT_ROOT / "data" / "policies_pdf"
    pdf_loader_mode: str = os.getenv("SMARTOFFICE_PDF_LOADER", "pypdf")
    index_path: Path = PROJECT_ROOT / "vector_index"
    embedding_model: str = os.getenv("SMARTOFFICE_EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
    top_k: int = 5
    llm_model: str = "deepseek-chat"
    llm_base_url: str = "https://api.deepseek.com"
    temperature: float = 0.1
    max_tokens: int = 1600
    use_vector_index: bool = os.getenv("SMARTOFFICE_USE_VECTOR", "1") == "1"


DEFAULT_CONFIG = RAGConfig()
