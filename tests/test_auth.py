"""Tests for API key auth."""

import os

import pytest

pytest.importorskip("temporalio")
from fastapi.testclient import TestClient

from apps.api.main import app


def test_healthz_no_auth_required():
    client = TestClient(app)
    resp = client.get("/healthz")
    assert resp.status_code == 200


def test_write_endpoint_rejects_invalid_key():
    os.environ["INFRA_API_KEY"] = "secret123"
    try:
        from packages.core.config import get_settings
        get_settings.cache_clear()
        client = TestClient(app)
        resp = client.post(
            "/v1/changes/start",
            json={"change_id": "CHG-001", "scenario": "CHG-001_A"},
            headers={"X-INFRA-KEY": "wrong"},
        )
        assert resp.status_code == 401
    finally:
        os.environ.pop("INFRA_API_KEY", None)
        from packages.core.config import get_settings
        get_settings.cache_clear()
