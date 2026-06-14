"""Project configuration defaults for the Enterprise Context Engine MVP."""

from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
SAMPLE_DOCS_DIR = DATA_DIR / "sample_docs"
RAW_DATA_DIR = DATA_DIR / "raw"
EVAL_DATA_DIR = DATA_DIR / "eval"


@dataclass(frozen=True)
class Settings:
    app_name: str = "Enterprise Context Engine"
    tagline: str = "Permission-aware context engineering for enterprise LLM applications."
    environment: str = "local"
    llm_mode: str = "mock"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    enable_reranking: bool = False
    default_top_k: int = 5
    max_context_chunks: int = 5
    target_chunk_words: int = 400
    chunk_overlap_words: int = 50


settings = Settings()
