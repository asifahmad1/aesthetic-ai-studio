"""Slide composition engine for Aesthetic AI Studio v1.

- LAYOUTS: the 13 supported layout ids (name + description each).
- compose_outline_offline(brief): deterministic outline builder (no AI needed).
- build_slides(project, outline, theme): turns outline items into slides with
  per-layout element builders on the 1000 x 562.5 canvas.
- apply_theme(project, theme_id): switch a project's theme id.

Rules enforced in build_slides:
- the same layout is never used on two consecutive slides (a compatible
  alternate is substituted);
- the first slide is always 'cover', the last always 'thank-you'.

Color note: builders set explicit colors only for decorative shapes (accent
bars, card fills) and semantic text roles (kickers, stat values). Ordinary
text keeps text_color=None so colors resolve at render time from the current
theme plus any element override.
"""

from __future__ import annotations

import re

from schema import CANVAS_H, new_id
from themes import get_theme

LAYOUTS: dict[str, dict] = {
    "cover": {"name": "Cover",
              "description": "Opening slide: kicker, large title, subtitle, accent bar."},
    "title-content": {"name": "Title & Content",
                      "description": "Title with accent underline plus a bullet list; "
                                     "supports an optional data table."},
    "two-column": {"name": "Two Column",
                   "description": "Title plus two headed panels side by side."},
    "three-column": {"name": "Three Column",
                     "description": "Title plus three headed panels across the slide."},
    "big-quote": {"name": "Big Quote",
                  "description": "Large centered quotation with attribution."},
    "stats-dashboard": {"name": "Stats Dashboard",
                        "description": "Three stat cards, each with a big value and a label."},
    "timeline": {"name": "Timeline",
                 "description": "Sequential milestone boxes across the slide."},
    "split-image-text": {"name": "Split Image & Text",
                         "description": "Image placeholder on the left, headed bullets on the right."},
    "section-divider": {"name": "Section Divider",
                        "description": "Centered section title used to open a new part."},
    "comparison": {"name": "Comparison",
                   "description": "Two headed panels contrasting A vs B."},
    "checklist": {"name": "Checklist",
                  "description": "Title plus checkbox-style bullet list."},
    "references": {"name": "References",
                   "description": "Title plus a numbered reference list."},
    "thank-you": {"name": "Thank You",
                  "description": "Closing slide: big thanks, discussion prompt, creator credit."},
}

# Compatible alternate used when a layout_hint would repeat consecutively.
_ALT_LAYOUT = {
    "cover": "section-divider",
    "section-divider": "title-content",
    "title-content": "two-column",
    "two-column": "title-content",
    "three-column": "two-column",
    "big-quote": "title-content",
    "stats-dashboard": "three-column",
    "timeline": "two-column",
    "split-image-text": "two-column",
    "comparison": "two-column",
    "checklist": "title-content",
    "references": "title-content",
    "thank-you": "section-divider",
}

_CREDIT = "Created by Dr. Asif Ahmad"


# ---------------------------------------------------------------------------
# element helpers
# ---------------------------------------------------------------------------

def _el(eid: str, etype: str, x, y, w, h, **kw) -> dict:
    e = {
        "id": eid, "type": etype,
        "x": float(x), "y": float(y), "w": float(w), "h": float(h),
        "fill": None, "line": None, "text_color": None,
        "font_size": None, "bold": False, "align": "left",
    }
    e.update(kw)
    return e


def _t(role, text, x, y, w, h, size=None, bold=False, align="left", color=None) -> dict:
    return _el(new_id("e_"), "text", x, y, w, h, role=role, text=str(text),
               font_size=size, bold=bold, align=align, text_color=color)


def _shape(shape, x, y, w, h, fill=None, line=None) -> dict:
    return _el(new_id("e_"), "shape", x, y, w, h, shape=shape, fill=fill, line=line)


def _table(rows, x, y, w, h, size=18) -> dict:
    return _el(new_id("e_"), "table", x, y, w, h, rows=rows, font_size=size)


def _img(alt, prompt, x, y, w, h) -> dict:
    return _el(new_id("e_"), "image", x, y, w, h, alt=str(alt), prompt=str(prompt))


