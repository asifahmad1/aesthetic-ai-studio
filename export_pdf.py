"""PDF exporter for Aesthetic AI Studio v1.

Renders each slide with reportlab onto a 16:9 landscape page
(13.333 x 7.5 inches = 960 x 540 pt). Text is drawn with manual word
wrapping via stringWidth; tables as grids; images as labeled placeholders.

Font mapping (built-in PDF fonts only, no embedding needed):
    Georgia      -> Times-Roman / Times-Bold
    Trebuchet MS -> Helvetica-Bold
    Calibri/Arial/Helvetica -> Helvetica / Helvetica-Bold

Public API:
    export_pdf(project, theme, out_path) -> {"ok": bool, "checks": [...]}
"""
from __future__ import annotations

import os

from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white
from reportlab.pdfbase.pdfmetrics import stringWidth
from pypdf import PdfReader

PAGE_W_PT = 13.333 * 72   # 960
PAGE_H_PT = 7.5 * 72      # 540
SX = PAGE_W_PT / 1000.0   # canvas x -> pt
SY = PAGE_H_PT / 562.5    # canvas y -> pt

_FALLBACK_THEME = {
    "name": "Fallback", "primary": "#0B3D2E", "secondary": "#14532D",
    "accent": "#C9A227", "background": "#FFFFFF", "surface": "#F4F1E8",
    "text": "#1A1A1A", "muted": "#6B7280",
    "chart": ["#0B3D2E", "#C9A227", "#14532D", "#6B7280", "#D6C68A"],
    "heading_font": "Georgia", "body_font": "Calibri",
}

_HEADING_ROLES = {"title", "heading", "section", "quote", "stat", "kicker"}


def _num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return float(default)


def _color(hex_color, default="#000000"):
    h = (hex_color or default).strip()
    if not h.startswith("#"):
        h = "#" + h
    try:
        return HexColor(h)
    except Exception:  # noqa: BLE001
        return HexColor(default)


def _pdf_font(name, bold):
    n = (name or "").lower()
    if "georgia" in n:
        return "Times-Bold" if bold else "Times-Roman"
    if "trebuchet" in n:
        return "Helvetica-Bold"
    if "calibri" in n or "arial" in n or "helvetica" in n:
        return "Helvetica-Bold" if bold else "Helvetica"
    return "Helvetica-Bold" if bold else "Helvetica"


def _role_style(role, theme, element):
    role = (role or "body").lower()
    if role in _HEADING_ROLES:
        family = theme.get("heading_font") or "Georgia"
    else:
        family = theme.get("body_font") or "Calibri"
    defaults = {
        "title": (30, True), "subtitle": (18, False), "heading": (22, True),
        "section": (26, True), "quote": (20, False), "stat": (30, True),
        "kicker": (13, True), "caption": (11, False), "footer": (10, False),
    }
    size, bold = defaults.get(role, (14, False))
    size = _num(element.get("font_size"), size) or size
    if element.get("bold") is not None:
        bold = bool(element.get("bold"))
    return _pdf_font(family, bold), size


def _wrap(line, font, size, max_w):
    words = str(line).split(" ")
    out, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if not cur or stringWidth(t, font, size) <= max_w:
            cur = t
        else:
            out.append(cur)
            cur = w
    if cur:
        out.append(cur)
    return out or [""]


def _box(el):
    x = max(0.0, _num(el.get("x")))
    y = max(0.0, _num(el.get("y")))
    w = max(8.0, _num(el.get("w"), 200))
    h = max(8.0, _num(el.get("h"), 60))
    return x * SX, y * SY, w * SX, h * SY


def _draw_text(c, el, theme):
    x, y, w, h = _box(el)
    font, size = _role_style(el.get("role"), theme, el)
    color = _color(el.get("text_color"), theme.get("text", "#1A1A1A"))
    align = (el.get("align") or "left").lower()

    max_w = max(10.0, w - 8)
    lines = []
    for raw in str(el.get("text") or "").split("\n"):
        raw = raw.strip()
        if not raw:
            continue
        bullet = raw.startswith(("\u2022 ", "- "))
        if raw.startswith("- "):
            raw = "\u2022 " + raw[2:]
        indent = 14 if bullet else 0
        for wl in _wrap(raw, font, size, max_w - indent):
            lines.append((wl, indent))

    line_h = size * 1.3
    cursor = PAGE_H_PT - y - size  # baseline of first line
    c.setFont(font, size)
    c.setFillColor(color)
    for text, indent in lines:
        if cursor < PAGE_H_PT - y - h + 4:
            break  # out of box; clip
        tw = stringWidth(text, font, size)
        if align == "center":
            tx = x + (w - tw) / 2
        elif align == "right":
            tx = x + w - tw - 4
        else:
            tx = x + 4 + indent
        c.drawString(tx, cursor, text)
        cursor -= line_h


