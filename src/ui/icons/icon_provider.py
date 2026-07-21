"""
Module: icon_provider.py
─────────────────────────
Purpose: Renders vendored MingCute SVG icons (see `mingcute/*.svg`) into
themeable `QIcon` instances.

Architectural Role:
Acts as the only place in CS4S that touches SVG rendering. Every window
requests icons through `get_icon()` rather than embedding raw SVG or,
critically, emoji/Unicode glyphs directly in widget code.

The vendored assets are the real MingCute icon set (Apache-2.0 licensed,
https://github.com/mingcute-design/mingcute-icons) — see
`mingcute/ATTRIBUTION.md`. Each file ships with a single fixed brand fill
color (`#09244B`) on the icon's visible path and `fill="none"` on the
invisible 24x24 frame path; `get_icon()` substitutes that fixed fill for
the requested theme color so the same vendored file works on light/dark
themes and on filled accent buttons.

Responsibilities:
- Load a vendored MingCute SVG file by name and substitute its fill color.
- Rasterize at 2x for crisp rendering on standard and HiDPI displays.
- Cache rendered icons per (name, color, size) to avoid redundant file I/O
  and SVG parsing.

Expected Collaborators:
- `src.ui.launcher`, `src.ui.client_window`, `src.ui.server_window`,
  `src.ui.widgets.*` (all icon-bearing widgets).
"""

import logging
import re
from pathlib import Path

from PyQt6.QtCore import QByteArray, QSize, Qt
from PyQt6.QtGui import QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer

_ICONS_DIR = Path(__file__).parent / "mingcute"

# The fixed brand fill color MingCute ships in every vendored SVG.
_SOURCE_FILL = re.compile(r'fill="#09244B"', re.IGNORECASE)

_source_cache: dict[str, str] = {}
_icon_cache: dict[tuple[str, str, int], QIcon] = {}


def _load_source(name: str) -> str | None:
    if name in _source_cache:
        return _source_cache[name]
    path = _ICONS_DIR / f"{name}.svg"
    if not path.exists():
        logging.warning("Missing vendored icon: %s", name)
        return None
    svg = path.read_text(encoding="utf-8")
    _source_cache[name] = svg
    return svg


def get_icon(name: str, color: str = "#2D3436", size: int = 18) -> QIcon:
    """
    Renders a named MingCute icon as a themeable QIcon.

    Args:
        name: The glyph key (a filename under `src/ui/icons/mingcute/`,
            without extension — e.g. "upload", "flask", "arrow-left").
        color: A hex color string substituted for the icon's fill.
        size: The logical icon size in pixels (rendered at 2x for HiDPI).

    Returns:
        A `QIcon` ready to attach to any `QAbstractButton`, `QAction`, or
        similar.

    Side Effects:
        Reads the vendored SVG file from disk on first use per name
        (cached afterwards); no network access.

    Failure Behavior:
        Returns a blank `QIcon` if the icon name has no matching vendored
        file, rather than raising — a missing icon should degrade
        gracefully, not crash the window that requested it.
    """
    key = (name, color, size)
    if key in _icon_cache:
        return _icon_cache[key]

    source = _load_source(name)
    if source is None:
        return QIcon()

    svg = _SOURCE_FILL.sub(f'fill="{color}"', source)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))

    scale = 2
    pixmap = QPixmap(QSize(size * scale, size * scale))
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(scale)

    icon = QIcon(pixmap)
    _icon_cache[key] = icon
    return icon
