"""
Module: tokens.py
──────────────────
Purpose: Canonical MintPy design tokens shared between QSS themes and Python
code that can't be expressed in a stylesheet (icon tint colors, spacing
constants used in manual layout code, etc).

Architectural Role:
The `.qss` files in this package are the source of truth for widget styling,
but a few values (icon stroke color, tooltip copy formatting) are needed at
construction time in Python, before any stylesheet is applied. This module
mirrors the relevant subset of `docs/DESIGN_SYSTEM.md` so both stay in sync.

Responsibilities:
- Expose icon tint colors per theme (light/dark) and per semantic role
  (default, on-accent, danger).
- Expose MintPy's mint gradient family (soft → deep) and the "sage" tone
  used to distinguish Lab View / advanced panels — both stay in the mint/
  botanical family; MintPy never introduces an unrelated accent hue.
- Expose the 8px spacing grid unit used across manual layout code.

Non-Responsibilities (Anti-Goals):
- It does NOT restate the full color palette (that lives in the .qss files
  and in docs/DESIGN_SYSTEM.md) — only the values Python code must read
  directly. Wait, with Epic 9, PALETTES is added here to act as the single source
  of truth for the template engine.
"""

PALETTES = {
    "mint_light": {
        "@ACCENT@": "#45B7A0",
        "@ACCENT_HOVER@": "#3CA38E",
        "@ACCENT_PRESSED@": "#34907D",
        "@ACCENT_MUTED@": "#A8DDD3",
        "@ACCENT_SURFACE@": "#E6F5F2",
        "@ACCENT_SURFACE_HOVER@": "#CCEBE5",
        "@ACCENT_SURFACE_PRESSED@": "#B3E0D8",
        "@BACKGROUND@": "#F7F8FA",
        "@SURFACE@": "#FFFFFF",
        "@SURFACE_RAISED@": "#F1F3F5",
        "@SURFACE_HOVER@": "#E9ECEF",
        "@SURFACE_PRESSED@": "#DEE2E6",
        "@SURFACE_DISABLED@": "#F1F3F5",
        "@SURFACE_ALT@": "#F8F9FA",
        "@SURFACE_ALT_HOVER@": "#E9ECEF",
        "@SURFACE_INSET@": "#F1F3F5",
        "@TEXT@": "#2D3436",
        "@TEXT_SECONDARY@": "#636E72",
        "@TEXT_MUTED@": "#B2BEC3",
        "@TEXT_DISABLED@": "#ADB5BD",
        "@BORDER@": "#DFE6E9",
        "@BORDER_HOVER@": "#CED4DA",
        "@BORDER_DISABLED@": "#F1F3F5",
        "@DANGER@": "#D63031",
        "@DANGER_HOVER@": "#B71C1C",
    },
    "mint_dark": {
        "@ACCENT@": "#45B7A0",
        "@ACCENT_HOVER@": "#3CA38E",
        "@ACCENT_PRESSED@": "#34907D",
        "@ACCENT_MUTED@": "#1F5C4F",
        "@ACCENT_SURFACE@": "#1E332E",
        "@ACCENT_SURFACE_HOVER@": "#172824",
        "@ACCENT_SURFACE_PRESSED@": "#111D1A",
        "@BACKGROUND@": "#1B1F2B",
        "@SURFACE@": "#232838",
        "@SURFACE_RAISED@": "#2A3042",
        "@SURFACE_HOVER@": "#3A4260",
        "@SURFACE_PRESSED@": "#1E2538",
        "@SURFACE_DISABLED@": "#1E2233",
        "@SURFACE_ALT@": "#262D40",
        "@SURFACE_ALT_HOVER@": "#1F3D37",
        "@SURFACE_INSET@": "#1E2436",
        "@TEXT@": "#E8ECEF",
        "@TEXT_SECONDARY@": "#8A94A6",
        "@TEXT_MUTED@": "#4A5568",
        "@TEXT_DISABLED@": "#4A5568",
        "@BORDER@": "#2E3548",
        "@BORDER_HOVER@": "#4A5568",
        "@BORDER_DISABLED@": "#262D3D",
        "@DANGER@": "#E17055",
        "@DANGER_HOVER@": "#D63031",
    },
}

