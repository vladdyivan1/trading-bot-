import os
from pathlib import Path
Path('data').mkdir(exist_ok=True)

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./data/test_scalper.db")
os.environ.setdefault("ENABLE_AI_FILTER", "true")
os.environ.setdefault("ENABLE_NEWS_FILTER", "true")
os.environ.setdefault("EXECUTION_MODE", "paper")
os.environ.setdefault("KILL_SWITCH", "false")


@pytest.fixture
async def client():
    from backend.main import app
    from backend.database import init_db

    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
