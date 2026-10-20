"""Schema for Aesthetic AI Studio v1.

Defines the slide-document model (plain JSON dicts), validation, id
generation, and the blank-project factory.

Canvas: 1000 x 562.5 units (16:9). All element x/y/w/h use these units.
"""

from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone

# Canvas geometry (16:9).
CANVAS_W = 1000.0
CANVAS_H = 562.5

HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")

STATUSES = ("draft", "outline", "ready")
PROVIDER_KINDS = ("offline", "openai", "gemini", "ollama")
ELEMENT_TYPES = ("text", "shape", "table", "image")
TEXT_ROLES = (
    "title", "subtitle", "kicker", "heading", "body",
    "bullets", "quote", "caption", "stat-value", "stat-label",
)
SHAPES = ("rect", "roundrect", "oval", "line")
ALIGNS = ("left", "center", "right")


def new_id(prefix: str) -> str:
    """Return a new id like 'p_' + 8 hex chars."""
    return f"{prefix}{secrets.token_hex(4)}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def blank_project(params: dict | None) -> dict:
    """Build a new, empty project document from user-supplied params."""
    p = dict(params or {})
    provider = p.get("provider") or {}
    try:
        slide_count = int(p.get("slide_count", 10))
    except (TypeError, ValueError):
        slide_count = 10
    now = _now_iso()
    return {
        "id": new_id("p_"),
        "title": str(p.get("title", "Untitled Presentation")),
        "instructions": str(p.get("instructions", "")),
        "purpose": str(p.get("purpose", "")),
        "audience": str(p.get("audience", "")),
        "knowledge_level": str(p.get("knowledge_level", "")),
        "slide_count": slide_count,
        "theme": str(p.get("theme", "emerald-ivory")),
        "slide_size": "16:9",
        "provider": {
            "kind": str(provider.get("kind", "offline")),
            "model": str(provider.get("model", "")),
        },
        "status": "draft",
        "outline": [],
        "slides": [],
        "created": now,
        "updated": now,
    }


def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _check_color(errors: list, where: str, value) -> None:
    if value is not None and not (isinstance(value, str) and HEX_COLOR.match(value)):
        errors.append(f"{where}: color must be '#rrggbb' or null, got {value!r}")


def validate_project(doc) -> list[str]:
    """Validate a project document.

    Returns a list of human-readable error strings; [] means valid.
    Checks required keys, value types, element bounds (0..1000 / 0..562.5),
    and that layout/theme ids are known.
    """
    from themes import THEMES          # lazy: themes is standalone, no cycle
    from generator import LAYOUTS      # lazy: generator imports schema (new_id)

    errors: list[str] = []
    if not isinstance(doc, dict):
        return ["project must be a JSON object"]

    required = (
        "id", "title", "instructions", "purpose", "audience",
        "knowledge_level", "slide_count", "theme", "slide_size",
        "provider", "status", "outline", "slides", "created", "updated",
    )
    for key in required:
        if key not in doc:
            errors.append(f"missing required key: {key!r}")

    def _str(key, allow_empty=True):
        if key in doc and not isinstance(doc[key], str):
            errors.append(f"{key!r} must be a string")
        elif key in doc and not allow_empty and not doc[key].strip():
            errors.append(f"{key!r} must not be empty")

    _str("id", allow_empty=False)
    _str("title", allow_empty=False)
    _str("instructions")
    _str("purpose")
    _str("audience")
    _str("knowledge_level")
    _str("created", allow_empty=False)
    _str("updated", allow_empty=False)

    if "slide_count" in doc and (
        not isinstance(doc["slide_count"], int) or isinstance(doc["slide_count"], bool)
    ):
        errors.append("'slide_count' must be an integer")

    if "theme" in doc:
        if not isinstance(doc["theme"], str):
            errors.append("'theme' must be a string")
        elif doc["theme"] not in THEMES:
            errors.append(f"unknown theme id: {doc['theme']!r}")

    if "slide_size" in doc and doc["slide_size"] != "16:9":
        errors.append("'slide_size' must be '16:9'")

    prov = doc.get("provider")
    if "provider" in doc:
        if not isinstance(prov, dict):
            errors.append("'provider' must be an object")
        else:
            if prov.get("kind") not in PROVIDER_KINDS:
                errors.append(f"unknown provider kind: {prov.get('kind')!r}")
            if "model" in prov and not isinstance(prov["model"], str):
                errors.append("'provider.model' must be a string")

    if "status" in doc and doc["status"] not in STATUSES:
        errors.append(f"unknown status: {doc['status']!r}")

    if "outline" in doc:
        if not isinstance(doc["outline"], list):
            errors.append("'outline' must be a list")
        else:
            for i, item in enumerate(doc["outline"]):
                where = f"outline[{i}]"
                if not isinstance(item, dict):
                    errors.append(f"{where} must be an object")
                    continue
                for k in ("title", "bullets", "layout_hint", "notes"):
                    if k not in item:
                        errors.append(f"{where} missing key: {k!r}")
                if "title" in item and not isinstance(item["title"], str):
                    errors.append(f"{where}.title must be a string")
                if "bullets" in item:
                    if not isinstance(item["bullets"], list) or not all(
                        isinstance(b, str) for b in item["bullets"]
                    ):
                        errors.append(f"{where}.bullets must be a list of strings")
                if "layout_hint" in item:
                    if not isinstance(item["layout_hint"], str):
                        errors.append(f"{where}.layout_hint must be a string")
                    elif item["layout_hint"] not in LAYOUTS:
                        errors.append(
                            f"{where} unknown layout_hint: {item['layout_hint']!r}"
                        )
                if "notes" in item and not isinstance(item["notes"], str):
                    errors.append(f"{where}.notes must be a string")

    if "slides" in doc:
        if not isinstance(doc["slides"], list):
            errors.append("'slides' must be a list")
        else:
            for i, slide in enumerate(doc["slides"]):
                _validate_slide(errors, f"slides[{i}]", slide, LAYOUTS)

    return errors


