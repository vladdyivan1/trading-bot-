from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.config import Settings
from backend.models import Base


@pytest.fixture()
def settings() -> Settings:
    return Settings(
        environment="test",
        webhook_secret="",
        enable_ai_filter=True,
        enable_news_filter=True,
        paper_trading=True,
        enable_broker_execution=False,
        database_url="sqlite:///:memory:",
    )


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    with Session() as session:
        yield session
