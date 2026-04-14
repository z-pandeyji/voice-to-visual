import whisper
import os
import torch
from typing import Optional


def transcribe_audio(file_path: str, model: Optional[whisper.Whisper] = None) -> str:
    print(f"[stt] Transcribing audio from: {file_path}")

    if model is None:
        if torch.cuda.is_available():
            device = "cuda"
        elif torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"
        print(f"[stt] Loading Whisper base on {device} (no preloaded model provided)...")
        model = whisper.load_model("base", device=device)

    result = model.transcribe(
        file_path,
        fp16=torch.cuda.is_available(),   # avoid FP16 errors on CPU
        language=None,                    # auto-detect language
        verbose=False,
    )
    transcript = result["text"].strip()
    print(f"[stt] Transcript: '{transcript}'")
    return transcript


if __name__ == "__main__":
    print("Standalone: provide an audio file path as argument.")
