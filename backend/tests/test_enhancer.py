"""
test_enhancer.py
================
Quality tests for the prompt enhancement pipeline (pipeline/enhancer.py).

These tests run without Stable Diffusion — they are fast and check that:
  1. The LLM enhancer actually makes prompts richer and more detailed.
  2. The fallback path works safely when Ollama is unavailable.
  3. Every business use-case prompt gets properly enhanced.

Run:
    cd backend
    pytest tests/test_enhancer.py -v
"""

import sys
import os

# Ensure the backend package is importable when pytest runs from the tests/ folder
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from pipeline.enhancer import enhance_prompt


class TestEnhancerQuality:
    """Verify that the Ollama-based prompt enhancer improves raw transcripts."""

    @pytest.mark.slow
    def test_enhanced_prompt_is_longer_than_raw(self):
        """Enhanced prompt must be more descriptive (longer) than the raw input."""
        raw = "a dog in a park"
        enhanced = enhance_prompt(raw)
        assert len(enhanced) > len(raw), (
            f"Enhanced prompt ({len(enhanced)} chars) should be longer than raw ({len(raw)} chars).\n"
            f"Enhanced: {enhanced}"
        )

    @pytest.mark.slow
    def test_enhanced_prompt_contains_quality_keywords(self):
        """
        Enhanced prompt should contain at least 2 Stable Diffusion quality descriptors.
        The system prompt in enhancer.py explicitly instructs the LLM to add these.
        """
        quality_keywords = [
            "cinematic", "8k", "detailed", "lighting", "photorealistic",
            "sharp", "professional", "volumetric", "high quality", "4k",
            "bokeh", "dramatic", "natural light", "studio", "hyperrealistic",
        ]
        raw = "a coffee shop interior"
        enhanced = enhance_prompt(raw).lower()
        matches = [kw for kw in quality_keywords if kw in enhanced]
        assert len(matches) >= 2, (
            f"Expected ≥2 quality keywords. Found only: {matches}\n"
            f"Enhanced prompt: {enhanced}"
        )

    def test_fallback_returns_original_when_ollama_unavailable(self, mock_ollama_unavailable):
        """
        When Ollama is unreachable the enhancer must fall back to returning
        the raw transcript unchanged (graceful degradation, not a crash).
        """
        raw = "a mountain landscape at sunset"
        result = enhance_prompt(raw)
        assert result == raw, (
            f"Fallback should return the original raw transcript.\nGot: {result}"
        )

    @pytest.mark.parametrize("use_case,raw", [
        ("product",      "wireless headphones on a white background"),
        ("social_media", "morning coffee flat lay"),
        ("ad_creative",  "woman using laptop in modern office"),
        ("brand",        "minimal tech startup logo"),
        ("real_estate",  "modern living room sunlight"),
    ])
    @pytest.mark.slow
    def test_business_use_case_enhancement(self, use_case, raw):
        """
        Each business use-case prompt must be enhanced:
          - result differs from the raw input
          - result is longer (more descriptive) than the raw input
        Prints the raw → enhanced pair so you can visually inspect quality.
        """
        enhanced = enhance_prompt(raw)
        print(f"\n[{use_case}]\n  RAW:      {raw}\n  ENHANCED: {enhanced}")
        assert enhanced != raw, (
            f"[{use_case}] Enhanced prompt should differ from raw input."
        )
        assert len(enhanced) > len(raw), (
            f"[{use_case}] Enhanced ({len(enhanced)} chars) should be longer than raw ({len(raw)} chars)."
        )

    @pytest.mark.slow
    def test_enhanced_prompt_has_no_conversational_prefix(self):
        """
        The enhancer system prompt says 'Respond ONLY with the final prompt'.
        Verify the output does not start with a conversational preamble.
        """
        raw = "a sunrise over mountains"
        enhanced = enhance_prompt(raw)
        forbidden_prefixes = ["sure", "here is", "here's", "of course", "certainly", "i'll", "below"]
        first_word = enhanced.lower().split()[0] if enhanced.split() else ""
        assert first_word not in forbidden_prefixes, (
            f"Enhanced prompt starts with a conversational prefix: '{first_word}'\n"
            f"Full enhanced: {enhanced}"
        )

    @pytest.mark.slow
    def test_enhanced_prompt_is_not_empty(self):
        """Enhancement must always return a non-empty string."""
        raw = "a simple red circle"
        enhanced = enhance_prompt(raw)
        assert enhanced.strip(), "Enhanced prompt must not be empty."

    @pytest.mark.slow
    def test_benchmark_prompts_quality_keywords(self, benchmark_prompts):
        """
        For every entry in benchmark_prompts.json, at least one of its
        expected_quality_keywords should appear in the enhanced prompt.
        """
        for entry in benchmark_prompts:
            use_case = entry["use_case"]
            raw = entry["raw"]
            expected_kws = [kw.lower() for kw in entry["expected_quality_keywords"]]

            enhanced = enhance_prompt(raw).lower()
            matches = [kw for kw in expected_kws if kw in enhanced]

            print(f"\n[{use_case}] matched keywords: {matches}")
            assert len(matches) >= 1, (
                f"[{use_case}] Enhanced prompt should contain at least 1 expected quality keyword.\n"
                f"Expected any of: {expected_kws}\n"
                f"Enhanced: {enhanced}"
            )
