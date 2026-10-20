"""Contract tests: schema, themes, generator, sample.

Each test tries to import its sibling module and calls pytest.skip() when
the module is not present yet, so the suite stays green during parallel
development and strict at integration.
"""
import pytest


def _need(modname):
    try:
        return __import__(modname)
    except ImportError as e:
        pytest.skip(f"sibling module {modname} not written yet ({e})")


def _outline_text(item):
    if isinstance(item, dict):
        for k in ("title", "heading", "name", "text"):
            if item.get(k):
                return str(item[k])
        return str(item)
    return str(item)


# ---------------------------------------------------------------- schema

def test_schema_accepts_valid_project():
    schema = _need("schema")
    project = schema.blank_project({
        "title": "Food Safety & Hygiene Workshop",
        "slide_count": 8,
        "theme": "dark-green-gold",
    })
    errors = schema.validate_project(project)
    assert errors == [], f"blank project should validate, got: {errors}"
    assert project["slide_size"] == "16:9"
    assert project["status"] in ("draft", "outline", "building", "ready")


def test_schema_rejects_invalid_project():
    schema = _need("schema")
    errors = schema.validate_project({"id": "x"})  # missing almost everything
    assert isinstance(errors, list) and len(errors) > 0, \
        "validate_project must return errors for a broken document"
    bad_theme = schema.blank_project({"title": "T", "theme": "no-such-theme"})
    assert schema.validate_project(bad_theme), \
        "unknown theme id must be flagged"


# ---------------------------------------------------------------- generator

def test_offline_outline_shape():
    gen = _need("generator")
    outline = gen.compose_outline_offline({
        "title": "Food Safety & Hygiene Workshop",
        "instructions": "Executive training for hospital canteens",
        "audience": "Medical Officers",
        "slide_count": 10,
    })
    assert isinstance(outline, list) and len(outline) >= 3
    first = _outline_text(outline[0]).lower()
    last = _outline_text(outline[-1]).lower()
    assert any(w in first for w in ("cover", "title", "food safety")), \
        f"outline should open with a cover/title slide, got: {first!r}"
    assert "thank" in last, \
        f"outline should close with a thank-you slide, got: {last!r}"


def test_build_slides_count_and_layout_variety():
    gen = _need("generator")
    schema = _need("schema")
    themes = _need("themes")
    project = schema.blank_project({
        "title": "Food Safety & Hygiene Workshop",
        "slide_count": 12,
        "theme": "dark-green-gold",
    })
    theme = themes.get_theme("dark-green-gold")
    outline = gen.compose_outline_offline({
        "title": project["title"], "slide_count": 12})
    slides = gen.build_slides(project, outline, theme)
    assert isinstance(slides, list)
    assert len(slides) == 12, f"expected 12 slides, got {len(slides)}"
    layouts = [s.get("layout") for s in slides]
    for prev, cur in zip(layouts, layouts[1:]):
        assert prev != cur, \
            f"consecutive duplicate layouts are boring: {prev}"
    known = set(gen.LAYOUTS)  # works whether LAYOUTS is a list or dict
    assert set(layouts) <= known, \
        f"unknown layout ids: {set(layouts) - known}"
    assert len(set(layouts)) >= 4, "a 12-slide deck should use varied layouts"
    assert schema.validate_project({**project, "slides": slides}) == []


def test_generator_layout_catalog():
    gen = _need("generator")
    # LAYOUTS may be a list of ids or a dict of id -> metadata.
    ids = set(gen.LAYOUTS)
    assert len(ids) == 13, f"expected 13 layouts, got {len(ids)}: {sorted(ids)}"
    for lid in ("cover", "checklist", "thank-you", "timeline",
                "stats-dashboard", "references"):
        assert lid in ids, f"layout {lid!r} missing from LAYOUTS"


# ---------------------------------------------------------------- themes

def test_all_six_themes_have_required_keys():
    themes = _need("themes")
    expected_ids = {"emerald-ivory", "forest-cream", "dark-green-gold",
                    "navy-white", "charcoal-gold", "pastel-academic"}
    listed = themes.list_themes()
    # list_themes() may return ids or dicts carrying an "id" key.
    got = {t["id"] if isinstance(t, dict) else t for t in listed}
    assert expected_ids <= got, f"missing theme ids: {expected_ids - got}"
    required = {"name", "primary", "secondary", "accent", "background",
                "surface", "text", "muted", "chart",
                "heading_font", "body_font"}
    for tid in expected_ids:
        t = themes.get_theme(tid)
        assert required <= set(t), f"theme {tid} missing keys: {required - set(t)}"
        assert isinstance(t["chart"], list) and len(t["chart"]) == 5, \
            f"theme {tid} chart palette must have 5 colors"


# ---------------------------------------------------------------- sample

def test_sample_deck_shape():
    sample = _need("sample")
    project = sample.build_sample_project()
    assert project["theme"] == "dark-green-gold"
    assert project["status"] == "ready"
    slides = project["slides"]
    assert len(slides) == 30, f"sample deck must have 30 slides, got {len(slides)}"

    def has(etype=None, layout=None):
        out = 0
        for s in slides:
            if layout and s.get("layout") != layout:
                continue
            for e in s.get("elements", []):
                if etype is None or (e.get("type") or "").lower() == etype:
                    out += 1
        return out

    assert has("table") >= 1, "sample deck must include tables"
    assert has(layout="checklist") >= 1, "sample deck must include checklists"
    noted = sum(1 for s in slides if (s.get("notes") or "").strip())
    assert noted >= 5, f"sample deck should carry notes, found {noted}"
    assert "food safety" in project["title"].lower()
