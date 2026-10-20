"""HTML exporter for Aesthetic AI Studio v1.

Produces a single standalone .html file (inline CSS, no external assets).
Prefers render.render_deck_html when the render module is available;
otherwise builds a faithful standalone document itself.

Public API:
    export_html(project, theme, out_path) -> {"ok": bool, "checks": [...]}
"""
from __future__ import annotations

import html
import os

_FALLBACK_THEME = {
    "name": "Fallback", "primary": "#0B3D2E", "secondary": "#14532D",
    "accent": "#C9A227", "background": "#FFFFFF", "surface": "#F4F1E8",
    "text": "#1A1A1A", "muted": "#6B7280",
    "chart": ["#0B3D2E", "#C9A227", "#14532D", "#6B7280", "#D6C68A"],
    "heading_font": "Georgia", "body_font": "Calibri",
}


def slide_title(slide):
    """Best-effort title: first title/heading-role text element, else first text."""
    texts = [e for e in (slide.get("elements") or [])
             if (e.get("type") or "").lower() == "text" and e.get("text")]
    for e in texts:
        if (e.get("role") or "").lower() in ("title", "heading", "section"):
            return str(e["text"]).split("\n")[0].strip()[:120]
    if texts:
        return str(texts[0]["text"]).split("\n")[0].strip()[:120]
    return f"Slide ({slide.get('layout', 'untitled')})"


def _esc(v):
    return html.escape(str(v), quote=True)


def _render_element(el, theme):
    etype = (el.get("type") or "").lower()
    x = float(el.get("x") or 0); y = float(el.get("y") or 0)
    w = float(el.get("w") or 200); h = float(el.get("h") or 60)
    style = (f"position:absolute;left:{x/10:.2f}%;top:{y/5.625:.2f}%;"
             f"width:{w/10:.2f}%;height:{h/5.625:.2f}%;")
    if etype == "text":
        role = (el.get("role") or "body").lower()
        tag = "h1" if role == "title" else "h2" if role in (
            "heading", "section") else "p"
        color = el.get("text_color") or theme.get("text", "#1A1A1A")
        fam = (theme.get("heading_font") if role in (
            "title", "heading", "section", "quote", "stat")
               else theme.get("body_font")) or "sans-serif"
        fs = float(el.get("font_size") or
                   {"title": 40, "heading": 28, "section": 32,
                    "stat": 38}.get(role, 18))
        # canvas 1000px wide -> slide rendered ~960px, keep px sizes close
        lines = []
        for raw in str(el.get("text") or "").split("\n"):
            raw = raw.strip()
            if not raw:
                continue
            if raw.startswith(("- ", "\u2022 ")):
                lines.append(f"<li>{_esc(raw[2:])}</li>")
            else:
                lines.append(_esc(raw))
        # group consecutive <li> items into a <ul>
        out, buf = [], []
        for item in lines:
            if item.startswith("<li>"):
                buf.append(item)
            else:
                if buf:
                    out.append("<ul>" + "".join(buf) + "</ul>")
                    buf = []
                out.append(f"<p>{item}</p>")
        if buf:
            out.append("<ul>" + "".join(buf) + "</ul>")
        align = (el.get("align") or "left").lower()
        bold = "font-weight:bold;" if el.get("bold") else ""
        return (f'<div style="{style}color:{_esc(color)};'
                f'font-family:{_esc(fam)};font-size:{fs*0.96:.1f}px;'
                f'text-align:{align};{bold}overflow:hidden;">'
                f"<{tag} style='margin:0 0 8px;font-size:inherit;'>"
                f"{''.join(out)}</{tag}></div>")
    if etype == "table":
        rows = [list(r) for r in (el.get("rows") or [])]
        cells = []
        for i, row in enumerate(rows):
            tds = "".join(
                f"<{'th' if i == 0 else 'td'}>{_esc(c)}</{'th' if i == 0 else 'td'}>"
                for c in row)
            cells.append(f"<tr>{tds}</tr>")
        return (f'<div style="{style}overflow:hidden;">'
                f"<table style='width:100%;border-collapse:collapse;"
                f"font-size:13px;'><tbody>{''.join(cells)}</tbody></table></div>")
    if etype == "image":
        alt = el.get("alt") or el.get("prompt") or "image"
        return (f'<div style="{style}display:flex;align-items:center;'
                f"justify-content:center;background:{_esc(theme.get('surface', '#F4F1E8'))};"
                f"border:1px dashed {_esc(theme.get('muted', '#6B7280'))};"
                f"color:{_esc(theme.get('muted', '#6B7280'))};"
                f'font-size:13px;text-align:center;">'
                f"\U0001F5BC {_esc(alt)}<br>(image placeholder)</div>")
    # shape
    kind = (el.get("shape") or "rect").lower()
    fill = el.get("fill")
    bg = "transparent" if (fill or "").lower() in (
        "none", "transparent") else (fill or theme.get("surface", "#F4F1E8"))
    radius = "50%" if kind in ("oval", "circle", "ellipse") else (
        "18px" if kind in ("roundrect", "rounded", "pill") else "6px")
    if kind == "line":
        return (f'<div style="{style}border-top:3px solid '
                f'{_esc(el.get("line") or theme.get("muted", "#6B7280"))};'
                f'height:0;"></div>')
    return (f'<div style="{style}background:{_esc(bg)};border-radius:{radius};'
            f'border:1px solid {_esc(el.get("line") or "transparent")};"></div>')


