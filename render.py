"""HTML rendering for Aesthetic AI Studio v1.

- render_slide_html(slide, theme): one slide as an HTML fragment of
  absolutely-positioned divs inside a 1000 x 562.5 box, with inline styles
  resolved from the theme plus element overrides.
- render_deck_html(project, theme): a full standalone HTML document with all
  slides as <section> pages plus print CSS.
"""

from __future__ import annotations

import html as _html
import re

# Default font sizes per text role (used when element.font_size is None).
_ROLE_FONT_SIZE = {
    "title": 40, "subtitle": 24, "kicker": 20, "heading": 28, "body": 22,
    "bullets": 20, "quote": 32, "caption": 16, "stat-value": 46, "stat-label": 18,
}

# Roles that use the theme's heading font; everything else uses the body font.
_HEADING_ROLES = {"title", "heading", "quote", "kicker", "stat-value"}

# Default theme color key per role (element.text_color overrides).
_ROLE_COLOR = {
    "kicker": "accent",
    "subtitle": "muted",
    "caption": "muted",
    "stat-value": "primary",
    "stat-label": "muted",
    "quote": "text",
}

_BULLET_RE = re.compile(r"^([•\-\u2611\u2713\u2717\u25b8])\s+(.*)$")
_NUMBERED_RE = re.compile(r"^(\d+)\.\s+(.*)$")


def _px(v) -> str:
    return f"{float(v):g}px"


def _render_rich_text(text: str) -> str:
    """Convert plain text with bullet markers into HTML.

    Lines starting with '• ', '- ', '☑ ', '✓ ', '✗ ' or '▸ ' become <ul>
    items; lines like '1. ...' become <ol> items; other lines become
    paragraphs. All content is HTML-escaped.
    """
    html_parts: list[str] = []
    open_list: str | None = None  # "ul" | "ol" | None

    def close_list():
        nonlocal open_list
        if open_list:
            html_parts.append(f"</{open_list}>")
            open_list = None

    for raw_line in (text or "").split("\n"):
        line = raw_line.strip()
        if not line:
            close_list()
            continue
        bullet = _BULLET_RE.match(line)
        numbered = _NUMBERED_RE.match(line)
        if bullet:
            if open_list != "ul":
                close_list()
                html_parts.append("<ul>")
                open_list = "ul"
            marker, text = bullet.group(1), bullet.group(2)
            if marker in ("☑", "✓", "✗", "▸"):
                # Keep semantic markers (checkboxes, ticks) visible: no disc.
                html_parts.append(
                    f'<li style="list-style:none;">{_html.escape(marker)} '
                    f"{_html.escape(text)}</li>"
                )
            else:
                html_parts.append(f"<li>{_html.escape(text)}</li>")
        elif numbered:
            if open_list != "ol":
                close_list()
                html_parts.append("<ol>")
                open_list = "ol"
            html_parts.append(f"<li>{_html.escape(numbered.group(2))}</li>")
        else:
            close_list()
            html_parts.append(f"<p>{_html.escape(line)}</p>")
    close_list()
    return "".join(html_parts)


def _render_text(el: dict, theme: dict) -> str:
    role = el.get("role", "body")
    font = theme["heading_font"] if role in _HEADING_ROLES else theme["body_font"]
    size = el.get("font_size") or _ROLE_FONT_SIZE.get(role, 20)
    color = el.get("text_color") or theme.get(_ROLE_COLOR.get(role, "text"), theme["text"])
    weight = "bold" if el.get("bold") else "normal"
    align = el.get("align", "left")
    body = _render_rich_text(el.get("text", ""))
    style = (
        f"position:absolute;left:{_px(el['x'])};top:{_px(el['y'])};"
        f"width:{_px(el['w'])};height:{_px(el['h'])};overflow:hidden;"
        f"font-family:{font},sans-serif;font-size:{size}px;font-weight:{weight};"
        f"text-align:{align};color:{color};line-height:1.45;"
    )
    return f'<div class="el-text el-{role}" style="{style}">{body}</div>'


def _render_shape(el: dict, theme: dict) -> str:
    shape = el.get("shape", "rect")
    if shape == "line":
        # A line is rendered as a thin horizontal bar.
        color = el.get("line") or el.get("fill") or theme["accent"]
        thickness = max(2.0, min(float(el["h"]), 8.0))
        style = (
            f"position:absolute;left:{_px(el['x'])};top:{_px(el['y'])};"
            f"width:{_px(el['w'])};height:{thickness:g}px;background:{color};"
        )
        return f'<div class="el-line" style="{style}"></div>'
    bg = el.get("fill") or "transparent"
    border = f"border:2px solid {el['line']};" if el.get("line") else ""
    radius = {"rect": "0", "roundrect": "14px", "oval": "50%"}.get(shape, "0")
    style = (
        f"position:absolute;left:{_px(el['x'])};top:{_px(el['y'])};"
        f"width:{_px(el['w'])};height:{_px(el['h'])};"
        f"background:{bg};{border}border-radius:{radius};"
    )
    return f'<div class="el-shape el-{shape}" style="{style}"></div>'


