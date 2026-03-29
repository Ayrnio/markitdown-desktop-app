"""Helpers for OpenAI-compatible local servers (e.g. LM Studio)."""

from __future__ import annotations

# Substrings commonly found in multimodal / vision model ids. OpenAI-compatible
# servers do not expose capabilities in /v1/models, so this is a best-effort hint.
_VISION_MODEL_HINTS: tuple[str, ...] = (
    "vision",
    "llava",
    "moondream",
    "bakllava",
    "cogvlm",
    "internvl",
    "minicpm-v",
    "qwen-vl",
    "qwen2-vl",
    "qwen2.5-vl",
    "phi-3-vision",
    "phi3-vision",
    "phi-4-multimodal",
    "pixtral",
    "smolvlm",
    "idefics",
    "florence",
    "mplug",
    "gpt-4o",
    "gpt-4.1",
    "o4-mini",
    "granite-vision",
    "llama-3.2",
    "llama3.2",
    "llama-3.3",
    "llama3.3",
    "-vl-",
    "vl-",
    "-vl",
)


def filter_likely_vision_models(model_ids: list[str]) -> list[str]:
    """Return ids that likely support image inputs, preserving input order."""
    seen: set[str] = set()
    out: list[str] = []
    for mid in model_ids:
        if mid in seen:
            continue
        lower = mid.lower()
        if any(h in lower for h in _VISION_MODEL_HINTS):
            seen.add(mid)
            out.append(mid)
    return out


def _require_openai():
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "OpenAI-compatible testing requires the 'openai' package. "
            "Install it with: pip install openai"
        ) from exc
    return OpenAI


def test_openai_compatible_endpoint(base_url: str) -> str:
    """Call GET /v1/models (via the OpenAI client) and return a short status line."""
    url = (base_url or "").strip()
    if not url:
        raise RuntimeError("Set the OpenAI-compatible API base URL first.")

    OpenAI = _require_openai()
    client = OpenAI(base_url=url, api_key="lm-studio")
    response = client.models.list()
    data = getattr(response, "data", None) or []
    count = len(data)
    return f"Connected; {count} model(s) reported by the server."


def fetch_openai_compatible_model_ids(base_url: str) -> list[str]:
    """Return sorted unique model ids from GET /v1/models."""
    url = (base_url or "").strip()
    if not url:
        raise RuntimeError("Set the OpenAI-compatible API base URL first.")

    OpenAI = _require_openai()
    client = OpenAI(base_url=url, api_key="lm-studio")
    response = client.models.list()
    data = getattr(response, "data", None) or []
    ids: list[str] = []
    for item in data:
        mid = getattr(item, "id", None)
        if mid:
            ids.append(str(mid))
    return sorted(set(ids), key=str.casefold)
