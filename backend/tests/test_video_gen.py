import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
from unittest.mock import MagicMock, patch
from PIL import Image as PILImage
from pipeline.video_gen import generate_video


def _make_mock_pipeline(num_frames: int = 16):
    """Returns a mock DiffusionPipeline that returns PIL image frames."""
    frames = [PILImage.new("RGB", (256, 256), color=(i * 15, 50, 100)) for i in range(num_frames)]
    mock_pipe = MagicMock()
    mock_pipe.return_value.frames = [frames]
    return mock_pipe


def test_generate_video_creates_mp4(tmp_path):
    """A .mp4 file must exist at output_path after successful generation."""
    mock_pipe = _make_mock_pipeline()
    output_path = str(tmp_path / "output.mp4")

    result = generate_video("a sunset timelapse", output_path, pipeline=mock_pipe)

    assert os.path.exists(output_path), "No .mp4 file created"
    assert result == output_path


def test_generate_video_file_is_not_empty(tmp_path):
    """The .mp4 file must not be a text placeholder — must have real bytes."""
    mock_pipe = _make_mock_pipeline()
    output_path = str(tmp_path / "output.mp4")

    generate_video("ocean waves", output_path, pipeline=mock_pipe)

    assert os.path.getsize(output_path) > 100, "Output file is too small to be a real video"


def test_generate_video_calls_pipeline_with_prompt(tmp_path):
    """The prompt must be passed as the first positional arg to the pipeline."""
    mock_pipe = _make_mock_pipeline()
    output_path = str(tmp_path / "test.mp4")

    generate_video("a dog running in a field", output_path, pipeline=mock_pipe)

    mock_pipe.assert_called_once()
    call_args = mock_pipe.call_args
    assert call_args[0][0] == "a dog running in a field"


def test_generate_video_loads_pipeline_when_none(tmp_path):
    """When pipeline=None, DiffusionPipeline.from_pretrained must be called."""
    frames = [PILImage.new("RGB", (256, 256)) for _ in range(4)]
    mock_pipe = MagicMock()
    mock_pipe.return_value.frames = [frames]
    mock_pipe.to.return_value = mock_pipe
    mock_pipe.enable_attention_slicing.return_value = None

    with patch("diffusers.DiffusionPipeline.from_pretrained", return_value=mock_pipe) as mock_load:
        output_path = str(tmp_path / "auto_load.mp4")
        generate_video("a test prompt", output_path, pipeline=None)
        mock_load.assert_called_once()
