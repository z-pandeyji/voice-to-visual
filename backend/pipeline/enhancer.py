import os
import re
import traceback
import requests

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
# If OLLAMA_MODEL env var is set, always use it.
# Otherwise, auto-detect the first installed model from the Ollama server.
_OLLAMA_MODEL_ENV: str | None = os.getenv("OLLAMA_MODEL")

_PREFERRED = [
    "minimax-m2.5:cloud","llama3", "llama3.2", "llama3.1", "llama2",
    "mistral", "mixtral",
    "gemma3", "gemma2", "gemma",
    "phi3", "phi", "qwen2", "qwen",
]
_detected_model: str | None = None


def _resolve_model() -> str | None:
    """Return the model to use, auto-detecting from Ollama if not overridden by env."""
    global _detected_model

    if _OLLAMA_MODEL_ENV:
        return _OLLAMA_MODEL_ENV

    if _detected_model is not None:
        return _detected_model

    try:
        resp = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        resp.raise_for_status()
        models = resp.json().get("models", [])
        if not models:
            print("[enhancer] Ollama has no models installed.")
            return None
        # Build two lookup dicts: one by full name, one by base name (before ":")
        installed_full = {m["name"].lower(): m["name"] for m in models}
        installed_base = {m["name"].split(":")[0].lower(): m["name"] for m in models}
        print(f"[enhancer] Installed Ollama models: {list(installed_full.keys())}")
        for pref in _PREFERRED:
            pref_lower = pref.lower()
            # Match on full name first (e.g. "minimax-m2.5:cloud"), then base
            if pref_lower in installed_full:
                _detected_model = installed_full[pref_lower]
                print(f"[enhancer] Auto-selected model: {_detected_model}")
                return _detected_model
            if pref_lower in installed_base:
                _detected_model = installed_base[pref_lower]
                print(f"[enhancer] Auto-selected model: {_detected_model}")
                return _detected_model
        # Fallback: first available
        _detected_model = models[0]["name"]
        print(f"[enhancer] Using first available model: {_detected_model}")
        return _detected_model
    except Exception as e:
        print(f"[enhancer] Could not reach Ollama for model detection: {e}")
        return None


def _clean_llm_output(text: str) -> str:
    """Strip common LLM preamble / markdown so only the prompt text remains."""
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'^[#\s]*enhanced\s+prompt\s*[:\-]*\s*', '', text, flags=re.IGNORECASE)
    preamble = re.compile(
        r'^(?:'
        r"here(?:'s| is)(?: (?:the|a|an|your))?(?: (?:enhanced|improved|cinematic|detailed|rewritten))?"
        r'(?: (?:image\s+)?prompt)?'
        r'|sure[!,]?\s*(?:here(?:\'s| is)[^:\n]*)?'
        r'|(?:image\s+)?prompt'
        r'|certainly[!,]?'
        r')[:\s\-]*',
        re.IGNORECASE,
    )
    text = preamble.sub('', text.strip()).strip()
    text = re.sub(r'^["""\'\']+|["""\'\']+$', '', text).strip()
    return text


def enhance_prompt(raw_transcript: str) -> str:
    print(f"[enhancer] INPUT: '{raw_transcript}'")

    system_prompt = (
        "You are an expert cinematic prompt engineer for Stable Diffusion and text-to-video models. "
        "Convert the user's raw voice transcript into a concise, vivid image/video generation prompt. "
        "STRICT LIMIT: output must be 60 tokens or fewer (roughly 12-15 words). "
        "Include the most important visual keywords: subject, style, lighting, mood. "
        "Respond ONLY with the final prompt. No conversational text, explanations, or quotes."
    )

    model = _resolve_model()
    if model is None:
        print("[enhancer] FALLBACK — no Ollama model available.")
        return raw_transcript

    result = _try_chat(model, system_prompt, raw_transcript)
    if result is not None:
        return result

    print("[enhancer] /api/chat failed — retrying with /api/generate")
    result = _try_generate(model, system_prompt, raw_transcript)
    if result is not None:
        return result

    print("[enhancer] FALLBACK — both Ollama endpoints failed, using raw transcript")
    return raw_transcript


def _try_chat(model: str, system_prompt: str, user_text: str) -> str | None:
    """Call /api/chat. Returns enhanced string on success, None on any failure."""
    url = f"{OLLAMA_HOST}/api/chat"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        "stream": False,
    }
    print(f"[enhancer] POST {url} model={model} timeout=180s")
    try:
        response = requests.post(url, json=payload, timeout=180)
        print(f"[enhancer] HTTP {response.status_code}")
        if response.status_code != 200:
            print(f"[enhancer] /api/chat non-200: {response.text[:200]}")
            return None
        data = response.json()
        raw_output = data["message"]["content"].strip()
        enhanced = _clean_llm_output(raw_output) or raw_output
        print(f"[enhancer] ENHANCED via /api/chat: '{enhanced[:120]}'")
        return enhanced
    except Exception as e:
        print(f"[enhancer] /api/chat error: {e}")
        return None


def _try_generate(model: str, system_prompt: str, user_text: str) -> str | None:
    """Call /api/generate (older Ollama endpoint). Returns enhanced string on success, None on failure."""
    url = f"{OLLAMA_HOST}/api/generate"
    full_prompt = (
        f"[SYSTEM]\n{system_prompt}\n\n"
        f"[USER]\n{user_text}\n\n"
        f"[ASSISTANT]\n"
    )
    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": False,
    }
    print(f"[enhancer] POST {url} model={model} timeout=180s")
    try:
        response = requests.post(url, json=payload, timeout=180)
        print(f"[enhancer] HTTP {response.status_code}")
        if response.status_code != 200:
            print(f"[enhancer] /api/generate non-200: {response.text[:200]}")
            return None
        data = response.json()
        raw_output = data.get("response", "").strip()
        enhanced = _clean_llm_output(raw_output) or raw_output
        print(f"[enhancer] ENHANCED via /api/generate: '{enhanced[:120]}'")
        return enhanced
    except Exception as e:
        print(f"[enhancer] /api/generate error: {e}")
        return None

if __name__ == "__main__":
    result = enhance_prompt("a dog drinking coffee")
    print("Test Output:", result)
