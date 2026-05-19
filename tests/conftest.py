from __future__ import annotations

import pytest

from backend.models import Base, SessionLocal, engine


@pytest.fixture(autouse=True)
def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def db_session():
    with SessionLocal() as session:
        yield session
