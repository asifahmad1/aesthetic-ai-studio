# ARCHITECTURE — Aesthetic AI Studio v1

## 1. What it is

A local Flask web app that generates slide presentations from a short
brief. Pipeline: **brief → outline → slides → edit → export**.
Everything runs on the user's machine; AI providers are optional
plug-ins. Projects persist as plain JSON under `data/`.

Port **4321**. Entry point: `python app.py` → `create_app(data_root=None)`.

## 2. Components

| Module | Owner | Responsibility |
|---|---|---|
| `app.py` | backend agent | Flask app factory `create_app(data_root=None)`; REST routes; wires store + generator + exporters. Lazily imports `export_pptx` / `export_pdf` / `export_html` inside the export route. |
| `schema.py` | backend agent | Slide-document model; `validate_project(doc) -> [errors]`; `blank_project(params) -> dict`. |
| `store.py` | backend agent | JSON persistence: load/save/list/delete projects under `data/projects/`; exports under `data/exports/`. |
| `themes.py` | backend agent | `THEMES` dict (6 ids), `get_theme(id)`, `list_themes()`. |
| `providers.py` | backend agent | Optional AI provider adapters (OpenAI/Anthropic/Gemini/Ollama); offline fallback. |
| `generator.py` | backend agent | `LAYOUTS` (13 ids); `compose_outline_offline(brief) -> outline`; `build_slides(project, outline, theme) -> slides`. |
| `sample.py` | backend agent | `build_sample_project()` — 30-slide food-safety deck, dark-green-gold, status `ready`. |
| `render.py` | frontend agent | `render_slide_html(slide, theme) -> str`; `render_deck_html(project, theme) -> str` (used by web UI and preferred by `export_html`). |
| `static/` | frontend agent | CSS/JS for the editor UI (outline editor, slide canvas, theme picker, export dialog). |
| `export_pptx.py` | **this agent** | Native editable PPTX export + self-validation (see §5). |
| `export_pdf.py` | **this agent** | reportlab PDF export + pypdf validation (see §5). |
| `export_html.py` | **this agent** | Standalone HTML export + validation; prefers `render.render_deck_html`, falls back to its own builder (see §5). |
| `tests/` | **this agent** | pytest suite: export validity, contract conformance, API round-trip. |
| `Start-Windows.cmd` / `start.sh` | **this agent** | One-click launchers (venv bootstrap, pip install, browser open). |

## 3. Data model (contract)

**Canvas:** every slide is a 1000 × 562.5 coordinate space (16:9).

```
project {
  id, title, instructions, purpose, audience, knowledge_level,
  slide_count, theme: "<theme-id>", slide_size: "16:9",
  provider: { kind, model }, status,            # draft|outline|building|ready
  outline: [...], slides: [...],
  created, updated                              # ISO timestamps
}

slide  { id, layout, elements: [...], notes }
element {
  id, type: "text"|"shape"|"table"|"image",
  role,            # e.g. title, subtitle, heading, body, caption, kicker…
  text,            # may contain \n; lines starting "• "/"- " are bullets
  shape,           # rect|roundrect|oval|line|diamond|triangle…
  rows,            # table: list of rows, each a list of cell strings
  alt, prompt,     # image: alt text + generation prompt (placeholder in v1)
  x, y, w, h,      # canvas coords (floats)
  fill, line,      # hex colors for shapes
  text_color, font_size, bold, align
}

theme {
  name, primary, secondary, accent, background, surface,
  text, muted, chart[5], heading_font, body_font
}
```

**Theme ids:** `emerald-ivory`, `forest-cream`, `dark-green-gold`,
`navy-white`, `charcoal-gold`, `pastel-academic`.

**Layout ids (13):** `cover`, `title-content`, `two-column`,
`three-column`, `big-quote`, `stats-dashboard`, `timeline`,
`split-image-text`, `section-divider`, `comparison`, `checklist`,
`references`, `thank-you`.

## 4. API reference

Exact routes live in `app.py` (backend agent). The REST surface the app
and tests are built around:

