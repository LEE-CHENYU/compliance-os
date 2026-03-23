"""SQLAlchemy database setup for compliance copilot."""

from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATA_DIR = Path(__file__).parents[3] / "data"


class Base(DeclarativeBase):
    pass


def create_engine_and_tables(db_path: str | None = None) -> Engine:
    """Create SQLite engine and all tables."""
    if db_path is None:
        DATA_DIR.mkdir(exist_ok=True)
        db_path = str(DATA_DIR / "copilot.db")
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    from compliance_os.web.models.tables import CaseRow, DiscoveryAnswerRow, ChatMessageRow, DocumentRow  # noqa: F401
    Base.metadata.create_all(engine)
    return engine


_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine_and_tables()
    return _engine


def get_session():
    """Yield a SQLAlchemy session (for FastAPI Depends)."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()