# 8px base spacing unit — see docs/DESIGN_SYSTEM.md § Spacing Scale.
SPACING_UNIT = 8

# Border radius scale (xs=5, sm=8, md=10, lg=14)
RADIUS = {
    "xs": 5,
    "sm": 8,
    "md": 10,
    "lg": 14,
}

# MintPy's gradient family: a soft pastel mint fading into a deeper mint —
# used for the nav rail's active-item pill, the brand mark, and the rail's
# edge seam. Every gradient in MintPy stays inside this one family; there is
# no second, unrelated hue standing in for "depth" or "advanced." See
# docs/DESIGN_SYSTEM.md § 4.1.
MINT_GRADIENT = {
    "mint_light": ("#A9E8D5", "#2F9C86"),
    "mint_dark": ("#3E8C79", "#1B6F5E"),
}

# "Sage" — a warmer, quieter relative of mint (same botanical family, lower
# saturation) used only to distinguish Lab View / advanced panels from the
# primary surface. It reads as "a different herb," not "a different brand."
SAGE_ACCENT = {
    "mint_light": "#7C9473",
    "mint_dark": "#9CB88F",
}

# Status-badge colors, keyed by theme then connection/server state.
STATUS_COLORS = {
    "mint_light": {
        "offline": "#B2BEC3",
        "connecting": "#E1A73C",
        "online": "#45B7A0",
        "error": "#D63031",
    },
    "mint_dark": {
        "offline": "#4A5568",
        "connecting": "#E8B84B",
        "online": "#45B7A0",
        "error": "#E17055",
    },
}

# Surface/border colors needed by custom-painted widgets (SectionCard,
# NavRail) that draw their own background/border via QPainter instead of
# QSS — a QPainter has no access to the active stylesheet, so these must be
# read directly from Python. Kept in exact sync with the "Surface"/"Border"
# rows of the palette table in docs/DESIGN_SYSTEM.md.
SURFACE_COLORS = {
    "mint_light": {"surface": "#FFFFFF", "border": "#DFE6E9", "background": "#F7F8FA"},
    "mint_dark": {"surface": "#232838", "border": "#2E3548", "background": "#1B1F2B"},
}

# Icon tint colors, keyed by theme name then semantic role.
# "default"   — icon sits on a neutral/surface background (secondary text tone).
# "on-accent" — icon sits on a filled mint/danger button (white).
# "muted"     — icon sits on a disabled control.
ICON_COLORS = {
    "mint_light": {
        "default": "#636E72",
        "on-accent": "#FFFFFF",
        "muted": "#B2BEC3",
    },
    "mint_dark": {
        "default": "#8A94A6",
        "on-accent": "#FFFFFF",
        "muted": "#4A5568",
    },
}


def text_color(theme_name: str, variant: str = "primary") -> str:
    palette = PALETTES.get(theme_name, PALETTES["mint_light"])
    key_map = {
        "primary": "@TEXT@",
        "secondary": "@TEXT_SECONDARY@",
        "muted": "@TEXT_MUTED@",
        "disabled": "@TEXT_DISABLED@",
        "on-accent": "@TEXT_ON_ACCENT@",
    }
    key = key_map.get(variant, "@TEXT@")
    return palette.get(key, palette["@TEXT@"])


def icon_color(theme_name: str, role: str = "default") -> str:
    """
    Resolves the correct icon stroke color for the active theme and role.

    Args:
        theme_name: One of `ThemeManager.THEMES` keys (e.g. "mint_light").
        role: One of "default", "on-accent", "muted".

    Returns:
        A hex color string.

    Side Effects:
        None.

    Failure Behavior:
        Falls back to `mint_light`/`default` if the theme or role is unknown,
        rather than raising — a wrong icon tint is a cosmetic issue, not
        worth crashing a window over.
    """
    theme = ICON_COLORS.get(theme_name, ICON_COLORS["mint_light"])
    return theme.get(role, theme["default"])


