import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
from unittest.mock import MagicMock, patch
from pipeline.stt import transcribe_audio


def test_transcribe_uses_provided_model(tmp_path):
    """When a preloaded model is passed, whisper.load_model must NOT be called."""
    mock_model = MagicMock()
    mock_model.transcribe.return_value = {"text": "a dog on a hill"}
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake audio bytes")

    with patch("whisper.load_model") as mock_load:
        result = transcribe_audio(str(audio_file), model=mock_model)
        mock_load.assert_not_called()

    mock_model.transcribe.assert_called_once_with(str(audio_file))
    assert result == "a dog on a hill"


def test_transcribe_strips_whitespace(tmp_path):
    """Returned transcript must have leading/trailing whitespace stripped."""
    mock_model = MagicMock()
    mock_model.transcribe.return_value = {"text": "   hello world   "}
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake")

    result = transcribe_audio(str(audio_file), model=mock_model)
    assert result == "hello world"


def test_transcribe_loads_model_when_none(tmp_path):
    """When model=None, whisper.load_model must be called exactly once."""
    mock_model = MagicMock()
    mock_model.transcribe.return_value = {"text": "auto loaded result"}
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake")

    with patch("whisper.load_model", return_value=mock_model) as mock_load:
        result = transcribe_audio(str(audio_file), model=None)
        mock_load.assert_called_once()

    assert result == "auto loaded result"
