# Aesthetic AI Studio v1

A **local, private AI presentation generator** that runs entirely on your own
computer. Describe the presentation you want — topic, audience, number of
slides — and it drafts an outline, builds fully editable slides in six
designer themes, and exports to **PowerPoint (.pptx)**, **PDF**, or a
standalone **HTML** file. No account, no cloud, no subscription: your content
never leaves your machine (unless you plug in an AI provider key, which is
optional).

**Creator:** Dr. Asif Ahmad

---

## Features

- **Guided 4-step workflow** — New presentation → outline review → slide
  build → edit → export. You stay in control at every step.
- **Offline-first generation** — works with zero configuration using the
  built-in outline composer and layout engine. Optional AI providers
  (OpenAI / Anthropic / Gemini / Ollama / local) can be plugged in via
  Settings for smarter drafting.
- **13 slide layouts** — cover, title-content, two-column, three-column,
  big-quote, stats-dashboard, timeline, split-image-text, section-divider,
  comparison, checklist, references, thank-you.
- **6 curated themes** — emerald-ivory, forest-cream, dark-green-gold,
  navy-white, charcoal-gold, pastel-academic. Every theme defines fonts,
  colors, and a 5-color chart palette.
- **Native editable PPTX export** — real text boxes, shapes, and tables
  (never screenshots), with speaker notes on every slide. Each export is
  self-validated: slide count, native text, and known layouts are checked
  before the file is handed to you.
- **PDF export** — 16:9 landscape pages with wrapped text, table grids,
  and image placeholders; page count validated with pypdf.
- **Standalone HTML export** — one file, inline CSS, works offline in any
  browser.
- **30-slide sample deck** — a food-safety workshop deck in dark-green-gold
  ships with the app so you can try every feature in one click.
- **Autosave projects** — everything is stored as JSON under `data/`;
  delete or back up a folder and you're done.

## Quick start

**Windows (easiest):** double-click `Start-Windows.cmd`.
First run creates a private Python environment and installs packages
automatically, then opens http://127.0.0.1:4321 in your browser.

**macOS / Linux:** run `bash start.sh` in a terminal.

Manual start (any OS):

```bash
python -m venv venv
venv/Scripts/activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
python app.py
```

Then open **http://127.0.0.1:4321**.

New to this? Read **[EASY-SETUP.md](EASY-SETUP.md)** — a beginner's guide
that assumes no technical knowledge.

## How to use (60 seconds)

1. Click **New Presentation**, enter a title, audience, and slide count.
2. Review the generated **outline** — reorder or reword items.
3. Click **Build Slides** — the app composes every slide from the outline.
4. **Edit** any text, swap the theme, add speaker notes.
5. **Export** to PPTX, PDF, or HTML. Each export shows a validation report
   so you know the file is good before you download it.

## Project layout

```
aesthetic-ai-studio/
├── app.py              # Flask app: routes, project store wiring
├── schema.py           # slide-document model + validation
├── store.py            # JSON persistence under data/
├── themes.py           # 6 themes, get_theme()/list_themes()
├── providers.py        # AI provider adapters (optional keys)
├── generator.py        # outline composer + slide builder, 13 layouts
├── sample.py           # 30-slide food-safety sample deck
├── render.py           # HTML rendering of slides/decks
├── export_pptx.py      # native editable PPTX export + validation
├── export_pdf.py       # reportlab PDF export + pypdf validation
├── export_html.py      # standalone HTML export + validation
├── static/             # CSS/JS for the web UI
├── tests/              # pytest suite (exports, contract, API)
├── data/               # your projects + exports (created at runtime)
├── Start-Windows.cmd   # Windows one-click launcher
├── start.sh            # macOS/Linux launcher
└── requirements.txt    # pinned dependencies
```

See **[ARCHITECTURE.md](ARCHITECTURE.md)** for the data model and API
reference, and **[ROADMAP.md](ROADMAP.md)** for what v1 does and does not
include.

## Requirements

- Python 3.10 or newer
- Internet only for the first-run package install (and optional AI providers)

## License

For personal use by Dr. Asif Ahmad.