| Method | Route | Purpose |
|---|---|---|
| POST | `/api/projects` | Create project from brief params → `{project}` (201) |
| GET | `/api/projects` | List projects |
| GET | `/api/projects/<id>` | Read one project (404 if missing) |
| PUT/PATCH | `/api/projects/<id>` | Update project fields |
| DELETE | `/api/projects/<id>` | Delete project |
| GET | `/api/projects/<id>/export/pptx` | Validated `.pptx` download |
| GET | `/api/projects/<id>/export/pdf` | Validated `.pdf` download |
| GET | `/api/projects/<id>/export/html` | Validated `.html` download |

The export routes lazily import the exporter modules
(`from export_pptx import export_pptx` etc.), call
`export_*(project, theme, out_path)`, and serve the file only when the
returned validation dict has `"ok": true`.

## 5. Export pipeline (this agent's modules)

All three exporters share one contract:

```
export_*(project: dict, theme: dict, out_path: str)
    -> {"ok": bool, "checks": [{"name": str, "passed": bool, "detail": str}]}
```

`"ok"` is true **only if every check passed** — exporters never claim
success falsely. On exception they return `ok: False` with the traceback
summary in the check detail.

**PPTX (`export_pptx.py`, python-pptx):**
canvas → inches via `in_x = x/1000*13.333`, `in_y = y/562.5*7.5`; slide
size 13.333×7.5 in on the blank layout. `text` → `add_textbox` with
paragraphs (`• `/`- ` lines → level-0 bullets, kept visible with the `•`
glyph); heading roles use the theme heading font. `shape`
rect/roundrect/oval → `add_shape` with fill/line colors; `line` →
`add_connector`. `table` → `add_table` with bold white-on-primary header
row. `image` → labeled placeholder rectangle ("🖼 alt / (image
placeholder)") — v1 never embeds pictures. Notes → `notes_slide`.
Checks: file >10KB, reopens, slide count matches, ≥1 shape per slide,
title text present, layouts all known, native text present.

**PDF (`export_pdf.py`, reportlab + pypdf):**
landscape pages 960×540 pt; background rect; shapes as rects/ellipses;
text with manual word-wrap via `stringWidth`; tables as grids; image
placeholders as boxes. Font mapping: Georgia→Times-Roman(/Bold),
Trebuchet MS→Helvetica-Bold, Calibri/Arial→Helvetica(/Bold) — built-in
PDF fonts, no embedding. Checks: file >10KB, `%PDF` header, pypdf page
count == slide count.

**HTML (`export_html.py`):**
uses `render.render_deck_html(project, theme)` when available, else a
built-in standalone builder (inline CSS, `aspect-ratio: 16/9` slides,
`<section class="slide">` per slide, notes in `<details>`). Checks: file
>5KB, ≥1 `<section>` per slide, all slide titles present.

## 6. Module map (import graph)

```
app.py ──► schema.py ──► (validation)
   ├─────► store.py ───► data/projects/*.json
   ├─────► themes.py
   ├─────► providers.py ──► (optional network)
   ├─────► generator.py ──► LAYOUTS
   ├─────► sample.py ──► generator, themes, schema
   ├─────► render.py ──► themes
   └─────► export_pptx.py ──┐
           export_pdf.py  ──┼──► (lazy imports inside export route)
           export_html.py ──┘         └─► render.py (preferred) or builtin
tests/ ──► export_*.py (+ fixtures)
       ──► schema, themes, generator, sample, app  (defensive; skip if absent)
```

No exporter imports any sibling module at top level — `export_html`
imports `render` lazily inside the function so exports work even if the
UI layer is absent.

## 7. Testing

```bash
python -m pytest tests/ -q
```

- `test_exports.py` — export validity against local fixtures (no sibling
  modules needed): pptx reopens with python-pptx, native text (no
  pictures/screenshots), tables/bullets/notes survive, pdf page count via
  pypdf, HTML contains every slide title and is standalone, validation
  dict structure, honest failure reporting.
- `test_contract.py` — schema valid/invalid, offline outline shape
  (cover-first, thank-you-last), build_slides count + layout variety, all
  6 themes' keys, sample deck (30 slides, tables, checklists, notes).
  Skips gracefully if a sibling module is missing.
- `test_api.py` — Flask test-client CRUD round-trip
  (create→get→update→delete) with defensive route discovery, plus export
  endpoint checks. Uses `tmp_path` as `data_root`.
