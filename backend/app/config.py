"""
Centralized application configuration.

All configuration is read from environment variables (optionally loaded from
a .env file). Nothing is hardcoded so the same codebase can run in dev,
CI, or production simply by changing environment variables.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present (no-op in prod where real env vars are injected)
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings:
    # --- General ---
    APP_NAME: str = "AI Candidate Screening System"
    ENV: str = os.getenv("ENV", "development")

    # --- Database ---
    # Defaults to a local SQLite file so the project runs with zero external
    # services. Set DATABASE_URL to a Postgres DSN in production, e.g.
    # postgresql+psycopg2://user:pass@host:5432/dbname
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'data' / 'app.db'}"
    )

    # --- Vector store (ChromaDB, persisted locally) ---
    VECTOR_STORE_DIR: str = os.getenv(
        "VECTOR_STORE_DIR", str(BASE_DIR / "data" / "vector_store")
    )

    # --- Knowledge base source documents ---
    KNOWLEDGE_BASE_DIR: str = os.getenv(
        "KNOWLEDGE_BASE_DIR", str(BASE_DIR / "data" / "knowledge_base")
    )

    # --- Embeddings ---
    # "hashing"            -> deterministic, dependency-light, works fully offline
    # "sentence-transformers" -> higher quality, requires the model to be
    #                            downloaded once (needs internet access)
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "hashing")
    EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "384"))
    SENTENCE_TRANSFORMER_MODEL: str = os.getenv(
        "SENTENCE_TRANSFORMER_MODEL", "all-MiniLM-L6-v2"
    )

    # --- LLM provider for question generation / extraction / summaries ---
    # "anthropic" | "openai" | "fallback" (rule-based, no API key required)
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "fallback")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # --- Chunking ---
    CHUNK_SIZE_TOKENS: int = int(os.getenv("CHUNK_SIZE_TOKENS", "400"))
    CHUNK_OVERLAP_TOKENS: int = int(os.getenv("CHUNK_OVERLAP_TOKENS", "60"))

    # --- Interview flow ---
    QUESTIONS_PER_SESSION: int = int(os.getenv("QUESTIONS_PER_SESSION", "6"))
    RETRIEVAL_TOP_K: int = int(os.getenv("RETRIEVAL_TOP_K", "4"))

    # --- CORS ---
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

    # --- Uploads ---
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", str(BASE_DIR / "data" / "uploads"))


settings = Settings()

# Ensure required directories exist at import time.
for path in [
    Path(settings.VECTOR_STORE_DIR),
    Path(settings.KNOWLEDGE_BASE_DIR),
    Path(settings.UPLOAD_DIR),
    BASE_DIR / "data",
]:
    path.mkdir(parents=True, exist_ok=True)
