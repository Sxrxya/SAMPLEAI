import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

TEST_ROOT = Path(tempfile.mkdtemp(prefix="tandem-backend-tests-"))
os.environ["ACCESS_TOKEN_SECRET"] = "test-only-secret-key-012345678901234567890123"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_ROOT / 'test.db'}"
os.environ["STORAGE_ROOT"] = str(TEST_ROOT / "storage")
os.environ["INFERENCE_ENABLED"] = "false"
os.environ["ENVIRONMENT"] = "testing"

from app.core.config import get_settings

get_settings.cache_clear()

from app.core.db import Base, engine
from app.main import app
from app.services.search import initialize_search_index


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    initialize_search_index()
    yield
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM resume_search"))
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
