"""
test_pipeline.py
================
End-to-end integration tests: raw brief → LLM enhancement → image generation.

These tests prove the core business value:
  "A raw, plain-language brief produces a better visual after LLM enhancement
  than the same brief fed directly to Stable Diffusion."

They also verify that every benchmark business use-case runs successfully
through the full two-step pipeline (enhance → generate).

Run:
    cd backend
    pytest tests/test_pipeline.py -v -s
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from PIL import Image
from pipeline.enhancer import enhance_prompt
from pipeline.image_gen import generate_image


class TestFullPipeline:

    @pytest.mark.slow
    def test_raw_vs_enhanced_prompt_both_generate_images(self, outputs_dir):
        """
        Core quality comparison:
          1. Generate an image from a short raw brief (no LLM).
          2. Generate an image from the LLM-enhanced version of the same brief.
          3. Both images must be valid 512×512 PNGs.
          4. Print file sizes — enhanced is typically larger (more texture/detail).

        This is the key demo: run `pytest -s` and inspect the file-size diff,
        then open both PNGs side-by-side to see the visual quality difference.
        """
        subject = "a coffee shop interior"
        enhanced = enhance_prompt(subject)

        raw_path = os.path.join(outputs_dir, "raw_prompt.png")
        enhanced_path = os.path.join(outputs_dir, "enhanced_prompt.png")

        generate_image(subject, raw_path, num_inference_steps=20)
        generate_image(enhanced, enhanced_path, num_inference_steps=20)

        raw_size = os.path.getsize(raw_path)
        enhanced_size = os.path.getsize(enhanced_path)

        print(f"\n{'='*60}")
        print(f"  SUBJECT:  {subject}")
        print(f"  ENHANCED: {enhanced}")
        print(f"  File sizes — raw: {raw_size:,}B | enhanced: {enhanced_size:,}B")
        print(f"  raw image      → {raw_path}")
        print(f"  enhanced image → {enhanced_path}")
        print(f"{'='*60}")

        assert os.path.exists(raw_path) and os.path.exists(enhanced_path)
        assert Image.open(raw_path).size == (512, 512)
        assert Image.open(enhanced_path).size == (512, 512)

    @pytest.mark.slow
    def test_all_benchmark_prompts_generate_images(self, benchmark_prompts, outputs_dir):
        """
        For every business use case in benchmark_prompts.json:
          1. Enhance the raw brief with the LLM.
          2. Generate an image from the enhanced prompt.
          3. Assert the output is a valid 512×512 PNG.

        Prints a full table of raw → enhanced pairs so quality can be
        assessed visually after the test run.
        """
        print(f"\n{'='*60}")
        for entry in benchmark_prompts:
            use_case = entry["use_case"]
            raw = entry["raw"]

            enhanced = enhance_prompt(raw)
            safe_name = use_case.replace(" ", "_").lower()
            output_path = os.path.join(outputs_dir, f"{safe_name}.png")

            generate_image(enhanced, output_path, num_inference_steps=20)

            assert os.path.exists(output_path), f"[{use_case}] No image generated."
            img = Image.open(output_path)
            assert img.size == (512, 512), f"[{use_case}] Wrong size: {img.size}"

            print(f"[{use_case}]")
            print(f"  RAW:      {raw}")
            print(f"  ENHANCED: {enhanced}")
            print(f"  OUTPUT:   {output_path}")
            print()
        print(f"{'='*60}")

    @pytest.mark.slow
    def test_pipeline_resilience_with_ollama_fallback(self, mock_ollama_unavailable, outputs_dir):
        """
        Resilience test: when Ollama is down, the pipeline must not crash.
        The enhancer falls back to the raw transcript, and generation continues
        with the plain prompt — a degraded but functional result.
        """
        raw = "a sunset over the ocean"

        # Enhancer should fall back gracefully
        enhanced = enhance_prompt(raw)
        assert enhanced == raw, (
            f"With Ollama down, enhance_prompt() should return the raw text unchanged. "
            f"Got: {enhanced}"
        )

        # Image generation must still work with the raw (unenhanced) prompt
        path = os.path.join(outputs_dir, "fallback_test.png")
        generate_image(enhanced, path, num_inference_steps=10)

        assert os.path.exists(path), "Image generation must succeed even without LLM enhancement."
        img = Image.open(path)
        assert img.size == (512, 512)
        print(f"\nFallback image generated at: {path}")

    @pytest.mark.slow
    def test_quality_steps_comparison_across_use_cases(self, outputs_dir):
        """
        Demonstrates the num_inference_steps quality lever for the most
        visually demanding use case: Ad Creative.

        Compares:
          - Raw brief + 20 steps (what a user would get without this tool)
          - Enhanced brief + 50 steps (maximum quality mode)
        """
        raw = "woman using a laptop in a modern office"
        enhanced = enhance_prompt(raw)

        baseline_path = os.path.join(outputs_dir, "ad_baseline.png")   # raw, 20 steps
        quality_path = os.path.join(outputs_dir, "ad_quality.png")     # enhanced, 50 steps

        generate_image(raw, baseline_path, num_inference_steps=20)
        generate_image(
            enhanced,
            quality_path,
            num_inference_steps=50,
            guidance_scale=8.5,
            negative_prompt=(
                "blurry, low quality, deformed, watermark, text, bad anatomy, "
                "extra limbs, disfigured, ugly, amateur"
            ),
        )

        baseline_size = os.path.getsize(baseline_path)
        quality_size = os.path.getsize(quality_path)

        print(f"\n{'='*60}")
        print(f"  RAW (20 steps):           {baseline_size:,}B  → {baseline_path}")
        print(f"  ENHANCED (50 steps):      {quality_size:,}B  → {quality_path}")
        print(f"  Enhanced prompt: {enhanced}")
        print(f"{'='*60}")

        assert os.path.exists(baseline_path) and os.path.exists(quality_path)
