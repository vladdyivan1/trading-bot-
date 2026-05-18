"""Database engine and session management."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from config.settings import get_settings
from database.models import Base


def get_engine():
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return create_engine(settings.database_url, echo=False)


def init_db() -> None:
    """Create all tables."""
    engine = get_engine()
    Base.metadata.create_all(engine)


SessionLocal = sessionmaker(autocommit=False, autoflush=False)


def get_session_factory():
    engine = get_engine()
    SessionLocal.configure(bind=engine)
    return SessionLocal


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