def _title_block(item: dict, th: dict, y: int = 56) -> list[dict]:
    """Standard title + accent underline used by most content layouts."""
    return [
        _t("title", item.get("title", ""), 60, y, 880, 92, size=40, bold=True),
        _shape("rect", 62, y + 100, 72, 7, fill=th["accent"]),
    ]


def _bullets_text(bullets: list[str], marker: str = "• ") -> str:
    return "\n".join(f"{marker}{b}" for b in bullets)


# ---------------------------------------------------------------------------
# per-layout builders: fn(project, item, theme) -> [elements]
# ---------------------------------------------------------------------------

def _b_cover(project, item, th) -> list[dict]:
    kicker = project.get("purpose") or project.get("audience") or "Presentation"
    subtitle = ""
    if item.get("bullets"):
        subtitle = item["bullets"][0]
    if not subtitle:
        subtitle = (project.get("instructions") or "")[:160]
    return [
        _shape("rect", 60, 176, 90, 10, fill=th["accent"]),
        _t("kicker", str(kicker).upper(), 60, 200, 880, 36,
           size=22, bold=True, color=th["accent"]),
        _t("title", item.get("title", ""), 60, 244, 880, 140, size=54, bold=True),
        _t("subtitle", subtitle, 60, 392, 880, 72, size=24, color=th["muted"]),
        _t("caption", _CREDIT, 60, 506, 880, 30, size=16,
           align="center", color=th["muted"]),
    ]


def _b_title_content(project, item, th) -> list[dict]:
    els = _title_block(item, th)
    y = 190
    bullets = item.get("bullets") or []
    table = item.get("table")
    if bullets and table:
        # Compact intro bullets so the table fits below them on the canvas.
        els.append(_t("bullets", _bullets_text(bullets), 60, y, 880, 100, size=19))
        y += 26 + len(bullets) * 30
    elif bullets:
        els.append(_t("bullets", _bullets_text(bullets), 60, y, 880, 300, size=22))
        y += 44 + len(bullets) * 36
    if table:
        rows = [table["headers"]] + table["rows"] if isinstance(table, dict) else table
        available = CANVAS_H - 20 - y
        h = max(120.0, min(320.0, available))
        els.append(_table(rows, 60, y, 880, h, size=18))
    return els


def _column_panels(item, th, columns: list[str], bullets: list[str],
                   n: int, marker: str = "• ") -> list[dict]:
    els = _title_block(item, th)
    gap = 24
    margin = 60
    w = (1000 - 2 * margin - (n - 1) * gap) / n
    y, h = 200, 320
    chunks = [bullets[i::n] for i in range(n)]  # round-robin keeps balance
    for i in range(n):
        x = margin + i * (w + gap)
        head = columns[i] if i < len(columns) else f"Part {i + 1}"
        els.append(_shape("roundrect", x, y, w, h, fill=th["surface"], line=th["muted"]))
        els.append(_t("heading", head, x + 20, y + 18, w - 40, 44,
                     size=23, bold=True, color=th["primary"]))
        if chunks[i]:
            els.append(_t("bullets", _bullets_text(chunks[i], marker),
                         x + 20, y + 70, w - 40, h - 90, size=19))
    return els


def _b_two_column(project, item, th) -> list[dict]:
    cols = item.get("columns") or ["Key Concepts", "Practical Notes"]
    return _column_panels(item, th, cols, item.get("bullets") or [], 2)


def _b_three_column(project, item, th) -> list[dict]:
    cols = item.get("columns") or ["Part 1", "Part 2", "Part 3"]
    return _column_panels(item, th, cols, item.get("bullets") or [], 3)


def _b_big_quote(project, item, th) -> list[dict]:
    bullets = item.get("bullets") or []
    quote = bullets[0] if bullets else item.get("title", "")
    attr = bullets[1] if len(bullets) > 1 else ""
    return [
        _t("quote", "\u201c", 60, 110, 880, 100, size=96,
           color=th["accent"], align="center"),
        _t("quote", quote, 130, 205, 740, 220, size=32, align="center"),
        _t("caption", attr, 130, 435, 740, 44, size=20,
           align="center", color=th["muted"]),
    ]