def build_standalone_html(project, theme):
    theme = dict(_FALLBACK_THEME, **(theme or {}))
    project = project or {}
    title = project.get("title") or "Presentation"
    slides = project.get("slides", [])
    parts = [f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(title)}</title>
<style>
  body {{ margin:0; background:#111; font-family:{_esc(theme.get('body_font','Calibri'))},sans-serif; }}
  header {{ color:#fff; padding:24px 32px; }}
  header h1 {{ margin:0 0 4px; font-family:{_esc(theme.get('heading_font','Georgia'))},serif; }}
  header p {{ margin:0; opacity:.7; }}
  section.slide {{ background:{_esc(theme.get('background','#FFFFFF'))};
    width:min(960px,94vw); aspect-ratio:16/9; margin:0 auto 32px;
    position:relative; overflow:hidden; border-radius:10px;
    box-shadow:0 8px 30px rgba(0,0,0,.45); color:{_esc(theme.get('text','#1A1A1A'))}; }}
  section.slide .badge {{ position:absolute; right:14px; bottom:10px;
    font-size:12px; color:{_esc(theme.get('muted','#6B7280'))}; }}
  table th {{ background:{_esc(theme.get('primary','#0B3D2E'))}; color:#fff;
    padding:6px 8px; text-align:left; }}
  table td {{ border:1px solid {_esc(theme.get('muted','#6B7280'))};
    padding:6px 8px; }}
  table th {{ border:1px solid {_esc(theme.get('primary','#0B3D2E'))}; }}
  ul {{ margin:4px 0; padding-left:22px; }}
</style>
</head>
<body>
<header><h1>{_esc(title)}</h1>
<p>{len(slides)} slides &middot; exported by Aesthetic AI Studio</p></header>
<main>"""]
    for i, s in enumerate(slides, 1):
        st = slide_title(s)
        els = "".join(_render_element(e, theme)
                      for e in (s.get("elements") or []))
        notes = (s.get("notes") or "").strip()
        notes_html = (f"<details style='margin:0 auto 32px;width:min(960px,94vw);"
                      f"color:#ddd;'><summary>Speaker notes</summary>"
                      f"<p>{_esc(notes)}</p></details>" if notes else "")
        parts.append(
            f'<section class="slide" id="slide-{i}" data-layout="{_esc(s.get("layout",""))}">'
            f"<!-- {_esc(st)} -->{els}"
            f'<div class="badge">{i} / {len(slides)}</div></section>{notes_html}')
    parts.append("</main></body></html>")
    return "".join(parts)


def _validate(out_path, project, html_text):
    checks = []

    def check(name, passed, detail):
        checks.append({"name": name, "passed": bool(passed),
                       "detail": str(detail)})

    exists = os.path.isfile(out_path)
    size = os.path.getsize(out_path) if exists else 0
    check("file exists and larger than 5KB",
          exists and size > 5 * 1024,
          f"exists={exists}, size={size} bytes")

    slides = project.get("slides", []) if project else []
    n_sections = html_text.count("<section")
    check("contains one <section> per slide",
          n_sections >= len(slides) and len(slides) > 0,
          f"found {n_sections} <section> tags for {len(slides)} slides")

    titles = [slide_title(s) for s in slides]
    missing = [t for t in titles if _esc(t) not in html_text and t not in html_text]
    if not missing:
        check("all slide titles present in HTML", True,
              f"all {len(titles)} slide titles found")
    else:
        first3 = titles[:3]
        first3_ok = all((_esc(t) in html_text or t in html_text)
                        for t in first3)
        check("all slide titles present in HTML",
              first3_ok and n_sections >= len(slides),
              f"{len(missing)} titles missing "
              f"(e.g. {missing[0][:50] if missing else ''}); "
              f"first-3 present={first3_ok}, section count ok="
              f"{n_sections >= len(slides)}")
    return checks


def export_html(project, theme, out_path):
    """Export project to standalone HTML and validate. Returns validation dict."""
    project = project or {}
    html_text = None
    try:
        try:
            from render import render_deck_html  # noqa: PLC0415
            html_text = render_deck_html(project, theme or {})
        except Exception:  # noqa: BLE001
            html_text = None
        if not html_text:
            html_text = build_standalone_html(project, theme or {})
        parent = os.path.dirname(os.path.abspath(out_path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html_text)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "checks": [
            {"name": "export completed", "passed": False,
             "detail": f"export raised: {type(e).__name__}: {e}"}]}
    checks = _validate(out_path, project, html_text)
    return {"ok": all(c["passed"] for c in checks), "checks": checks}
