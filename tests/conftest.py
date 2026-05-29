from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.config import reset_settings_cache


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SELLEROPS_DB_PATH", str(tmp_path / "sellerops-test.db"))
    reset_settings_cache()

    from app.api.db import init_db
    from app.api.main import app

    init_db()
    with TestClient(app) as test_client:
        yield test_client

    reset_settings_cache()

