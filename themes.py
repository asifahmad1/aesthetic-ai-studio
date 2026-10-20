"""Color themes for Aesthetic AI Studio v1.

Six curated themes. Fonts are restricted to the safe cross-platform set:
Georgia, Trebuchet MS, Calibri, Arial.
"""

from __future__ import annotations

THEMES: dict[str, dict] = {
    "emerald-ivory": {
        "name": "Emerald & Ivory",
        "primary": "#0E6E52",
        "secondary": "#155E46",
        "accent": "#C9A227",
        "background": "#FDFBF4",
        "surface": "#FFFFFF",
        "text": "#1E2A24",
        "muted": "#6B7A70",
        "chart": ["#0E6E52", "#2A9D6F", "#C9A227", "#7FB69E", "#3D5A45"],
        "heading_font": "Georgia",
        "body_font": "Trebuchet MS",
    },
    "forest-cream": {
        "name": "Forest & Cream",
        "primary": "#1B4332",
        "secondary": "#2D6A4F",
        "accent": "#D8B24C",
        "background": "#FAF6EA",
        "surface": "#FFFFFF",
        "text": "#21281F",
        "muted": "#707A68",
        "chart": ["#1B4332", "#2D6A4F", "#D8B24C", "#95D5B2", "#52796F"],
        "heading_font": "Georgia",
        "body_font": "Calibri",
    },
    "dark-green-gold": {
        "name": "Dark Green & Gold",
        "primary": "#2E8B66",
        "secondary": "#1B5E43",
        "accent": "#C9A227",
        "background": "#101915",
        "surface": "#1A2B21",
        "text": "#F2EFE3",
        "muted": "#9AA79C",
        "chart": ["#C9A227", "#2E8B66", "#E8D27A", "#7FB69E", "#4C8C6B"],
        "heading_font": "Georgia",
        "body_font": "Trebuchet MS",
    },
    "navy-white": {
        "name": "Navy & White",
        "primary": "#1F3864",
        "secondary": "#2E5AAC",
        "accent": "#E8A838",
        "background": "#FFFFFF",
        "surface": "#F4F6FA",
        "text": "#1A2332",
        "muted": "#64748B",
        "chart": ["#1F3864", "#2E5AAC", "#E8A838", "#7BA7D9", "#4C6B8A"],
        "heading_font": "Georgia",
        "body_font": "Calibri",
    },
    "charcoal-gold": {
        "name": "Charcoal & Gold",
        "primary": "#8A8F96",
        "secondary": "#45484D",
        "accent": "#C9A227",
        "background": "#232527",
        "surface": "#2E3134",
        "text": "#F5F2E8",
        "muted": "#A8A49A",
        "chart": ["#C9A227", "#E8D27A", "#8A8F96", "#6B6F75", "#A8801F"],
        "heading_font": "Georgia",
        "body_font": "Arial",
    },
    "pastel-academic": {
        "name": "Pastel Academic",
        "primary": "#5E8F7B",
        "secondary": "#A8CBB8",
        "accent": "#D9A441",
        "background": "#FDF8F0",
        "surface": "#FFFFFF",
        "text": "#3A3A3A",
        "muted": "#8A8A8A",
        "chart": ["#5E8F7B", "#A8CBB8", "#D9A441", "#E8C99A", "#7FB3D5"],
        "heading_font": "Georgia",
        "body_font": "Calibri",
    },
}

_DEFAULT_THEME_ID = "emerald-ivory"


def get_theme(theme_id: str | None) -> dict:
    """Return the theme dict for an id, falling back to emerald-ivory."""
    if isinstance(theme_id, str) and theme_id in THEMES:
        return THEMES[theme_id]
    return THEMES[_DEFAULT_THEME_ID]


def list_themes() -> list[dict]:
    """Return [{id, name, swatches:[primary, accent, background]}] for all themes."""
    return [
        {
            "id": tid,
            "name": t["name"],
            "swatches": [t["primary"], t["accent"], t["background"]],
        }
        for tid, t in THEMES.items()
    ]
