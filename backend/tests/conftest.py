import pytest
import json
import os
import sys
from unittest.mock import MagicMock, patch
from PIL import Image as PILImage

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

BENCHMARK_PATH = os.path.join(os.path.dirname(__file__), "prompts", "benchmark_prompts.json")


# ──────────────────────────────────────────
# Original fixtures (unchanged)
# ──────────────────────────────────────────

@pytest.fixture
def benchmark_prompts():
    with open(BENCHMARK_PATH) as f:
        return json.load(f)


@pytest.fixture
def outputs_dir(tmp_path):
    """Temporary output directory — cleaned up after each test."""
    return str(tmp_path)


@pytest.fixture
def mock_ollama_unavailable(monkeypatch):
    """Simulate Ollama being unreachable — forces fallback path in enhancer."""
    import requests

    def raise_connection_error(*args, **kwargs):
        raise requests.exceptions.ConnectionError("Ollama not running")

    monkeypatch.setattr(requests, "post", raise_connection_error)


# ──────────────────────────────────────────
# Mock model fixtures (fast, no GPU)
# ──────────────────────────────────────────

@pytest.fixture
def mock_whisper_model():
    """A MagicMock that behaves like a loaded Whisper model."""
    model = MagicMock()
    model.transcribe.return_value = {"text": "a beautiful sunset over the ocean"}
    return model


@pytest.fixture
def mock_sd_pipeline():
    """A MagicMock that behaves like a loaded StableDiffusionPipeline."""
    mock_image = PILImage.new("RGB", (512, 512), color=(100, 100, 200))
    pipeline = MagicMock()
    pipeline.return_value.images = [mock_image]
    return pipeline


@pytest.fixture
def mock_video_pipeline():
    """A MagicMock that behaves like a loaded ModelScope DiffusionPipeline."""
    frames = [PILImage.new("RGB", (256, 256), color=(i * 10, 50, 100)) for i in range(16)]
    pipeline = MagicMock()
    pipeline.return_value.frames = [frames]
    return pipeline


# ──────────────────────────────────────────
# Async API test client (requires main.py)
# ──────────────────────────────────────────

@pytest.fixture
async def async_client(mock_whisper_model, mock_sd_pipeline, mock_video_pipeline):
    """
    AsyncClient with all models patched — no GPU required.
    Patches models.loader singletons and suppresses worker startup.
    """
    from httpx import AsyncClient, ASGITransport

    with patch("models.loader._whisper_model", mock_whisper_model), \
         patch("models.loader._sd_pipeline", mock_sd_pipeline), \
         patch("models.loader._video_pipeline", mock_video_pipeline), \
         patch("models.loader._models_ready", True), \
         patch("asyncio.create_task"):
        import importlib
        import main as main_module
        importlib.reload(main_module)

        async with AsyncClient(
            transport=ASGITransport(app=main_module.app),
            base_url="http://test",
        ) as client:
            yield client
