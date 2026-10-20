"""PPTX exporter for Aesthetic AI Studio v1.

Converts a slide-document (see ARCHITECTURE.md data model) into a fully
editable .pptx file using ONLY native python-pptx objects -- text boxes,
shapes, tables and connectors. Never screenshots.

Canvas: the slide model uses a 1000 x 562.5 coordinate space which maps to a
16:9 slide of 13.333 x 7.5 inches.

Public API:
    export_pptx(project, theme, out_path) -> {"ok": bool, "checks": [...]}
"""
from __future__ import annotations

import os

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

SLIDE_W_IN = 13.333
SLIDE_H_IN = 7.5
CANVAS_W = 1000.0
CANVAS_H = 562.5

KNOWN_LAYOUTS = [
    "cover", "title-content", "two-column", "three-column", "big-quote",
    "stats-dashboard", "timeline", "split-image-text", "section-divider",
    "comparison", "checklist", "references", "thank-you",
]

HEADING_ROLES = {"title", "heading", "section", "quote", "stat", "kicker"}

_ALIGN = {
    "left": PP_ALIGN.LEFT,
    "center": PP_ALIGN.CENTER,
    "right": PP_ALIGN.RIGHT,
    "justify": PP_ALIGN.JUSTIFY,
}

_SHAPE_MAP = {
    "rect": MSO_SHAPE.RECTANGLE,
    "rectangle": MSO_SHAPE.RECTANGLE,
    "roundrect": MSO_SHAPE.ROUNDED_RECTANGLE,
    "rounded": MSO_SHAPE.ROUNDED_RECTANGLE,
    "oval": MSO_SHAPE.OVAL,
    "circle": MSO_SHAPE.OVAL,
    "ellipse": MSO_SHAPE.OVAL,
    "diamond": MSO_SHAPE.DIAMOND,
    "triangle": MSO_SHAPE.ISOSCELES_TRIANGLE,
    "pill": MSO_SHAPE.ROUNDED_RECTANGLE,
}

_FALLBACK_THEME = {
    "name": "Fallback", "primary": "#0B3D2E", "secondary": "#14532D",
    "accent": "#C9A227", "background": "#FFFFFF", "surface": "#F4F1E8",
    "text": "#1A1A1A", "muted": "#6B7280",
    "chart": ["#0B3D2E", "#C9A227", "#14532D", "#6B7280", "#D6C68A"],
    "heading_font": "Georgia", "body_font": "Calibri",
}


# ---------------------------------------------------------------- helpers

def _num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return float(default)


def _rgb(hex_color, default="#000000"):
    h = (hex_color or default).strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6 or any(c not in "0123456789abcdefABCDEF" for c in h):
        h = default.lstrip("#")
    return RGBColor.from_string(h)


def _box(el):
    """Canvas coords -> inches (left, top, width, height), clamped sane."""
    x = max(0.0, _num(el.get("x")))
    y = max(0.0, _num(el.get("y")))
    w = max(8.0, _num(el.get("w"), 200))
    h = max(8.0, _num(el.get("h"), 60))
    return (Inches(x / CANVAS_W * SLIDE_W_IN),
            Inches(y / CANVAS_H * SLIDE_H_IN),
            Inches(w / CANVAS_W * SLIDE_W_IN),
            Inches(h / CANVAS_H * SLIDE_H_IN))


def _role_font(role, theme, element):
    role = (role or "body").lower()
    if role in HEADING_ROLES:
        family = theme.get("heading_font") or "Georgia"
    else:
        family = theme.get("body_font") or "Calibri"
    defaults = {
        "title": (40, True), "subtitle": (24, False), "heading": (28, True),
        "section": (32, True), "quote": (26, False), "stat": (38, True),
        "kicker": (16, True), "caption": (13, False), "footer": (12, False),
    }
    size, bold = defaults.get(role, (18, False))
    size = _num(element.get("font_size"), size) or size
    if element.get("bold") is not None:
        bold = bool(element.get("bold"))
    return family, Pt(size), bold


# ---------------------------------------------------------------- builders

