"""Shared fixtures for the Aesthetic AI Studio test suite.

Fixtures build contract-shaped projects/themes locally so export tests do
not depend on the sibling agents' modules. Contract-dependent tests import
those modules defensively and pytest.skip() when they are missing.
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


@pytest.fixture()
def theme():
    return {
        "name": "Dark Green Gold",
        "primary": "#0B3D2E",
        "secondary": "#14532D",
        "accent": "#C9A227",
        "background": "#FFFFFF",
        "surface": "#F4F1E8",
        "text": "#1A1A1A",
        "muted": "#6B7280",
        "chart": ["#0B3D2E", "#C9A227", "#14532D", "#6B7280", "#D6C68A"],
        "heading_font": "Georgia",
        "body_font": "Calibri",
    }


def _text(eid, role, text, x=80, y=40, w=840, h=80, **kw):
    el = {"id": eid, "type": "text", "role": role, "text": text,
          "x": x, "y": y, "w": w, "h": h}
    el.update(kw)
    return el


@pytest.fixture()
def project():
    """A realistic multi-slide deck exercising every element type."""
    slides = []
    slides.append({
        "id": "s-cover", "layout": "cover",
        "elements": [
            _text("e1", "kicker", "EVERYDAY FOOD SCIENCE", y=120, h=40,
                  align="center"),
            _text("e2", "title", "Food Safety & Hygiene Workshop",
                  y=170, h=140, align="center"),
            _text("e3", "subtitle", "For hospital canteens and institutions",
                  y=320, h=60, align="center"),
            {"id": "e4", "type": "shape", "shape": "rect",
             "x": 420, "y": 400, "w": 160, "h": 10, "fill": "#C9A227"},
        ],
        "notes": "Welcome the Medical Officers and inspection officials.",
    })
    slides.append({
        "id": "s-points", "layout": "title-content",
        "elements": [
            _text("e5", "heading", "Five Keys to Safer Food", h=70),
            _text("e6", "body",
                  "• Keep clean: wash hands and surfaces\n"
                  "- Separate raw and cooked foods\n"
                  "• Cook thoroughly to safe temperatures\n"
                  "• Keep food at safe temperatures\n"
                  "• Use safe water and raw materials",
                  y=130, h=320),
            {"id": "e7", "type": "table",
             "rows": [["Food", "Safe core temp"],
                      ["Poultry", "75 °C"],
                      ["Minced meat", "70 °C"],
                      ["Fish", "63 °C"],
                      ["Reheated food", "75 °C"]],
             "x": 560, "y": 130, "w": 360, "h": 200},
        ],
        "notes": "Walk through each key with a canteen example.",
    })
    slides.append({
        "id": "s-check", "layout": "checklist",
        "elements": [
            _text("e8", "heading", "Daily Hygiene Checklist", h=70),
            _text("e9", "body",
                  "• Floors and drains cleaned and disinfected\n"
                  "• Handwash stations stocked\n"
                  "• Fridge temperatures logged (≤ 5 °C)\n"
                  "• Pest control points inspected",
                  y=130, h=320),
            {"id": "e10", "type": "image", "alt": "inspector checking fridge",
             "prompt": "food inspector with thermometer",
             "x": 560, "y": 130, "w": 360, "h": 220},
        ],
        "notes": "",
    })
    # filler content slides so exports exceed the 10KB/5KB honesty thresholds
    for i in range(9):
        slides.append({
            "id": f"s-fill-{i}", "layout": "title-content",
            "elements": [
                _text(f"ef{i}a", "heading",
                      f"Module {i + 1}: Food Safety in Practice", h=70),
                _text(f"ef{i}b", "body", "\n".join(
                    f"• Detailed guidance point {k} for module {i + 1}, "
                    f"covering hygiene practice and monitoring"
                    for k in range(1, 6)), y=130, h=330),
                {"id": f"ef{i}c", "type": "shape", "shape": "line",
                 "x": 80, "y": 480, "w": 840, "h": 0, "line": "#C9A227"},
            ],
            "notes": f"Speaker notes for module {i + 1}.",
        })
    slides.append({
        "id": "s-thanks", "layout": "thank-you",
        "elements": [
            _text("e11", "title", "Thank You", y=180, h=120, align="center"),
            _text("e12", "body", "Questions & Discussion",
                  y=320, h=60, align="center"),
        ],
        "notes": "Invite questions from the committee.",
    })
    return {
        "id": "proj-test-1",
        "title": "Food Safety & Hygiene Workshop",
        "instructions": "Executive training deck",
        "purpose": "training",
        "audience": "Medical Officers and inspection officials",
        "knowledge_level": "mixed",
        "slide_count": len(slides),
        "theme": "dark-green-gold",
        "slide_size": "16:9",
        "provider": {"kind": "offline", "model": "offline"},
        "status": "ready",
        "outline": [],
        "slides": slides,
        "created": "2026-10-19",
        "updated": "2026-10-19",
    }
