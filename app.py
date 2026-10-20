"""Flask backend for Aesthetic AI Studio v1.

Run locally:  python app.py   ->  http://127.0.0.1:4321

All API routes return JSON (unless noted). Exporter modules
(export_pptx / export_pdf / export_html) are written by another agent and
imported lazily inside the export route, so the app works without them.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

from flask import Flask, jsonify, request, send_file, send_from_directory

import providers
from generator import (
    LAYOUTS,
    apply_theme,
    build_slides,
    compose_outline_offline,
)
from render import render_slide_html
from sample import build_sample_project
from schema import blank_project, validate_project
from store import ProjectStore, SettingsStore
from themes import THEMES, get_theme, list_themes

BASE_DIR = Path(__file__).resolve().parent

_OFFLINE_ASSIST_MSG = (
    "No AI provider configured — connect one in Settings to use AI assist."
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _json_body(required: bool = True):
    """Return the parsed JSON body dict, or (None, error_response)."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        if required:
            return None, (jsonify({"error": "Request body must be JSON"}), 400)
        return {}, None
    return data, None


def _project_cfg(project: dict, settings: SettingsStore) -> dict:
    """Build a provider cfg from the project's provider kind + stored settings."""
    kind = ((project.get("provider") or {}).get("kind") or "offline").lower()
    stored = settings.get()["providers"].get(kind, {})
    return {
        "kind": kind,
        "model": (project.get("provider") or {}).get("model") or stored.get("model", ""),
        "api_key": stored.get("api_key", ""),
        "base_url": stored.get("base_url", ""),
    }


def _brief_from_project(project: dict) -> dict:
    return {
        "title": project.get("title", ""),
        "instructions": project.get("instructions", ""),
        "purpose": project.get("purpose", ""),
        "audience": project.get("audience", ""),
        "knowledge_level": project.get("knowledge_level", ""),
        "slide_count": project.get("slide_count", 10),
    }


def _slide_summary(slide: dict) -> dict:
    """Extract {title, bullets, notes} from a built slide's elements."""
    title, bullets = "", []
    for el in slide.get("elements", []):
        if el.get("type") != "text":
            continue
        if el.get("role") == "title" and not title:
            title = el.get("text", "")
        elif el.get("role") == "bullets" and not bullets:
            for line in (el.get("text", "") or "").split("\n"):
                clean = line.strip().lstrip("•-☑✓✗▸ ").strip()
                if clean:
                    bullets.append(clean)
    return {"title": title, "bullets": bullets, "notes": slide.get("notes", "")}


# ---------------------------------------------------------------------------
# app factory
# ---------------------------------------------------------------------------

