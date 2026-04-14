import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
from unittest.mock import MagicMock, patch
import importlib


def test_models_not_ready_before_load():
    import models.loader as loader
    importlib.reload(loader)
    assert loader.models_ready() is False


def test_load_all_models_sets_ready_flag():
    import models.loader as loader
    importlib.reload(loader)

    mock_whisper = MagicMock()
    mock_sd = MagicMock()
    mock_sd.to.return_value = mock_sd
    mock_video = MagicMock()
    mock_video.to.return_value = mock_video

    with patch("whisper.load_model", return_value=mock_whisper), \
         patch("diffusers.StableDiffusionPipeline.from_pretrained", return_value=mock_sd), \
         patch("diffusers.DiffusionPipeline.from_pretrained", return_value=mock_video):
        loader.load_all_models()

    assert loader.models_ready() is True


def test_getters_return_loaded_models():
    import models.loader as loader
    importlib.reload(loader)

    mock_whisper = MagicMock()
    mock_sd = MagicMock()
    mock_sd.to.return_value = mock_sd
    mock_video = MagicMock()
    mock_video.to.return_value = mock_video

    with patch("whisper.load_model", return_value=mock_whisper), \
         patch("diffusers.StableDiffusionPipeline.from_pretrained", return_value=mock_sd), \
         patch("diffusers.DiffusionPipeline.from_pretrained", return_value=mock_video):
        loader.load_all_models()

    assert loader.get_whisper_model() is mock_whisper
    assert loader.get_sd_pipeline() is mock_sd
    assert loader.get_video_pipeline() is mock_video
