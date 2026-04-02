"""Shared test fixtures."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from compliance_os.web.app import app
from compliance_os.web.models import database


@pytest.fixture
def client(tmp_path):
    """Create test client with temporary database."""
    db_path = str(tmp_path / "test.db")
    database._engine = None
    database._SessionLocal = None
    engine = database.create_engine_and_tables(db_path)
    database._engine = engine
    database._SessionLocal = sessionmaker(bind=engine)
    yield TestClient(app)
    database._engine = None
    database._SessionLocal = None


@pytest.fixture
def case_id(client):
    """Create a test case and return its ID."""
    resp = client.post("/api/cases", json={"workflow_type": "tax"})
    return resp.json()["id"]