def _render_table(el: dict, theme: dict) -> str:
    rows = el.get("rows") or []
    size = el.get("font_size") or 18
    font = theme["body_font"]
    parts = [
        f'<table style="width:100%;border-collapse:collapse;'
        f'font-family:{font},sans-serif;font-size:{size}px;">'
    ]
    for ri, row in enumerate(rows):
        parts.append("<tr>")
        tag = "th" if ri == 0 else "td"
        cell_style = (
            f"background:{theme['primary']};color:#FFFFFF;font-weight:bold;"
            if ri == 0 else f"color:{theme['text']};"
        )
        for cell in row:
            parts.append(
                f"<{tag} style=\"{cell_style}border:1px solid {theme['muted']};"
                f"padding:8px 10px;text-align:left;vertical-align:top;\">"
                f"{_html.escape(cell)}</{tag}>"
            )
        parts.append("</tr>")
    parts.append("</table>")
    style = (
        f"position:absolute;left:{_px(el['x'])};top:{_px(el['y'])};"
        f"width:{_px(el['w'])};height:{_px(el['h'])};overflow:hidden;"
    )
    return f'<div class="el-table" style="{style}">{"".join(parts)}</div>'


def _render_image(el: dict, theme: dict) -> str:
    alt = _html.escape(el.get("alt") or "Image")
    style = (
        f"position:absolute;left:{_px(el['x'])};top:{_px(el['y'])};"
        f"width:{_px(el['w'])};height:{_px(el['h'])};"
        f"border:2px dashed {theme['muted']};background:{theme['surface']};"
        f"display:flex;flex-direction:column;align-items:center;justify-content:center;"
        f"font-family:{theme['body_font']},sans-serif;color:{theme['muted']};"
        f"text-align:center;padding:12px;box-sizing:border-box;"
    )
    return (
        f'<div class="el-image" style="{style}">'
        f'<div style="font-size:22px;">🖼 {alt}</div>'
        f'<div style="font-size:14px;margin-top:8px;">'
        f"(image placeholder — see Roadmap)</div></div>"
    )


def _render_element(el: dict, theme: dict) -> str:
    etype = el.get("type")
    if etype == "text":
        return _render_text(el, theme)
    if etype == "shape":
        return _render_shape(el, theme)
    if etype == "table":
        return _render_table(el, theme)
    if etype == "image":
        return _render_image(el, theme)
    return ""


def render_slide_html(slide: dict, theme: dict) -> str:
    """Render one slide as an HTML fragment (1000 x 562.5 box)."""
    body_font = theme.get("body_font", "Arial")
    parts = [
        f'<div class="slide" data-layout="{_html.escape(slide.get("layout", ""))}" '
        f'style="position:relative;width:1000px;height:562.5px;overflow:hidden;'
        f'background:{theme["background"]};font-family:{body_font},sans-serif;">'
    ]
    for el in slide.get("elements", []):
        parts.append(_render_element(el, theme))
    parts.append("</div>")
    return "".join(parts)


def render_deck_html(project: dict, theme: dict) -> str:
    """Render the whole project as a standalone HTML document."""
    title = _html.escape(project.get("title", "Presentation"))
    sections = []
    for i, slide in enumerate(project.get("slides", []), start=1):
        sections.append(
            f'<section class="slide-page" data-slide="{i}">'
            f"{render_slide_html(slide, theme)}</section>"
        )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  body {{ margin: 0; background: #1c1c1c; font-family: {theme.get('body_font', 'Arial')}, sans-serif; }}
  .deck {{ max-width: 1060px; margin: 0 auto; padding: 28px 16px; }}
  .deck-title {{ color: #f2f2f2; font-size: 22px; margin: 0 0 20px 20px; }}
  section.slide-page {{ width: 1000px; height: 562.5px; margin: 0 auto 32px auto;
    box-shadow: 0 6px 28px rgba(0,0,0,.55); }}
  section.slide-page ul, section.slide-page ol {{ margin: 6px 0; padding-left: 26px; }}
  section.slide-page li {{ margin: 4px 0; }}
  section.slide-page p {{ margin: 6px 0; }}
  @media print {{
    body {{ background: #fff; }}
    .deck {{ padding: 0; max-width: none; }}
    .deck-title {{ display: none; }}
    section.slide-page {{ margin: 0; box-shadow: none; page-break-after: always;
      break-after: page; }}
    @page {{ size: 13.33in 7.5in; margin: 0; }}
  }}
</style>
</head>
<body>
<div class="deck">
<h1 class="deck-title">{title}</h1>
{"".join(sections)}
</div>
</body>
</html>"""
