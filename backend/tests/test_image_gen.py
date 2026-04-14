"""
test_image_gen.py
=================
Quality tests for Stable Diffusion image generation (pipeline/image_gen.py).

These tests verify:
  1. The generated file is a valid 512×512 PNG.
  2. Quality controls (num_inference_steps, guidance_scale, negative_prompt) work.
  3. Higher inference steps produce more detailed output.
  4. All business use-case prompts successfully generate images.

NOTE: These tests run Stable Diffusion locally — they are slow (minutes on CPU).
      Run on GPU for faster iteration.

Run:
    cd backend
    pytest tests/test_image_gen.py -v -s
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from PIL import Image
from pipeline.image_gen import generate_image


class TestImageGeneration:

    @pytest.mark.slow
    def test_generates_valid_png_file(self, outputs_dir):
        """
        Baseline sanity check:
          - output file is created at the given path
          - it is a valid, non-trivially-small PNG
          - dimensions are 512×512 (SD v1.5 default)
        """
        path = os.path.join(outputs_dir, "test_output.png")
        generate_image("a red apple on a white table", path)

        assert os.path.exists(path), "Output file was not created."
        assert os.path.getsize(path) > 10_000, (
            f"Output file is suspiciously small ({os.path.getsize(path)} bytes). "
            "Expected a real image, not a placeholder."
        )

        img = Image.open(path)
        assert img.format == "PNG", f"Expected PNG, got {img.format}"
        assert img.size == (512, 512), f"Expected 512×512, got {img.size}"

    @pytest.mark.slow
    def test_fast_vs_quality_steps_file_size(self, outputs_dir):
        """
        num_inference_steps controls output quality.
        More steps → more texture/detail → larger PNG file size.
        Demonstrates the quality parameter is actually applied.
        """
        prompt = "a cinematic portrait of a woman, golden hour lighting, bokeh background"

        fast_path = os.path.join(outputs_dir, "steps_10.png")
        quality_path = os.path.join(outputs_dir, "steps_50.png")

        generate_image(prompt, fast_path, num_inference_steps=10)
        generate_image(prompt, quality_path, num_inference_steps=50)

        fast_size = os.path.getsize(fast_path)
        quality_size = os.path.getsize(quality_path)

        print(f"\nFile sizes — 10 steps: {fast_size:,}B | 50 steps: {quality_size:,}B")
        assert quality_size > fast_size, (
            f"50-step image ({quality_size}B) should be larger/more detailed than "
            f"10-step image ({fast_size}B)."
        )

    @pytest.mark.slow
    def test_default_steps_produces_valid_image(self, outputs_dir):
        """
        Default num_inference_steps=20 is the production default used by the API.
        Ensure it produces a valid image without explicit parameter passing.
        """
        path = os.path.join(outputs_dir, "default_steps.png")
        generate_image("a mountain lake at dawn, reflection in water", path)

        img = Image.open(path)
        assert img.size == (512, 512)

    @pytest.mark.slow
    def test_negative_prompt_runs_without_error(self, outputs_dir):
        """
        Negative prompt is passed to the diffusion pipeline.
        Verify it is accepted and generation completes successfully.
        """
        path = os.path.join(outputs_dir, "negative_prompt.png")
        generate_image(
            "a product photo of a perfume bottle on white marble",
            path,
            num_inference_steps=20,
            guidance_scale=7.5,
            negative_prompt="blurry, low quality, deformed, watermark, text, bad anatomy, duplicate",
        )
        assert os.path.exists(path)
        img = Image.open(path)
        assert img.size == (512, 512)

    @pytest.mark.slow
    def test_high_guidance_scale_runs_without_error(self, outputs_dir):
        """
        guidance_scale=12 makes the model adhere more strictly to the prompt.
        Verify this setting is accepted and does not crash.
        """
        path = os.path.join(outputs_dir, "high_cfg.png")
        generate_image(
            "a minimalist geometric logo, white background, clean lines",
            path,
            guidance_scale=12.0,
            num_inference_steps=20,
        )
        img = Image.open(path)
        assert img.size == (512, 512)

    @pytest.mark.slow
    def test_low_guidance_scale_runs_without_error(self, outputs_dir):
        """
        guidance_scale=3 gives the model more creative freedom.
        Verify this setting is accepted and does not crash.
        """
        path = os.path.join(outputs_dir, "low_cfg.png")
        generate_image(
            "abstract colorful painting",
            path,
            guidance_scale=3.0,
            num_inference_steps=20,
        )
        img = Image.open(path)
        assert img.size == (512, 512)

    @pytest.mark.parametrize("use_case,prompt", [
        (
            "product_mockup",
            "wireless headphones, studio lighting, white background, "
            "product photography, sharp focus, high detail",
        ),
        (
            "social_media_post",
            "morning coffee flat lay, overhead shot, warm tones, "
            "aesthetic, soft bokeh, natural light, cozy",
        ),
        (
            "ad_creative",
            "professional woman at laptop in modern office, cinematic lighting, "
            "natural light through window, sharp, photorealistic",
        ),
        (
            "brand_concept",
            "minimal tech startup logo, blue and white, geometric shapes, "
            "clean vector style, modern, white background",
        ),
        (
            "real_estate",
            "modern living room, floor-to-ceiling windows, natural sunlight, "
            "photorealistic interior, warm tones, cozy, high detail",
        ),
    ])
    @pytest.mark.slow
    def test_business_use_case_image_generation(self, outputs_dir, use_case, prompt):
        """
        Every business use case must produce a valid 512×512 PNG.
        Prints the output path so images can be visually inspected after the run.
        """
        path = os.path.join(outputs_dir, f"{use_case}.png")
        generate_image(prompt, path, num_inference_steps=20)

        assert os.path.exists(path), f"[{use_case}] No output file created."
        img = Image.open(path)
        assert img.size == (512, 512), f"[{use_case}] Unexpected size: {img.size}"
        print(f"\n[{use_case}] ✓ {path}")

    def test_uses_provided_pipeline_without_loading(self, outputs_dir):
        """When a preloaded pipeline is passed, from_pretrained must NOT be called."""
        from PIL import Image as PILImage
        from unittest.mock import MagicMock, patch

        mock_image = PILImage.new("RGB", (512, 512), color=(100, 150, 200))
        mock_pipeline = MagicMock()
        mock_pipeline.return_value.images = [mock_image]

        path = os.path.join(outputs_dir, "preloaded.png")

        with patch("diffusers.StableDiffusionPipeline.from_pretrained") as mock_load:
            generate_image("a sunset", path, pipeline=mock_pipeline)
            mock_load.assert_not_called()

        assert os.path.exists(path)
        assert PILImage.open(path).size == (512, 512)

    def test_pipeline_called_with_correct_prompt(self, outputs_dir):
        """Verify the exact prompt is passed to the pipeline as first positional arg."""
        from PIL import Image as PILImage
        from unittest.mock import MagicMock

        mock_image = PILImage.new("RGB", (512, 512))
        mock_pipeline = MagicMock()
        mock_pipeline.return_value.images = [mock_image]

        path = os.path.join(outputs_dir, "prompt_check.png")
        generate_image("a red apple", path, pipeline=mock_pipeline)

        call_args = mock_pipeline.call_args
        assert call_args[0][0] == "a red apple"
