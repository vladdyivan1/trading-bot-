"""Database engine and session helpers."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

from config.settings import get_settings

Base = declarative_base()


def get_engine():
    settings = get_settings()
    return create_engine(settings.database_url, future=True, echo=False)


SessionLocal = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
)


def init_db() -> None:
    from database import models  # noqa: F401

    Base.metadata.create_all(bind=get_engine())
