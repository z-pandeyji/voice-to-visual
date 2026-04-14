"""
test_api.py
===========
Integration tests for the FastAPI endpoints.
All AI models are mocked — these tests run without a GPU or Ollama.

Run:
    cd backend
    pytest tests/test_api.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from io import BytesIO
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from starlette.websockets import WebSocketDisconnect

pytestmark = pytest.mark.asyncio


def _fake_audio() -> BytesIO:
    """Minimal fake audio bytes to satisfy the upload field."""
    return BytesIO(b"RIFF" + b"\x00" * 40)


# ── Tests ──────────────────────────────────────────────────────────────────

async def test_generate_returns_202_with_job_id(async_client):
    """POST /generate must return HTTP 202 and a non-empty job_id string."""
    response = await async_client.post(
        "/generate",
        files={"audio": ("test.webm", _fake_audio(), "audio/webm")},
        data={"mode": "image"},
    )
    assert response.status_code == 202
    body = response.json()
    assert "job_id" in body
    assert isinstance(body["job_id"], str)
    assert len(body["job_id"]) > 0


async def test_generate_video_mode_returns_202(async_client):
    """mode=video must also be accepted and return 202."""
    response = await async_client.post(
        "/generate",
        files={"audio": ("test.webm", _fake_audio(), "audio/webm")},
        data={"mode": "video"},
    )
    assert response.status_code == 202
    assert "job_id" in response.json()


async def test_generate_returns_503_when_models_not_ready():
    """When models are still loading, POST /generate must return 503."""
    with patch("models.loader._models_ready", False), \
         patch("asyncio.create_task"):
        import importlib
        import main as main_module
        importlib.reload(main_module)
        async with AsyncClient(
            transport=ASGITransport(app=main_module.app),
            base_url="http://test",
        ) as c:
            response = await c.post(
                "/generate",
                files={"audio": ("test.webm", _fake_audio(), "audio/webm")},
                data={"mode": "image"},
            )
    assert response.status_code == 503
    assert "models not ready" in response.json()["detail"]


async def test_different_jobs_get_unique_ids(async_client):
    """Each POST /generate must return a unique job_id."""
    r1 = await async_client.post(
        "/generate",
        files={"audio": ("a.webm", _fake_audio(), "audio/webm")},
        data={"mode": "image"},
    )
    r2 = await async_client.post(
        "/generate",
        files={"audio": ("b.webm", _fake_audio(), "audio/webm")},
        data={"mode": "image"},
    )
    assert r1.json()["job_id"] != r2.json()["job_id"]


async def test_websocket_unknown_job_closes_with_4004():
    """
    Connecting to /ws/<unknown_id> must trigger a WebSocket close with code 4004.

    Starlette's TestClient raises WebSocketDisconnect when the server closes
    the connection before accept() — so the assertion is on exc.code.
    """
    with patch("models.loader._models_ready", True), \
         patch("asyncio.create_task"):
        import importlib
        import main as main_module
        importlib.reload(main_module)
        from starlette.testclient import TestClient
        sync_client = TestClient(main_module.app, raise_server_exceptions=False)
        try:
            with sync_client.websocket_connect("/ws/nonexistent-job-id") as ws:
                ws.receive()  # Should not reach here
                pytest.fail("Expected WebSocketDisconnect was not raised")
        except WebSocketDisconnect as exc:
            # Starlette raises this when server closes before accept()
            assert exc.code == 4004, f"Expected close code 4004, got {exc.code}"
