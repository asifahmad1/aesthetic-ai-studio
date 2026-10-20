"""AI provider integrations for Aesthetic AI Studio v1.

Supported kinds: openai, gemini, ollama (plus 'offline', which cannot call
an API and always raises ProviderError).

cfg shape: {"kind", "model", "api_key", "base_url"}
brief shape: {"title", "instructions", "purpose", "audience",
              "knowledge_level", "slide_count"}

Every failure raises ProviderError carrying the REAL error message — the
caller must surface it, never claim success falsely. No API keys are
hardcoded anywhere; credentials arrive in cfg from the SettingsStore.
"""

from __future__ import annotations

import json
import re

import requests

REQUEST_TIMEOUT = 90  # seconds, per contract

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


class ProviderError(Exception):
    """Raised for any provider failure, carrying the real error message."""


# ---------------------------------------------------------------------------
# low-level HTTP helpers
# ---------------------------------------------------------------------------

def _post_json(url: str, payload: dict, headers: dict | None = None) -> dict:
    """POST JSON and return the decoded body, raising ProviderError on failure."""
    try:
        resp = requests.post(url, json=payload, headers=headers or {},
                             timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        raise ProviderError(f"Request failed: {exc}") from exc
    if resp.status_code >= 400:
        body = (resp.text or "").strip()[:500]
        raise ProviderError(f"HTTP {resp.status_code} from provider: {body}")
    try:
        data = resp.json()
    except ValueError as exc:
        raise ProviderError(
            f"Provider returned non-JSON response: {(resp.text or '')[:200]}"
        ) from exc
    if not isinstance(data, dict):
        raise ProviderError("Provider returned an unexpected response shape")
    return data


def _strip_fences(text: str) -> str:
    """Remove ```json ... ``` fences some models wrap around their JSON."""
    match = _FENCE_RE.search(text or "")
    return match.group(1) if match else (text or "").strip()


def _parse_json_object(text: str, what: str) -> dict | list:
    cleaned = _strip_fences(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ProviderError(
            f"Model returned invalid JSON for {what}: {exc}; "
            f"raw excerpt: {cleaned[:200]}"
        ) from exc


# ---------------------------------------------------------------------------
# per-provider raw text calls
# ---------------------------------------------------------------------------

def _call_openai(cfg: dict, messages: list[dict], as_json: bool = True) -> str:
    base_url = (cfg.get("base_url") or "https://api.openai.com/v1").rstrip("/")
    model = cfg.get("model") or "gpt-4o-mini"
    api_key = cfg.get("api_key") or ""
    if not api_key:
        raise ProviderError("OpenAI API key is not configured (see Settings)")
    payload: dict = {"model": model, "messages": messages, "temperature": 0.7}
    if as_json:
        payload["response_format"] = {"type": "json_object"}
    data = _post_json(
        f"{base_url}/chat/completions",
        payload,
        {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    try:
        return data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderError(
            f"Unexpected OpenAI response shape: {json.dumps(data)[:200]}"
        ) from exc


def _call_gemini(cfg: dict, prompt: str) -> str:
    model = cfg.get("model") or "gemini-3.8-flash"
    api_key = cfg.get("api_key") or ""
    if not api_key:
        raise ProviderError("Gemini API key is not configured (see Settings)")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    data = _post_json(
        url,
        {"contents": [{"parts": [{"text": prompt}]}]},
        {"Content-Type": "application/json"},
    )
    feedback = (data.get("promptFeedback") or {}).get("blockReason")
    if feedback:
        raise ProviderError(f"Gemini blocked the prompt: {feedback}")
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"] or ""
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderError(
            f"Unexpected Gemini response shape: {json.dumps(data)[:200]}"
        ) from exc


def _call_ollama(cfg: dict, messages: list[dict], as_json: bool = True) -> str:
    base_url = (cfg.get("base_url") or "http://localhost:11434").rstrip("/")
    model = cfg.get("model") or ""
    if not model:
        raise ProviderError("Ollama model is not configured (see Settings)")
    payload: dict = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    if as_json:
        payload["format"] = "json"
    data = _post_json(
        f"{base_url}/api/chat", payload, {"Content-Type": "application/json"}
    )
    try:
        return data["message"]["content"] or ""
    except (KeyError, TypeError) as exc:
        raise ProviderError(
            f"Unexpected Ollama response shape: {json.dumps(data)[:200]}"
        ) from exc


def _check_kind(cfg: dict) -> str:
    kind = (cfg.get("kind") or "offline").lower()
    if kind == "offline":
        raise ProviderError(
            "Offline provider cannot call an AI API — connect a provider in Settings"
        )
    if kind not in ("openai", "gemini", "ollama"):
        raise ProviderError(f"Unknown provider kind: {cfg.get('kind')!r}")
    return kind


def generate_json(cfg: dict, system_prompt: str, user_prompt: str) -> dict | list:
    """Low-level helper: run one prompt through the configured provider.

    Returns the parsed JSON (dict or list). Raises ProviderError on any failure.
    """
    kind = _check_kind(cfg)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    if kind == "openai":
        raw = _call_openai(cfg, messages)
    elif kind == "gemini":
        raw = _call_gemini(cfg, f"{system_prompt}\n\n{user_prompt}")
    else:  # ollama
        raw = _call_ollama(cfg, messages)
    return _parse_json_object(raw, "request")


# ---------------------------------------------------------------------------
# prompts
# ---------------------------------------------------------------------------

def _layout_hint_list() -> str:
    from generator import LAYOUTS  # lazy: generator does not import providers

    return ", ".join(sorted(LAYOUTS))


def _brief_text(brief: dict) -> str:
    return (
        f"Presentation title: {brief.get('title', '')}\n"
        f"Author instructions: {brief.get('instructions', '')}\n"
        f"Purpose: {brief.get('purpose', '')}\n"
        f"Audience: {brief.get('audience', '')}\n"
        f"Audience knowledge level: {brief.get('knowledge_level', '')}\n"
        f"Desired slide count: {brief.get('slide_count', '')}"
    )


_OUTLINE_SYSTEM = (
    "You are a presentation outline planner. Return ONLY valid JSON — no "
    "markdown, no commentary. The JSON must be an object with a single key "
    '"slides", whose value is a list of slide objects. Each slide object must '
    'have exactly these keys: "title" (string), "bullets" (list of 3-5 concise '
    'strings), "layout_hint" (one of: {layouts}), and "notes" (2-3 sentences of '
    "speaker notes). Vary the layout_hint values across slides."
)


def _coerce_outline_item(item: dict, index: int) -> dict:
    from generator import LAYOUTS  # lazy

    if not isinstance(item, dict):
        raise ProviderError(f"Outline slide {index} is not an object")
    title = item.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ProviderError(f"Outline slide {index} has no valid title")
    bullets = item.get("bullets") or []
    if not isinstance(bullets, list):
        raise ProviderError(f"Outline slide {index} bullets must be a list")
    bullets = [str(b) for b in bullets][:6]
    hint = item.get("layout_hint") or "title-content"
    if hint not in LAYOUTS:
        hint = "title-content"
    notes = item.get("notes") or ""
    return {
        "title": title.strip(),
        "bullets": bullets,
        "layout_hint": hint,
        "notes": str(notes),
    }


def generate_outline(cfg: dict, brief: dict) -> list[dict]:
    """Generate a slide outline via the configured AI provider."""
    _check_kind(cfg)
    system = _OUTLINE_SYSTEM.format(layouts=_layout_hint_list())
    user = (
        _brief_text(brief)
        + "\n\nWrite the outline now. First slide should introduce the topic "
        "(layout_hint 'cover'), last slide should close it (layout_hint "
        "'thank-you')."
    )
    parsed = generate_json(cfg, system, user)
    if isinstance(parsed, dict):
        items = parsed.get("slides", parsed.get("outline"))
    elif isinstance(parsed, list):
        items = parsed
    else:
        raise ProviderError("Model returned an unexpected outline shape")
    if not isinstance(items, list) or not items:
        raise ProviderError("Model returned an empty outline")
    return [_coerce_outline_item(it, i) for i, it in enumerate(items)]


_SLIDE_SYSTEM = (
    "You are a slide-content writer. Return ONLY valid JSON — no markdown, no "
    "commentary. The JSON must be an object with exactly these keys: "
    '"title" (string), "bullets" (list of 3-5 concise strings), "notes" '
    "(2-3 sentences of speaker notes)."
)


def generate_slide_content(cfg: dict, brief: dict, item: dict) -> dict:
    """(Re)generate title/bullets/notes for a single slide via the AI provider."""
    _check_kind(cfg)
    user = (
        _brief_text(brief)
        + "\n\nCurrent slide draft:\n"
        + f"Title: {item.get('title', '')}\n"
        + "Bullets:\n"
        + "".join(f"- {b}\n" for b in (item.get("bullets") or []))
        + f"\nNotes: {item.get('notes', '')}\n"
        + "\nWrite improved content for this slide now."
    )
    parsed = generate_json(cfg, _SLIDE_SYSTEM, user)
    if not isinstance(parsed, dict):
        raise ProviderError("Model returned an unexpected slide-content shape")
    title = parsed.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ProviderError("Model returned no valid slide title")
    bullets = parsed.get("bullets") or []
    if not isinstance(bullets, list):
        raise ProviderError("Model returned invalid slide bullets")
    return {
        "title": title.strip(),
        "bullets": [str(b) for b in bullets][:6],
        "notes": str(parsed.get("notes") or ""),
    }


def test_connection(cfg: dict) -> bool:
    """Send a tiny 'Say OK' probe through the provider.

    Returns True on success; raises ProviderError with the real error otherwise.
    """
    kind = _check_kind(cfg)
    if kind == "openai":
        raw = _call_openai(
            cfg,
            [{"role": "user", "content": "Reply with exactly: OK"}],
            as_json=False,
        )
    elif kind == "gemini":
        raw = _call_gemini(cfg, "Reply with exactly: OK")
    else:  # ollama
        raw = _call_ollama(
            cfg,
            [{"role": "user", "content": "Reply with exactly: OK"}],
            as_json=False,
        )
    if "OK" not in (raw or "").upper():
        raise ProviderError(f"Unexpected test response from provider: {raw[:120]!r}")
    return True