def _b_stats_dashboard(project, item, th) -> list[dict]:
    els = _title_block(item, th)
    bullets = list((item.get("bullets") or [])[:3])
    while len(bullets) < 3:
        bullets.append("")
    xs = [40, 360, 680]
    for i, b in enumerate(bullets):
        x = xs[i]
        match = re.search(r"\d[\d,]*\.?\d*", b)
        value = match.group(0) if match else "\u2014"
        low = b.lower()
        for word in ("million", "billion", "thousand"):
            if word in low and word not in value.lower():
                value += " " + word
                break
        if "%" in b and "%" not in value:
            value += "%"
        els.append(_shape("roundrect", x, 215, 280, 250,
                          fill=th["surface"], line=th["accent"]))
        els.append(_t("stat-value", value, x + 20, 245, 240, 80,
                     size=52, bold=True, align="center", color=th["primary"]))
        if b:
            els.append(_t("stat-label", b, x + 20, 340, 240, 105,
                         size=18, align="center", color=th["muted"]))
    return els


def _b_timeline(project, item, th) -> list[dict]:
    els = _title_block(item, th)
    bullets = item.get("bullets") or []
    n = min(max(len(bullets), 1), 7)
    steps = (bullets + [""] * n)[:n]
    gap, margin = 16, 40
    w = (1000 - 2 * margin - (n - 1) * gap) / n
    y, h = 245, 235
    for i, step in enumerate(steps):
        x = margin + i * (w + gap)
        els.append(_shape("roundrect", x, y, w, h, fill=th["surface"], line=th["primary"]))
        els.append(_t("heading", f"Step {i + 1}", x + 10, y + 14, w - 20, 34,
                     size=19, bold=True, color=th["primary"], align="center"))
        if step:
            els.append(_t("body", step, x + 10, y + 56, w - 20, h - 70,
                         size=16, align="center"))
    return els


def _b_split_image_text(project, item, th) -> list[dict]:
    els = _title_block(item, th)
    bullets = item.get("bullets") or []
    els.append(_img(item.get("title", "Illustration"),
                    f"Illustration for: {item.get('title', '')}",
                    60, 210, 400, 300))
    els.append(_t("heading", "Highlights", 505, 210, 435, 40,
                 size=24, bold=True, color=th["primary"]))
    if bullets:
        els.append(_t("bullets", _bullets_text(bullets), 505, 258, 435, 252, size=20))
    return els


def _b_section_divider(project, item, th) -> list[dict]:
    return [
        _t("kicker", "SECTION", 60, 190, 880, 40, size=22, bold=True,
           color=th["accent"], align="center"),
        _shape("rect", 460, 242, 80, 8, fill=th["accent"]),
        _t("title", item.get("title", ""), 60, 262, 880, 150,
           size=52, bold=True, align="center"),
        _t("caption", project.get("title", ""), 60, 420, 880, 40, size=18,
           align="center", color=th["muted"]),
    ]


def _b_comparison(project, item, th) -> list[dict]:
    title = item.get("title", "")
    cols = item.get("columns")
    if not cols:
        for sep in (" vs ", " Vs ", " VS ", " and ", " & ", " / "):
            if sep in title:
                cols = [p.strip() for p in title.split(sep, 1)]
                break
        else:
            cols = ["Current State", "Desired State"]
    return _column_panels(item, th, cols, item.get("bullets") or [], 2, marker="✓ ")


def _b_checklist(project, item, th) -> list[dict]:
    els = _title_block(item, th)
    bullets = item.get("bullets") or []
    if bullets:
        els.append(_t("bullets", _bullets_text(bullets, marker="☑ "),
                     60, 195, 880, 330, size=22))
    return els


def _b_references(project, item, th) -> list[dict]:
    els = _title_block(item, th)
    bullets = item.get("bullets") or []
    numbered = "\n".join(f"{i + 1}. {b}" for i, b in enumerate(bullets))
    if numbered:
        els.append(_t("body", numbered, 60, 195, 880, 330, size=18))
    return els