def _draw_shape(c, el, theme):
    x, y, w, h = _box(el)
    kind = (el.get("shape") or "rect").lower()
    top = PAGE_H_PT - y
    if kind == "line":
        c.setStrokeColor(_color(el.get("line"), theme.get("muted", "#6B7280")))
        c.setLineWidth(2)
        c.line(x, top, x + w, top - h)
        return
    fill = el.get("fill")
    if (fill or "").lower() not in ("none", "transparent"):
        c.setFillColor(_color(fill, theme.get("surface", "#F4F1E8")))
        filled = 1
    else:
        filled = 0
    if kind in ("oval", "circle", "ellipse"):
        c.ellipse(x, top - h, x + w, top, stroke=1, fill=filled)
    else:
        c.setStrokeColor(_color(el.get("line"), theme.get("muted", "#6B7280")))
        c.rect(x, top - h, w, h, stroke=1, fill=filled)


def _draw_table(c, el, theme):
    rows = [list(r) for r in (el.get("rows") or []) if r is not None]
    if not rows:
        return
    ncols = max(len(r) for r in rows)
    for r in rows:
        r.extend([""] * (ncols - len(r)))
    x, y, w, h = _box(el)
    nrows = len(rows)
    row_h = h / nrows
    col_w = w / ncols
    top = PAGE_H_PT - y
    font_b = _pdf_font(theme.get("body_font"), True)
    font_r = _pdf_font(theme.get("body_font"), False)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cx, cy = x + j * col_w, top - (i + 1) * row_h
            if i == 0:
                c.setFillColor(_color(theme.get("primary", "#0B3D2E")))
                c.rect(cx, cy, col_w, row_h, stroke=0, fill=1)
                c.setFillColor(white)
                c.setFont(font_b, 10)
            else:
                if i % 2 == 0:
                    c.setFillColor(_color(theme.get("surface", "#F4F1E8")))
                    c.rect(cx, cy, col_w, row_h, stroke=0, fill=1)
                c.setFillColor(_color(theme.get("text", "#1A1A1A")))
                c.setFont(font_r, 10)
            c.drawString(cx + 4, cy + row_h / 2 - 3.5,
                         str(val)[: int(col_w / 6) + 8])
    c.setStrokeColor(_color(theme.get("muted", "#6B7280")))
    c.setLineWidth(0.75)
    for i in range(nrows + 1):
        c.line(x, top - i * row_h, x + w, top - i * row_h)
    for j in range(ncols + 1):
        c.line(x + j * col_w, top, x + j * col_w, top - h)


def _draw_image_placeholder(c, el, theme):
    x, y, w, h = _box(el)
    top = PAGE_H_PT - y
    c.setFillColor(_color(theme.get("surface", "#F4F1E8")))
    c.setStrokeColor(_color(theme.get("muted", "#6B7280")))
    c.setLineWidth(1)
    c.rect(x, top - h, w, h, stroke=1, fill=1)
    alt = el.get("alt") or el.get("prompt") or "image"
    c.setFillColor(_color(theme.get("muted", "#6B7280")))
    c.setFont("Helvetica", 12)
    label = ("[Image] " + str(alt))[:60]
    tw = stringWidth(label, "Helvetica", 12)
    c.drawString(x + (w - tw) / 2, top - h / 2, label)


def _draw_slide(c, slide, theme):
    c.setFillColor(_color(theme.get("background", "#FFFFFF")))
    c.rect(0, 0, PAGE_W_PT, PAGE_H_PT, stroke=0, fill=1)
    for el in slide.get("elements", []) or []:
        etype = (el.get("type") or "").lower()
        try:
            if etype == "text":
                _draw_text(c, el, theme)
            elif etype == "shape":
                _draw_shape(c, el, theme)
            elif etype == "table":
                _draw_table(c, el, theme)
            elif etype == "image":
                _draw_image_placeholder(c, el, theme)
        except Exception:  # noqa: BLE001
            continue
    # notes are not rendered on the slide itself; PDF has no notes pages in v1
    c.showPage()


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
    if exists:
        with open(out_path, "rb") as f:
            header = f.read(5)
        check("%PDF header present", header == b"%PDF-",
              f"first bytes: {header!r}")
    else:
        check("%PDF header present", False, "no file to inspect")

    try:
        reader = PdfReader(out_path)
        pages = len(reader.pages)
        check("PDF opens and page count matches slide count",
              pages == len(project.get("slides", [])),
              f"pdf has {pages} pages, project has "
              f"{len(project.get('slides', []))} slides")
    except Exception as e:  # noqa: BLE001
        check("PDF opens and page count matches slide count", False,
              f"pypdf failed: {type(e).__name__}: {e}")
    return checks


def export_pdf(project, theme, out_path):
    """Export project to PDF and validate. Returns validation dict."""
    try:
        theme = dict(_FALLBACK_THEME, **(theme or {}))
        parent = os.path.dirname(os.path.abspath(out_path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        c = canvas.Canvas(out_path, pagesize=(PAGE_W_PT, PAGE_H_PT))
        c.setTitle((project or {}).get("title", "Presentation"))
        c.setAuthor("Aesthetic AI Studio")
        for s in (project or {}).get("slides", []):
            _draw_slide(c, s, theme)
        c.save()
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "checks": [
            {"name": "export completed", "passed": False,
             "detail": f"export raised: {type(e).__name__}: {e}"}]}
    checks = _validate(out_path, project or {})
    return {"ok": all(ch["passed"] for ch in checks), "checks": checks}
