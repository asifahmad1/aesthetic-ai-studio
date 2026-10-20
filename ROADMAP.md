# ROADMAP — Aesthetic AI Studio

The product vision is a full AI presentation studio (the 29-section vision
doc covers brief intake, multi-agent drafting, brand kits, asset libraries,
review workflows, analytics, and publishing). This roadmap maps that vision
onto build phases — honestly, starting with what v1 actually ships.

## v1 — Local foundation (this release)

- Guided workflow: brief → outline → build → edit → export
- Offline-first outline composer + layout engine (no key required)
- Optional AI provider plug-ins (OpenAI / Anthropic / Gemini / Ollama)
- 13 layouts, 6 themes, speaker notes
- Native editable PPTX export with self-validation
- PDF export (16:9, validated page count)
- Standalone HTML export
- 30-slide sample deck (food-safety, dark-green-gold)
- JSON project storage under `data/`; one-click Windows/macOS launchers
- pytest suite: exports, contract, API

## v1.1 — Polish (next)

- Undo/redo in the slide editor
- Drag-to-resize elements on the canvas
- Per-element theme overrides remembered across rebuilds
- Export presets (e.g. "print PDF" with notes pages)
- Import an existing outline from Markdown

## v2 — Smarter generation

- Provider-backed section drafting with citations
- Brand kit: save your own theme (logo, fonts, palette)
- Asset library: reuse images/icons across decks
- Multi-language decks

## v3 — Teams & publishing

- Share links, comments, version history
- One-click publish to the web / LMS embed
- Usage analytics per deck

---

## Explicitly NOT in v1 (honest scope)

These are real parts of the vision, deliberately deferred — not silently
missing:

1. **Multi-agent orchestration beyond the pipeline** — v1 runs one
   deterministic pipeline (outline → slides). No researcher/writer/critic
   agent teams, no debate loops.
2. **Template marketplace** — no browsing, buying, or sharing templates;
   the 13 built-in layouts and 6 themes are the whole catalog.
3. **Collaboration / cloud** — single user, local files only. No accounts,
   no simultaneous editing, no cloud sync or backup.
4. **Animations & transitions** — slides are static. No entrance
   animations, morphs, or timed builds.
5. **PPT import / redesign** — v1 only creates new decks; it cannot open
   an existing `.pptx` and restyle it.
6. **Real image generation / stock photos** — `image` elements export as
   labeled placeholders. No DALL-E/Midjourney calls, no stock library.
7. **Charts from data** — `stats-dashboard` is a layout with styled
   stat blocks, not live charts; paste your own chart as an image
   placeholder or build it in PowerPoint after export.
8. **ODP / MP4 / GIF exports** — v1 exports PPTX, PDF, and HTML only.
9. **Speaker-notes PDF handouts** — notes live in the PPTX notes pane and
   in collapsible HTML sections; there is no separate handout layout yet.
10. **Accessibility checker** — contrast/reading-order checks are on the
    v1.1 list, not in v1.

If you were promised any of the above for v1, that promise was wrong —
this list is the correction.
