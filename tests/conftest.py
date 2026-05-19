import os
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Shared in-memory DB for app lifespan + tests
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["WEBHOOK_SECRET"] = "test-secret"
os.environ["AI_PROVIDER"] = "mock"
os.environ["NEWS_PROVIDER"] = "mock"
os.environ["EXECUTION_MODE"] = "paper"
os.environ["ENABLE_BROKER_EXECUTION"] = "false"

from backend.config import get_settings
from backend.database import Base, get_db
from backend.main import app

get_settings.cache_clear()

TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def _recent_et_iso() -> str:
    now = datetime.now(ZoneInfo("America/New_York"))
    # Use in-session time (10:15 ET) when outside trading windows for CI stability
    m = now.hour * 60 + now.minute
    if m < 9 * 60 + 35 or (11 * 60 + 30 <= m < 13 * 60 + 30) or m >= 15 * 60 + 30:
        return now.replace(hour=10, minute=15, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S%z")
    return now.strftime("%Y-%m-%dT%H:%M:%S%z")


@pytest.fixture
def recent_time():
    return _recent_et_iso()


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