def _add_text(slide, el, theme):
    left, top, width, height = _box(el)
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    family, size, bold = _role_font(el.get("role"), theme, el)
    color = _rgb(el.get("text_color"), theme.get("text", "#1A1A1A"))
    align = _ALIGN.get((el.get("align") or "left").lower(), PP_ALIGN.LEFT)

    raw = el.get("text") or ""
    lines = str(raw).split("\n")
    first = True
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        bullet = stripped.startswith(("\u2022 ", "- "))
        text = stripped
        if stripped.startswith("- "):
            text = "\u2022 " + stripped[2:]
        p.text = ""
        run = p.add_run()
        run.text = text
        run.font.name = family
        run.font.size = size
        run.font.bold = bold
        run.font.color.rgb = color
        p.alignment = align
        if bullet:
            p.level = 0
    return txBox


def _add_shape(slide, el, theme):
    kind = (el.get("shape") or "rect").lower()
    if kind == "line":
        return _add_line(slide, el, theme)
    left, top, width, height = _box(el)
    shape = slide.shapes.add_shape(
        _SHAPE_MAP.get(kind, MSO_SHAPE.RECTANGLE), left, top, width, height)
    fill = el.get("fill")
    if (fill or "").lower() in ("none", "transparent"):
        shape.fill.background()
    else:
        shape.fill.solid()
        shape.fill.fore_color.rgb = _rgb(fill, theme.get("surface", "#F4F1E8"))
    line = el.get("line")
    if line:
        shape.line.color.rgb = _rgb(line, theme.get("muted", "#6B7280"))
        shape.line.width = Pt(1.5)
    else:
        shape.line.fill.background()
    shape.text_frame.word_wrap = True
    return shape


def _add_line(slide, el, theme):
    x = _num(el.get("x")); y = _num(el.get("y"))
    w = _num(el.get("w"), 200); h = _num(el.get("h"), 0)
    bx = Inches(x / CANVAS_W * SLIDE_W_IN)
    by = Inches(y / CANVAS_H * SLIDE_H_IN)
    ex = Inches((x + w) / CANVAS_W * SLIDE_W_IN)
    ey = Inches((y + h) / CANVAS_H * SLIDE_H_IN)
    conn = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, bx, by, ex, ey)
    conn.line.color.rgb = _rgb(el.get("line"), theme.get("muted", "#6B7280"))
    conn.line.width = Pt(2.25)
    return conn


def _add_table(slide, el, theme):
    rows = el.get("rows") or []
    rows = [list(r) for r in rows if r is not None]
    if not rows:
        return None
    ncols = max(len(r) for r in rows)
    for r in rows:
        r.extend([""] * (ncols - len(r)))
    left, top, width, height = _box(el)
    graphic = slide.shapes.add_table(len(rows), ncols, left, top, width, height)
    table = graphic.table
    col_w = int(width / ncols)
    for j in range(ncols):
        table.columns[j].width = col_w
    header_fill = _rgb(theme.get("primary", "#0B3D2E"))
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = table.cell(i, j)
            cell.text = ""
            cell.vertical_anchor = 1  # middle
            p = cell.text_frame.paragraphs[0]
            run = p.add_run()
            run.text = str(val)
            if i == 0:
                run.font.bold = True
                run.font.size = Pt(13)
                run.font.color.rgb = RGBColor(255, 255, 255)
                cell.fill.solid()
                cell.fill.fore_color.rgb = header_fill
            else:
                run.font.size = Pt(12)
                run.font.color.rgb = _rgb(theme.get("text", "#1A1A1A"))
                if i % 2 == 0:
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = _rgb(
                        theme.get("surface", "#F4F1E8"))
            p.alignment = PP_ALIGN.LEFT
    return graphic


def _add_image_placeholder(slide, el, theme):
    left, top, width, height = _box(el)
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = _rgb(theme.get("surface", "#F4F1E8"))
    shape.line.color.rgb = _rgb(theme.get("muted", "#6B7280"))
    shape.line.width = Pt(1)
    alt = el.get("alt") or el.get("prompt") or "image"
    tf = shape.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = "\U0001F5BC " + str(alt)
    run.font.size = Pt(14)
    run.font.color.rgb = _rgb(theme.get("muted", "#6B7280"))
    p2 = tf.add_paragraph()
    p2.alignment = PP_ALIGN.CENTER
    run2 = p2.add_run()
    run2.text = "(image placeholder)"
    run2.font.size = Pt(11)
    run2.font.color.rgb = _rgb(theme.get("muted", "#6B7280"))
    return shape


