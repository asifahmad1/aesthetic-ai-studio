"""Persistent storage for projects and settings (JSON files on disk)."""

from __future__ import annotations

import copy
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import schema

_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]+$")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_id(pid: str) -> str | None:
    """Return the id only if it is safe to use as a file name, else None."""
    if isinstance(pid, str) and _SAFE_ID.match(pid):
        return pid
    return None


class ProjectStore:
    """CRUD store for project documents. Projects live in <root>/projects/<id>.json."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        (self.root / "projects").mkdir(parents=True, exist_ok=True)

    def _path(self, pid: str) -> Path | None:
        safe = _safe_id(pid)
        if safe is None:
            return None
        return self.root / "projects" / f"{safe}.json"

    def list(self) -> list[dict]:
        """Return summary dicts: id, title, slide_count, status, updated (newest first)."""
        summaries = []
        for path in (self.root / "projects").glob("*.json"):
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(doc, dict):
                continue
            summaries.append(
                {
                    "id": doc.get("id"),
                    "title": doc.get("title"),
                    "slide_count": doc.get("slide_count", len(doc.get("slides", []))),
                    "status": doc.get("status"),
                    "updated": doc.get("updated"),
                }
            )
        summaries.sort(key=lambda s: s.get("updated") or "", reverse=True)
        return summaries

    def get(self, pid: str) -> dict | None:
        """Return the full project document, or None if not found/unreadable."""
        path = self._path(pid)
        if path is None or not path.exists():
            return None
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return doc if isinstance(doc, dict) else None

    def save(self, doc: dict) -> dict:
        """Validate, refresh the updated timestamp, and persist the document.

        Raises ValueError listing validation errors when the document is invalid.
        """
        errors = schema.validate_project(doc)
        if errors:
            raise ValueError("Invalid project: " + "; ".join(errors))
        doc["updated"] = _now_iso()
        path = self._path(doc["id"])
        if path is None:
            raise ValueError(f"Invalid project id: {doc['id']!r}")
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        return doc

    def delete(self, pid: str) -> bool:
        """Delete a project. Returns True when something was deleted."""
        path = self._path(pid)
        if path is None or not path.exists():
            return False
        path.unlink()
        return True


_DEFAULT_SETTINGS = {
    "providers": {
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-4o-mini",
            "api_key": "",
            "configured": False,
        },
        "gemini": {
            "model": "gemini-2.0-flash",
            "api_key": "",
            "configured": False,
        },
        "ollama": {
            "base_url": "http://localhost:11434",
            "model": "",
            "configured": False,
        },
    }
}

_PROVIDER_FIELDS = {
    "openai": ("base_url", "model", "api_key"),
    "gemini": ("model", "api_key"),
    "ollama": ("base_url", "model"),
}


def _is_configured(kind: str, entry: dict) -> bool:
    if kind == "openai":
        return bool(entry.get("api_key")) and bool(entry.get("model"))
    if kind == "gemini":
        return bool(entry.get("api_key")) and bool(entry.get("model"))
    if kind == "ollama":
        return bool(entry.get("model")) and bool(entry.get("base_url"))
    return False


class SettingsStore:
    """Server-side settings, including provider credentials (never sent to clients)."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._path = self.root / "settings.json"

    def get(self) -> dict:
        """Return the full settings dict (includes api keys — server side only)."""
        merged = copy.deepcopy(_DEFAULT_SETTINGS)
        if self._path.exists():
            try:
                stored = json.loads(self._path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                stored = {}
            if isinstance(stored, dict):
                for kind, entry in (stored.get("providers") or {}).items():
                    if kind in merged["providers"] and isinstance(entry, dict):
                        merged["providers"][kind].update(entry)
        return merged

    def set_provider(self, kind: str, cfg: dict | None) -> dict:
        """Store/merge provider config and recompute its 'configured' flag."""
        if kind not in _PROVIDER_FIELDS:
            raise ValueError(f"Unknown provider: {kind!r}")
        cfg = dict(cfg or {})
        settings = self.get()
        entry = settings["providers"][kind]
        for field in _PROVIDER_FIELDS[kind]:
            if field in cfg and isinstance(cfg[field], str):
                entry[field] = cfg[field].strip() if field != "api_key" else cfg[field]
        entry["configured"] = _is_configured(kind, entry)
        self._path.write_text(
            json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return entry

    def public_view(self) -> dict:
        """Settings safe for API responses: flags + base_url/model, no api keys."""
        settings = self.get()
        public = {"providers": {}}
        for kind, entry in settings["providers"].items():
            view = {
                "configured": bool(entry.get("configured")),
                "model": entry.get("model", ""),
            }
            if "base_url" in entry:
                view["base_url"] = entry.get("base_url", "")
            public["providers"][kind] = view
        return public
