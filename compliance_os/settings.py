"""Application settings — loaded from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Load .env from project root
_PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


class Settings(BaseSettings):
    """Application configuration."""

    # Paths
    project_root: Path = _PROJECT_ROOT
    data_dir: Path = Field(default_factory=lambda: _PROJECT_ROOT / "user_data")
    chroma_dir: Path = Field(default_factory=lambda: _PROJECT_ROOT / "chroma_db")

    # OpenAI
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    llm_model: str = "gpt-4o-mini"

    # Indexer
    chunk_size: int = 1024
    chunk_overlap: int = 128
    max_file_size: int = 5 * 1024 * 1024  # 5MB
    collection_name: str = "compliance_docs"

    # Query
    default_top_k: int = 5

    # File extensions to index
    index_extensions: set[str] = {".txt", ".md", ".csv", ".pdf", ".docx"}

    # Patterns to skip
    skip_patterns: set[str] = {
        ".DS_Store", "__pycache__", "chroma_db", ".git",
        "node_modules", ".env", "secrets",
    }

    model_config = {"env_prefix": "COS_", "extra": "ignore"}


settings = Settings()