def _build(project, theme, out_path):
    theme = dict(_FALLBACK_THEME, **(theme or {}))
    prs = Presentation()
    prs.slide_width = Inches(SLIDE_W_IN)
    prs.slide_height = Inches(SLIDE_H_IN)
    blank = prs.slide_layouts[6]

    for s in project.get("slides", []):
        slide = prs.slides.add_slide(blank)
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = _rgb(
            theme.get("background", "#FFFFFF"))
        for el in s.get("elements", []) or []:
            etype = (el.get("type") or "").lower()
            try:
                if etype == "text":
                    _add_text(slide, el, theme)
                elif etype == "shape":
                    _add_shape(slide, el, theme)
                elif etype == "table":
                    _add_table(slide, el, theme)
                elif etype == "image":
                    _add_image_placeholder(slide, el, theme)
            except Exception:
                continue  # one bad element must not kill the deck
        notes = (s.get("notes") or "").strip()
        if notes:
            slide.notes_slide.notes_text_frame.text = notes

    parent = os.path.dirname(os.path.abspath(out_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    prs.save(out_path)
    return out_path


# ---------------------------------------------------------------- validation

def _deck_text(path):
    prs = Presentation(path)
    parts = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                parts.append(shape.text_frame.text)
            if shape.has_table:
                for row in shape.table.rows:
                    for cell in row.cells:
                        parts.append(cell.text)
    return "\n".join(parts)


def _validate(out_path, project):
    checks = []

    def check(name, passed, detail):
        checks.append({"name": name, "passed": bool(passed),
                       "detail": str(detail)})

    exists = os.path.isfile(out_path)
    size = os.path.getsize(out_path) if exists else 0
    check("file exists and larger than 10KB",
          exists and size > 10 * 1024,
          f"exists={exists}, size={size} bytes")

    try:
        prs = Presentation(out_path)
    except Exception as e:  # noqa: BLE001
        check("file opens as a valid presentation", False, f"open failed: {e}")
        return checks
    check("file opens as a valid presentation", True,
          "python-pptx reopened the file")

    expected = len(project.get("slides", []))
    actual = len(prs.slides)
    check("slide count matches project",
          actual == expected,
          f"pptx has {actual} slides, project has {expected}")

    empty = [i + 1 for i, sl in enumerate(prs.slides)
             if len(sl.shapes) == 0]
    check("every slide has at least one shape",
          not empty,
          "all slides have shapes" if not empty
          else f"slides with no shapes: {empty}")

    title = (project.get("title") or "").strip()
    if title:
        text = _deck_text(out_path)
        check("deck text contains project title",
              title.lower() in text.lower(),
              f"title '{title[:60]}' found in deck text"
              if title.lower() in text.lower()
              else f"title '{title[:60]}' NOT found in deck text")
    else:
        check("deck text contains project title", False,
              "project has no title to check")

    layouts = [s.get("layout") for s in project.get("slides", [])]
    bad = sorted({l for l in layouts if l not in KNOWN_LAYOUTS})
    check("all slide layouts are from the known set",
          not bad,
          "all layouts known" if not bad
          else f"unknown layouts: {bad}")

    native = sum(1 for sl in prs.slides for sh in sl.shapes
                 if sh.has_text_frame and sh.text_frame.text.strip())
    check("deck uses native editable text (not screenshots)",
          native > 0,
          f"{native} shapes carry native text")
    return checks


# ---------------------------------------------------------------- public API

def export_pptx(project, theme, out_path):
    """Export project to .pptx and validate. Returns validation dict."""
    try:
        _build(project or {}, theme or {}, out_path)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "checks": [
            {"name": "export completed", "passed": False,
             "detail": f"export raised: {type(e).__name__}: {e}"}]}
    checks = _validate(out_path, project or {})
    return {"ok": all(c["passed"] for c in checks), "checks": checks}