def _b_thank_you(project, item, th) -> list[dict]:
    return [
        _t("title", item.get("title") or "Thank You", 60, 170, 880, 100,
           size=64, bold=True, align="center"),
        _t("subtitle", "Questions & Discussion", 60, 280, 880, 60,
           size=28, align="center", color=th["muted"]),
        _shape("rect", 460, 360, 80, 8, fill=th["accent"]),
        _t("caption", _CREDIT, 60, 506, 880, 30, size=16,
           align="center", color=th["muted"]),
    ]


_BUILDERS = {
    "cover": _b_cover,
    "title-content": _b_title_content,
    "two-column": _b_two_column,
    "three-column": _b_three_column,
    "big-quote": _b_big_quote,
    "stats-dashboard": _b_stats_dashboard,
    "timeline": _b_timeline,
    "split-image-text": _b_split_image_text,
    "section-divider": _b_section_divider,
    "comparison": _b_comparison,
    "checklist": _b_checklist,
    "references": _b_references,
    "thank-you": _b_thank_you,
}


def _resolve_layout(hint: str | None, prev: str | None) -> str:
    """Normalize a layout hint and avoid repeating the previous layout."""
    if hint not in LAYOUTS:
        hint = "title-content"
    if hint == prev:
        hint = _ALT_LAYOUT.get(hint, "title-content")
    return hint


# ---------------------------------------------------------------------------
# offline outline composer
# ---------------------------------------------------------------------------

_DEFAULT_SECTIONS = [
    "Background & Key Concepts",
    "Core Principles",
    "Methods & Best Practices",
    "Practical Applications",
    "Challenges & Solutions",
]

_MIDDLE_LAYOUT_ROTATION = [
    "title-content", "two-column", "checklist", "comparison",
    "split-image-text", "big-quote", "three-column", "stats-dashboard",
    "timeline",
]


def _derive_sections(instructions: str) -> list[str]:
    """Pull candidate section titles out of the instructions text.

    Falls back to a generic 5-section arc when the instructions do not
    contain enough usable phrases.
    """
    candidates: list[str] = []
    for chunk in re.split(r"[\n;]+", instructions or ""):
        s = chunk.strip(" \t-•*–—0123456789.()\"'")
        words = s.split()
        if (
            2 <= len(words) <= 7
            and len(s) < 80
            and s[:1].isupper()
            and not s.endswith((".", "?", "!", ":"))
        ):
            s = s[0].upper() + s[1:]
            if s not in candidates:
                candidates.append(s)
    if len(candidates) >= 3:
        return candidates[:6]
    return list(_DEFAULT_SECTIONS)


def _section_bullets(section: str, brief: dict) -> list[str]:
    title = (brief.get("title") or "this presentation").strip()
    audience = (brief.get("audience") or "the audience").strip()
    knowledge = (brief.get("knowledge_level") or "").strip()
    instructions = (brief.get("instructions") or "").strip()
    focus = instructions[:120] + ("…" if len(instructions) > 120 else "")
    level = f" at a {knowledge.lower()} level" if knowledge else ""
    bullets = [
        f"What {section.lower()} covers and why it matters for {title.lower()}",
        f"Core ideas every {audience.lower()} should understand{level}",
    ]
    if focus:
        bullets.append(f"How {section.lower()} connects to the session goals: {focus}")
    else:
        bullets.append(f"How {section.lower()} connects to the goals of this session")
    bullets.append(f"Practical implications and next steps for {section.lower()}")
    return bullets[:5]


def _section_notes(section: str, brief: dict) -> str:
    title = brief.get("title") or "the topic"
    audience = brief.get("audience") or "your audience"
    purpose = brief.get("purpose") or "the session purpose"
    return (
        f"Introduce {section.lower()} in the context of '{title}'. "
        f"Tailor examples to {audience}. Emphasise how this section supports "
        f"the purpose: {purpose}. Pause for a quick question before moving on."
    )