def create_app(data_root: str | Path | None = None) -> Flask:
    root = Path(data_root) if data_root else BASE_DIR / "data"
    root.mkdir(parents=True, exist_ok=True)
    (root / "exports").mkdir(parents=True, exist_ok=True)

    projects = ProjectStore(root)
    settings = SettingsStore(root)

    app = Flask(
        __name__,
        static_folder=str(BASE_DIR / "static"),
        static_url_path="/static",
    )

    # -- JSON error handlers -------------------------------------------------
    @app.errorhandler(404)
    def _not_found(_e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(405)
    def _method_not_allowed(_e):
        return jsonify({"error": "Method not allowed"}), 405

    def _get_project(pid: str):
        doc = projects.get(pid)
        if doc is None:
            return None, (jsonify({"error": "Project not found"}), 404)
        return doc, None

    # -- projects ------------------------------------------------------------
    @app.get("/api/projects")
    def api_list_projects():
        return jsonify(projects.list())

    @app.post("/api/projects")
    def api_create_project():
        data, err = _json_body()
        if err:
            return err
        title = str(data.get("title", "")).strip()
        if not title:
            return jsonify({"error": "'title' is required"}), 400
        try:
            slide_count = int(data.get("slide_count", 10))
        except (TypeError, ValueError):
            return jsonify({"error": "'slide_count' must be an integer"}), 400
        if not 3 <= slide_count <= 60:
            return jsonify({"error": "'slide_count' must be between 3 and 60"}), 400
        theme = data.get("theme", "emerald-ivory")
        if theme not in THEMES:
            return jsonify({"error": f"Unknown theme id: {theme!r}"}), 400
        provider = data.get("provider") or {}
        kind = str(provider.get("kind", "offline")).lower()
        if kind not in ("offline", "openai", "gemini", "ollama"):
            return jsonify({"error": f"Unknown provider kind: {kind!r}"}), 400
        doc = blank_project({
            "title": title,
            "instructions": data.get("instructions", ""),
            "purpose": data.get("purpose", ""),
            "audience": data.get("audience", ""),
            "knowledge_level": data.get("knowledge_level", ""),
            "slide_count": slide_count,
            "theme": theme,
            "provider": {"kind": kind, "model": str(provider.get("model", ""))},
        })
        errors = validate_project(doc)
        if errors:
            return jsonify({"error": "; ".join(errors)}), 400
        projects.save(doc)
        return jsonify(doc), 201

    @app.get("/api/projects/<pid>")
    def api_get_project(pid):
        doc, err = _get_project(pid)
        if err:
            return err
        return jsonify(doc)

    @app.put("/api/projects/<pid>")
    def api_update_project(pid):
        doc, err = _get_project(pid)
        if err:
            return err
        data, berr = _json_body()
        if berr:
            return berr
        updatable = (
            "title", "instructions", "purpose", "audience", "knowledge_level",
            "slide_count", "theme", "provider", "outline", "slides", "status",
        )
        for key in updatable:
            if key not in data:
                continue
            if key == "provider" and isinstance(data["provider"], dict):
                merged = dict(doc.get("provider") or {})
                merged.update(data["provider"])
                doc["provider"] = merged
            elif key == "theme":
                try:
                    apply_theme(doc, data["theme"])
                except ValueError as exc:
                    return jsonify({"error": str(exc)}), 400
            else:
                doc[key] = data[key]
        errors = validate_project(doc)
        if errors:
            return jsonify({"error": "; ".join(errors)}), 400
        projects.save(doc)
        return jsonify(doc)

    @app.delete("/api/projects/<pid>")
    def api_delete_project(pid):
        if not projects.delete(pid):
            return jsonify({"error": "Project not found"}), 404
        return jsonify({"ok": True})

    # -- outline & generation ------------------------------------------------
    @app.post("/api/projects/<pid>/outline")
    def api_generate_outline(pid):
        doc, err = _get_project(pid)
        if err:
            return err
        cfg = _project_cfg(doc, settings)
        brief = _brief_from_project(doc)
        try:
            if cfg["kind"] == "offline":
                outline = compose_outline_offline(brief)
            else:
                outline = providers.generate_outline(cfg, brief)
        except providers.ProviderError as exc:
            return jsonify({"error": str(exc)}), 502
        doc["outline"] = outline
        doc["status"] = "outline"
        try:
            projects.save(doc)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"outline": outline})

    @app.post("/api/projects/<pid>/generate")
    def api_generate_slides(pid):
        doc, err = _get_project(pid)
        if err:
            return err
        data, berr = _json_body(required=False)
        if berr:
            return berr
        outline = (data or {}).get("outline") or doc.get("outline") or []
        if not outline:
            return jsonify({"error": "No outline available — generate an outline first"}), 400
        doc["outline"] = outline
        try:
            theme = get_theme(doc.get("theme"))
            doc["slides"] = build_slides(doc, outline, theme)
        except Exception as exc:  # defensive: never return a half-built deck
            return jsonify({"error": f"Slide generation failed: {exc}"}), 500
        doc["status"] = "ready"
        try:
            projects.save(doc)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify(doc)

    @app.get("/api/projects/<pid>/slides/<sid>/html")
    def api_slide_html(pid, sid):
        doc, err = _get_project(pid)
        if err:
            return err
        slide = next((s for s in doc.get("slides", []) if s.get("id") == sid), None)
        if slide is None:
            return jsonify({"error": "Slide not found"}), 404
        theme = get_theme(doc.get("theme"))
        return jsonify({"html": render_slide_html(slide, theme)})

    # -- export (exporter modules written by another agent; lazy import) -----
    @app.post("/api/projects/<pid>/export")
    def api_export(pid):
        doc, err = _get_project(pid)
        if err:
            return err
        data, berr = _json_body()
        if berr:
            return berr
        fmt = str(data.get("format", "")).lower()
        if fmt not in ("pptx", "pdf", "html"):
            return jsonify({"error": "'format' must be one of: pptx, pdf, html"}), 400

        module_name = f"export_{fmt}"
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            return jsonify({"error": "exporter not installed"}), 501
        export_fn = getattr(module, module_name, None) or getattr(module, "export", None)
        if not callable(export_fn):
            return jsonify({"error": f"exporter module '{module_name}' has no export function"}), 500

        out_dir = root / "exports" / doc["id"]
        out_dir.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^a-z0-9]+", "-", (doc.get("title") or "deck").lower()).strip("-")[:50] or "deck"
        filename = f"{slug}-{doc['id']}.{fmt}"
        out_file = out_dir / filename
        theme = get_theme(doc.get("theme"))
        # Exporter convention: fn(project, theme, out_file_path) -> {"ok", "checks"}.
        try:
            try:
                result = export_fn(doc, theme, str(out_file))
            except TypeError:
                # Fall back to a simpler (project, out_dir) signature.
                result = export_fn(doc, str(out_dir))
        except Exception as exc:
            return jsonify({"error": f"Export failed: {exc}"}), 500

        validation = result if isinstance(result, dict) else {}
        if not out_file.exists():
            detail = ""
            if isinstance(validation, dict) and not validation.get("ok", True):
                failed = [c for c in validation.get("checks", []) if not c.get("passed")]
                detail = "; ".join(c.get("detail", c.get("name", "")) for c in failed[:3])
            return jsonify({"error": f"Exporter did not produce the file: {filename}"
                                     + (f" ({detail})" if detail else "")}), 500

        return jsonify({
            "ok": True,
            "filename": filename,
            "validation": validation,
            "download_url": f"/api/download/{doc['id']}/{fmt}",
        })

    @app.get("/api/download/<pid>/<fmt>")
    def api_download(pid, fmt):
        fmt = fmt.lower()
        if fmt not in ("pptx", "pdf", "html"):
            return jsonify({"error": "Unknown format"}), 404
        out_dir = root / "exports" / pid
        if not out_dir.is_dir():
            return jsonify({"error": "No exports found for this project"}), 404
        candidates = sorted(
            out_dir.glob(f"*.{fmt}"), key=lambda p: p.stat().st_mtime, reverse=True
        )
        if not candidates:
            return jsonify({"error": "No exports found for this project"}), 404
        return send_file(candidates[0], as_attachment=True,
                         download_name=candidates[0].name)

    # -- themes & layouts ----------------------------------------------------
    @app.get("/api/themes")
    def api_themes():
        return jsonify(list_themes())

    @app.get("/api/layouts")
    def api_layouts():
        return jsonify([{"id": lid, "name": l["name"]} for lid, l in LAYOUTS.items()])

    # -- settings ------------------------------------------------------------
    @app.get("/api/settings")
    def api_get_settings():
        # Public view only: configured flags + base_url/model, never api keys.
        return jsonify(settings.public_view())

    @app.post("/api/settings")
    def api_set_settings():
        data, err = _json_body()
        if err:
            return err
        provider = str(data.get("provider", "")).lower()
        if provider not in ("openai", "gemini", "ollama"):
            return jsonify({"error": "'provider' must be one of: openai, gemini, ollama"}), 400
        config = data.get("config")
        if not isinstance(config, dict):
            return jsonify({"error": "'config' must be an object"}), 400
        try:
            entry = settings.set_provider(provider, config)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"ok": True, "configured": bool(entry.get("configured"))})

    @app.post("/api/settings/test")
    def api_test_settings():
        data, err = _json_body()
        if err:
            return err
        provider = str(data.get("provider", "")).lower()
        if provider not in ("openai", "gemini", "ollama"):
            return jsonify({"error": "'provider' must be one of: openai, gemini, ollama"}), 400
        stored = settings.get()["providers"].get(provider, {})
        if provider == "offline" or not stored.get("configured"):
            return jsonify({"ok": False,
                            "error": f"'{provider}' provider is not configured — add credentials in Settings."})
        cfg = {
            "kind": provider,
            "model": stored.get("model", ""),
            "api_key": stored.get("api_key", ""),
            "base_url": stored.get("base_url", ""),
        }
        try:
            providers.test_connection(cfg)
        except providers.ProviderError as exc:
            return jsonify({"ok": False, "error": str(exc)})
        return jsonify({"ok": True})

    # -- AI assist -----------------------------------------------------------
    @app.post("/api/assist")
    def api_assist():
        data, err = _json_body()
        if err:
            return err
        project_id = data.get("project_id")
        slide_id = data.get("slide_id")
        task = data.get("task")
        instruction = data.get("instruction", "")
        if not project_id or not slide_id:
            return jsonify({"error": "'project_id' and 'slide_id' are required"}), 400
        if task not in ("improve", "relayout"):
            return jsonify({"error": "'task' must be 'improve' or 'relayout'"}), 400

        doc, perr = _get_project(project_id)
        if perr:
            return perr
        cfg = _project_cfg(doc, settings)
        if cfg["kind"] == "offline":
            return jsonify({"error": _OFFLINE_ASSIST_MSG}), 400
        stored = settings.get()["providers"].get(cfg["kind"], {})
        if not stored.get("configured"):
            return jsonify({"error": f"'{cfg['kind']}' provider is not configured — add credentials in Settings."}), 400

        slide = next((s for s in doc.get("slides", []) if s.get("id") == slide_id), None)
        if slide is None:
            return jsonify({"error": "Slide not found"}), 404
        summary = _slide_summary(slide)
        brief = _brief_from_project(doc)

        try:
            if task == "improve":
                content = providers.generate_slide_content(cfg, brief, {
                    "title": summary["title"],
                    "bullets": summary["bullets"],
                    "notes": summary["notes"],
                    "instruction": instruction,
                })
                for el in slide.get("elements", []):
                    if el.get("type") == "text" and el.get("role") == "title":
                        el["text"] = content["title"]
                        break
                for el in slide.get("elements", []):
                    if el.get("type") == "text" and el.get("role") == "bullets":
                        el["text"] = "\n".join(f"• {b}" for b in content["bullets"])
                        break
                slide["notes"] = content["notes"]
            else:  # relayout — ask the provider to pick the best layout, then rebuild
                hint_list = ", ".join(sorted(LAYOUTS))
                picked = providers.generate_json(
                    cfg,
                    "You are a presentation designer. Return ONLY valid JSON — no markdown.",
                    f"Slide title: {summary['title']}\nBullets:\n"
                    + "".join(f"- {b}\n" for b in summary["bullets"])
                    + (f"\nUser instruction: {instruction}\n" if instruction else "")
                    + f"\nChoose the best layout_hint for this slide from: {hint_list}. "
                      'Return {"layout_hint": "<id>"}.',
                )
                hint = picked.get("layout_hint") if isinstance(picked, dict) else None
                if hint not in LAYOUTS or hint == slide.get("layout"):
                    from generator import _ALT_LAYOUT  # internal fallback map
                    hint = _ALT_LAYOUT.get(slide.get("layout"), "title-content")
                rebuilt = build_slides(
                    doc,
                    [{
                        "title": summary["title"] or "Untitled",
                        "bullets": summary["bullets"],
                        "layout_hint": hint,
                        "notes": summary["notes"],
                    }],
                    get_theme(doc.get("theme")),
                )[0]
                rebuilt["id"] = slide["id"]  # keep the slide's identity
                idx = doc["slides"].index(slide)
                doc["slides"][idx] = rebuilt
                slide = rebuilt
        except providers.ProviderError as exc:
            return jsonify({"error": str(exc)}), 502

        try:
            projects.save(doc)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"slide": slide})

    # -- sample --------------------------------------------------------------
    @app.post("/api/sample")
    def api_sample():
        doc = build_sample_project()
        projects.save(doc)
        return jsonify({"id": doc["id"]}), 201

    # -- frontend ------------------------------------------------------------
    @app.get("/")
    def index():
        index_path = BASE_DIR / "static" / "index.html"
        if index_path.exists():
            return send_from_directory(str(BASE_DIR / "static"), "index.html")
        # Placeholder until the frontend agent ships index.html.
        return (
            "<html><head><title>Aesthetic AI Studio</title></head>"
            "<body style='font-family:sans-serif;padding:40px'>"
            "<h1>Aesthetic AI Studio v1</h1>"
            "<p>Backend is running. The frontend (static/index.html) is not installed yet.</p>"
            "<p>API: <code>/api/projects</code> · <code>/api/themes</code> · "
            "<code>/api/layouts</code> · <code>/api/settings</code></p>"
            "</body></html>"
        )

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=4321)