def _validate_slide(errors: list, where: str, slide, layouts) -> None:
    if not isinstance(slide, dict):
        errors.append(f"{where} must be an object")
        return
    for k in ("id", "layout", "elements", "notes"):
        if k not in slide:
            errors.append(f"{where} missing key: {k!r}")
    if "id" in slide and not isinstance(slide["id"], str):
        errors.append(f"{where}.id must be a string")
    if "layout" in slide:
        if not isinstance(slide["layout"], str):
            errors.append(f"{where}.layout must be a string")
        elif slide["layout"] not in layouts:
            errors.append(f"{where} unknown layout: {slide['layout']!r}")
    if "notes" in slide and not isinstance(slide["notes"], str):
        errors.append(f"{where}.notes must be a string")
    if "elements" in slide:
        if not isinstance(slide["elements"], list):
            errors.append(f"{where}.elements must be a list")
        else:
            for j, el in enumerate(slide["elements"]):
                _validate_element(errors, f"{where}.elements[{j}]", el)


def _validate_element(errors: list, where: str, el) -> None:
    if not isinstance(el, dict):
        errors.append(f"{where} must be an object")
        return
    for k in ("id", "type", "x", "y", "w", "h"):
        if k not in el:
            errors.append(f"{where} missing key: {k!r}")
    if el.get("type") not in ELEMENT_TYPES:
        errors.append(f"{where} unknown element type: {el.get('type')!r}")
        return

    for k in ("x", "y", "w", "h"):
        if k in el and not _is_num(el[k]):
            errors.append(f"{where}.{k} must be a number")

    # Bounds check on the 1000 x 562.5 canvas.
    if all(_is_num(el.get(k)) for k in ("x", "y", "w", "h")):
        x, y, w, h = (float(el[k]) for k in ("x", "y", "w", "h"))
        if not (0 <= x <= CANVAS_W):
            errors.append(f"{where}.x out of canvas bounds 0..{CANVAS_W}")
        if not (0 <= y <= CANVAS_H):
            errors.append(f"{where}.y out of canvas bounds 0..{CANVAS_H}")
        if w <= 0:
            errors.append(f"{where}.w must be > 0")
        if h <= 0:
            errors.append(f"{where}.h must be > 0")
        if x + w > CANVAS_W + 1e-6:
            errors.append(f"{where} extends past canvas right edge (x+w > {CANVAS_W})")
        if y + h > CANVAS_H + 1e-6:
            errors.append(f"{where} extends past canvas bottom edge (y+h > {CANVAS_H})")

    _check_color(errors, f"{where}.fill", el.get("fill"))
    _check_color(errors, f"{where}.line", el.get("line"))
    _check_color(errors, f"{where}.text_color", el.get("text_color"))
    if "font_size" in el and el["font_size"] is not None and (
        not isinstance(el["font_size"], int) or isinstance(el["font_size"], bool)
    ):
        errors.append(f"{where}.font_size must be an integer or null")
    if "bold" in el and not isinstance(el["bold"], bool):
        errors.append(f"{where}.bold must be a boolean")
    if "align" in el and el["align"] not in ALIGNS:
        errors.append(f"{where}.align must be one of {ALIGNS}")

    etype = el["type"]
    if etype == "text":
        if el.get("role") not in TEXT_ROLES:
            errors.append(f"{where} unknown text role: {el.get('role')!r}")
        if "text" in el and not isinstance(el["text"], str):
            errors.append(f"{where}.text must be a string")
    elif etype == "shape":
        if el.get("shape") not in SHAPES:
            errors.append(f"{where} unknown shape: {el.get('shape')!r}")
    elif etype == "table":
        rows = el.get("rows")
        if not isinstance(rows, list) or not rows:
            errors.append(f"{where}.rows must be a non-empty list of rows")
        else:
            width = None
            for r, row in enumerate(rows):
                if not isinstance(row, list) or not all(
                    isinstance(c, str) for c in row
                ):
                    errors.append(f"{where}.rows[{r}] must be a list of strings")
                    continue
                if width is None:
                    width = len(row)
                elif len(row) != width:
                    errors.append(f"{where}.rows[{r}] has inconsistent column count")
    elif etype == "image":
        if "alt" in el and not isinstance(el["alt"], str):
            errors.append(f"{where}.alt must be a string")
        if "prompt" in el and not isinstance(el["prompt"], str):
            errors.append(f"{where}.prompt must be a string")
