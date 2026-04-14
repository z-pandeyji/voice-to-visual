import torch
from typing import Optional, Callable
from diffusers import StableDiffusionPipeline
import os


_DEFAULT_NEGATIVE_PROMPT = (
    "blurry, out of focus, low quality, worst quality, low resolution, "
    "deformed, distorted, disfigured, bad anatomy, bad hands, extra fingers, "
    "missing fingers, extra limbs, mutated, mutation, ugly, duplicate, "
    "morbid, gross, watermark, signature, text, username, logo, "
    "oversaturated, overexposed, underexposed, washed out, noisy, grainy, "
    "jpeg artifacts, pixelated, cropped, cut off"
)


def generate_image(
    prompt: str,
    output_path: str,
    pipeline: Optional[StableDiffusionPipeline] = None,
    num_inference_steps: int = 30,
    guidance_scale: float = 8.5,
    negative_prompt: str = _DEFAULT_NEGATIVE_PROMPT,
    step_callback: Optional[Callable[[int, int], None]] = None,
) -> str:
    print(f"[image_gen] Generating image for: '{prompt[:60]}'")
    print(f"[image_gen] steps={num_inference_steps}, guidance={guidance_scale}")

    if pipeline is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        print(f"[image_gen] Loading SD v1.5 on {device} (no preloaded pipeline)...")
        pipeline = StableDiffusionPipeline.from_pretrained(
            "runwayml/stable-diffusion-v1-5", torch_dtype=dtype
        ).to(device)
        pipeline.enable_attention_slicing()

    # Build a diffusers-compatible step callback so the worker can emit
    # live progress events without blocking the asyncio event loop.
    sd_callback = None
    if step_callback is not None:
        def sd_callback(step: int, timestep: int, latents):  # type: ignore[override]
            step_callback(step + 1, num_inference_steps)

    image = pipeline(
        prompt,
        num_inference_steps=num_inference_steps,
        guidance_scale=guidance_scale,
        negative_prompt=negative_prompt,
        callback=sd_callback,
        callback_steps=1,
    ).images[0]

    dir_name = os.path.dirname(output_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    image.save(output_path)
    print(f"[image_gen] Saved to {output_path}")
    return output_path


if __name__ == "__main__":
    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "outputs"))
    os.makedirs(output_dir, exist_ok=True)
    generate_image(
        "a cinematic photo of an astronaut riding a horse on mars, detailed, 8k",
        os.path.join(output_dir, "test_image.png"),
    )
