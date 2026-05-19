"""Database engine and session management."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from backend.config import get_settings

settings = get_settings()
_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
_pool = None
if settings.database_url.rstrip("/") in ("sqlite:", "sqlite://"):
    from sqlalchemy.pool import StaticPool
    _pool = StaticPool
_engine_kw: dict = {"connect_args": _connect_args}
if _pool:
    _engine_kw["poolclass"] = _pool
engine = create_engine(settings.database_url, **_engine_kw)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from backend import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
