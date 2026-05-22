"""Application settings — loaded from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Load .env from project root
_PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


def _persistent_data_dir() -> Path:
    """The base for files that must survive container restarts.

    Honors `DATA_DIR` (set by Fly to `/data`, the mounted volume) so
    the diligence SQLite DB and persona-output YAMLs persist across
    deploys. Falls back to `<repo>/data` for local development.
    """
    return Path(os.environ.get("DATA_DIR", str(_PROJECT_ROOT / "data")))


def _user_state_dir() -> Path:
    """Writable per-user state dir for the MCP server's local artifacts.

    Required because the DXT/uv install lands compliance_os in a
    read-only cache directory, so the legacy `<package>/chroma_db`
    default fails with "unable to open database file". Resolution
    order:
      1. GUARDIAN_HOME — explicit override
      2. DATA_DIR     — honored on Fly (mounted volume)
      3. ~/.guardian  — user-writable default everywhere else
    """
    explicit = os.environ.get("GUARDIAN_HOME")
    if explicit:
        return Path(explicit)
    if "DATA_DIR" in os.environ:
        return Path(os.environ["DATA_DIR"])
    return Path.home() / ".guardian"


class Settings(BaseSettings):
    """Application configuration."""

    # Paths
    project_root: Path = _PROJECT_ROOT
    data_dir: Path = Field(default_factory=lambda: _user_state_dir() / "uploads", alias="GUARDIAN_DATA_DIR")
    chroma_dir: Path = Field(default_factory=lambda: _user_state_dir() / "chroma_db", alias="GUARDIAN_CHROMA_DIR")
    diligence_db_path: Path = Field(
        default_factory=lambda: _persistent_data_dir() / "diligence.db"
    )
    professional_search_output_dir: Path = Field(
        default_factory=lambda: _persistent_data_dir() / "output" / "professional_search"
    )

    # OpenAI
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    llm_model: str = "gpt-4o-mini"

    # Local embedding fallback — used when OPENAI_API_KEY is not set, OR when
    # GUARDIAN_EMBEDDING_PROVIDER=local is forced. HuggingFace model id; first
    # use downloads weights into ~/.cache/huggingface (~100-500MB depending on
    # choice). Default is set by the embedding bakeoff in tests/eval.
    embedding_provider: str = Field(default="auto", alias="GUARDIAN_EMBEDDING_PROVIDER")
    local_embedding_model: str = Field(
        default="BAAI/bge-small-en-v1.5",
        alias="GUARDIAN_LOCAL_EMBEDDING_MODEL",
    )

    # Stripe (paywall on professional-search reports)
    stripe_secret_key: str = Field(default="", alias="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str = Field(default="", alias="STRIPE_WEBHOOK_SECRET")
    stripe_publishable_key: str = Field(default="", alias="STRIPE_PUBLISHABLE_KEY")
    # Price in cents — keep as int to avoid float math; Stripe wants integer cents.
    stripe_report_price_cents: int = Field(default=1500, alias="STRIPE_REPORT_PRICE_CENTS")
    # Recurring price ID for Guardian Pro ($20/mo). Created in the Stripe
    # Dashboard once; we never construct prices on the fly. Empty string
    # means subscriptions endpoints will 503 — same pattern as the other
    # Stripe knobs above.
    stripe_pro_price_id: str = Field(default="", alias="STRIPE_PRO_PRICE_ID")
    # Where Stripe redirects after success/cancel; falls back to FRONTEND_URL.
    public_app_url: str = Field(default="https://guardian-compliance.fly.dev", alias="FRONTEND_URL")

    # Anthropic (professional search runner)
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    # Sonnet 4.6 is fast enough to finish a 3-persona fan-out in ~5 min
    # end-to-end; web research isn't intelligence-bottlenecked, so Opus's
    # extra reasoning doesn't pay back the latency cost.
    search_model: str = "claude-sonnet-4-6"
    # Research-style fan-out doesn't benefit much from deep reasoning —
    # quality comes from the web_search results, not from thinking between
    # searches. `low` keeps per-persona wall-clock under ~3 min.
    search_effort: str = "low"  # low | medium | high | xhigh | max

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