def compose_outline_offline(brief: dict) -> list[dict]:
    """Build a deterministic outline from the brief without any AI provider."""
    n = brief.get("slide_count", 10)
    try:
        n = int(n)
    except (TypeError, ValueError):
        n = 10
    n = max(4, min(60, n))

    title = (brief.get("title") or "Untitled Presentation").strip()
    instructions = (brief.get("instructions") or "").strip()
    audience = brief.get("audience") or "the audience"
    purpose = brief.get("purpose") or "this session"
    sections = _derive_sections(instructions)

    items: list[dict] = []

    # 1. Cover.
    cover_sub = instructions[:150] if instructions else purpose
    items.append({
        "title": title,
        "bullets": [cover_sub] if cover_sub else [],
        "layout_hint": "cover",
        "notes": (
            f"Welcome {audience}. State the purpose of the session: {purpose}. "
            f"Set expectations for the {n} slides ahead and invite questions at the end."
        ),
    })

    # 2. Agenda.
    items.append({
        "title": "Agenda",
        "bullets": sections[:6],
        "layout_hint": "title-content",
        "notes": (
            "Walk through the agenda so the audience knows the journey. "
            "Mention the key takeaways slide at the end."
        ),
    })

    # Middle slides distributed across sections.
    middle_count = n - 4  # cover + agenda + takeaways + thank-you
    per_section = middle_count // len(sections)
    extra = middle_count % len(sections)
    prev_hint = "title-content"
    rot_idx = 0
    for si, section in enumerate(sections):
        count = per_section + (1 if si < extra else 0)
        for k in range(count):
            slide_title = section if count == 1 else (
                section if k == 0 else f"{section}: In Practice"
            )
            hint = _MIDDLE_LAYOUT_ROTATION[rot_idx % len(_MIDDLE_LAYOUT_ROTATION)]
            rot_idx += 1
            if hint == prev_hint:
                hint = _ALT_LAYOUT.get(hint, "title-content")
            prev_hint = hint
            items.append({
                "title": slide_title,
                "bullets": _section_bullets(section, brief),
                "layout_hint": hint,
                "notes": _section_notes(section, brief),
            })

    # Second-last: key takeaways.
    take_hint = "checklist" if prev_hint != "checklist" else "title-content"
    items.append({
        "title": "Key Takeaways",
        "bullets": [
            f"The essentials of {s.lower()} to remember" for s in sections[:4]
        ],
        "layout_hint": take_hint,
        "notes": (
            "Recap the four essentials. Ask the audience to name one action "
            "they will take after this session."
        ),
    })

    # Last: thank-you.
    items.append({
        "title": "Thank You",
        "bullets": [],
        "layout_hint": "thank-you",
        "notes": "Thank the audience and open the floor for questions and discussion.",
    })

    return items


# ---------------------------------------------------------------------------
# slide building / theming
# ---------------------------------------------------------------------------

def build_slides(project: dict, outline: list[dict], theme) -> list[dict]:
    """Turn outline items into slides with per-layout elements.

    `theme` may be a theme dict or a theme id. Enforces: first slide is
    'cover', last is 'thank-you', and no two consecutive slides share a layout.
    """
    th = theme if isinstance(theme, dict) else get_theme(theme)
    slides: list[dict] = []
    prev: str | None = None
    total = len(outline)
    for idx, item in enumerate(outline):
        hint = item.get("layout_hint") or "title-content"
        if idx == 0:
            hint = "cover"
        elif idx == total - 1 and total > 1:
            hint = "thank-you"
        hint = _resolve_layout(hint, prev)
        prev = hint
        builder = _BUILDERS[hint]
        elements = builder(project, item, th)
        slides.append({
            "id": new_id("s_"),
            "layout": hint,
            "elements": elements,
            "notes": str(item.get("notes", "")),
        })
    return slides


def apply_theme(project: dict, theme_id: str) -> dict:
    """Set a project's theme id (text is kept; colors resolve at render time)."""
    from themes import THEMES  # local import, no cycle

    if theme_id not in THEMES:
        raise ValueError(f"Unknown theme id: {theme_id!r}")
    project["theme"] = theme_id
    return project