def accent_color(theme_name: str, variant: str = "default") -> str:
    """
    Resolves the accent color variants for the active theme.

    Args:
        theme_name: One of `ThemeManager.THEMES` keys.
        variant: "default", "hover", "pressed", "muted".

    Returns:
        A hex color string.
    """
    palette = PALETTES.get(theme_name, PALETTES["mint_light"])
    key_map = {
        "default": "@ACCENT@",
        "hover": "@ACCENT_HOVER@",
        "pressed": "@ACCENT_PRESSED@",
        "muted": "@ACCENT_MUTED@",
    }
    key = key_map.get(variant, "@ACCENT@")
    return palette.get(key, palette["@ACCENT@"])


def mint_gradient(theme_name: str) -> tuple[str, str]:
    """
    Resolves the (soft, deep) mint gradient stop pair for the active theme.

    Args:
        theme_name: One of `ThemeManager.THEMES` keys.

    Returns:
        A `(soft_hex, deep_hex)` tuple, meant to be used as the two stops of
        a linear gradient — never as two unrelated flat colors.

    Side Effects:
        None.

    Failure Behavior:
        Falls back to `mint_light` if the theme is unknown.
    """
    return MINT_GRADIENT.get(theme_name, MINT_GRADIENT["mint_light"])


def sage_color(theme_name: str) -> str:
    """
    Resolves MintPy's "sage" tone — the quieter, same-family green used to
    distinguish Lab View / advanced panels from primary surfaces.

    Args:
        theme_name: One of `ThemeManager.THEMES` keys.

    Returns:
        A hex color string.

    Side Effects:
        None.

    Failure Behavior:
        Falls back to `mint_light` if the theme is unknown.
    """
    return SAGE_ACCENT.get(theme_name, SAGE_ACCENT["mint_light"])


def status_color(theme_name: str, state: str) -> str:
    """
    Resolves the status-badge color for a given connection/server state.

    Args:
        theme_name: One of `ThemeManager.THEMES` keys.
        state: One of "offline", "connecting", "online", "error".

    Returns:
        A hex color string.

    Side Effects:
        None.

    Failure Behavior:
        Falls back to `mint_light`/"offline" if the theme or state is unknown.
    """
    theme = STATUS_COLORS.get(theme_name, STATUS_COLORS["mint_light"])
    return theme.get(state, theme["offline"])


def surface_colors(theme_name: str) -> dict:
    """
    Resolves the surface/border/background triad for custom-painted widgets.

    Args:
        theme_name: One of `ThemeManager.THEMES` keys.

    Returns:
        A dict with "surface", "border", and "background" hex color keys.

    Side Effects:
        None.

    Failure Behavior:
        Falls back to `mint_light` if the theme is unknown.
    """
    return SURFACE_COLORS.get(theme_name, SURFACE_COLORS["mint_light"])


def console_colors(theme_name: str) -> dict:
    """
    Resolves the semantic text colors for the Protocol Inspector console.

    Args:
        theme_name: One of `ThemeManager.THEMES` keys.

    Returns:
        A dict with "tx", "rx", "encrypted", and "muted" hex color keys,
        guaranteed to provide >=4.5:1 contrast against the log surface.
    """
    if theme_name == "mint_dark":
        return {
            "tx": "#45B7A0",  # Accent
            "rx": "#9CB88F",  # Sage
            "encrypted": "#E8B84B",  # Status connecting (amber)
            "muted": "#8A94A6",  # Text secondary
        }
    else:
        return {
            "tx": "#2F9C86",  # Deep mint
            "rx": "#7C9473",  # Sage
            "encrypted": "#E1A73C",  # Status connecting (amber)
            "muted": "#636E72",  # Text secondary
        }
