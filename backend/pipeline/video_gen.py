import os
import torch
import numpy as np
import imageio
from typing import Optional
from diffusers import DiffusionPipeline
from PIL import Image as PILImage


def generate_video(
    prompt: str,
    output_path: str,
    pipeline: Optional[DiffusionPipeline] = None,
    num_inference_steps: int = 25,
    num_frames: int = 16,
) -> str:
    print(f"[video_gen] Generating video for: '{prompt[:60]}'")
    print(f"[video_gen] steps={num_inference_steps}, frames={num_frames}")

    if pipeline is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        print(f"[video_gen] Loading damo-vilab/text-to-video-ms-1.7b on {device}...")
        pipeline = DiffusionPipeline.from_pretrained(
            "damo-vilab/text-to-video-ms-1.7b", torch_dtype=dtype
        ).to(device)
        pipeline.enable_attention_slicing()

    # CLIP tokenizer hard-limit is 77 tokens (incl. BOS/EOS).
    # Truncate here so the pipeline never silently drops tokens.
    if hasattr(pipeline, "tokenizer") and pipeline.tokenizer is not None:
        tok = pipeline.tokenizer
        encoded = tok(prompt, truncation=True, max_length=77, return_tensors="pt")
        truncated = tok.decode(encoded["input_ids"][0], skip_special_tokens=True)
        if truncated != prompt:
            print(f"[video_gen] Prompt truncated from {len(tok.encode(prompt))} → 77 tokens")
            prompt = truncated

    result = pipeline(
        prompt,
        num_inference_steps=num_inference_steps,
        num_frames=num_frames,
    )

    frames = result.frames[0]  # first batch item: list of PIL images or numpy arrays

    dir_name = os.path.dirname(output_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    with imageio.get_writer(output_path, fps=8) as writer:
        for frame in frames:
            if isinstance(frame, PILImage.Image):
                writer.append_data(np.array(frame))
            else:
                writer.append_data(frame)

    print(f"[video_gen] Saved {len(frames)} frames to {output_path}")
    return output_path


if __name__ == "__main__":
    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "outputs"))
    os.makedirs(output_dir, exist_ok=True)
    generate_video(
        "a cinematic timelapse of a sunset over the ocean, smooth motion",
        os.path.join(output_dir, "test_video.mp4"),
    )
