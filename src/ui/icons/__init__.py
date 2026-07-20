"""
Package: src.ui.icons
──────────────────────
Purpose: The MintPy iconography set — vendored MingCute icons (Apache-2.0,
see `mingcute/ATTRIBUTION.md`) covering every action surfaced in CS4S.

Architectural Role:
Provides the single source of icon glyphs for the entire application,
replacing emoji and decorative Unicode glyphs (▶, ◀, ↑) with a consistent,
recolorable icon language.

Public API:
- `icon_provider.get_icon(name, color, size)`: Renders a named glyph as a QIcon.
"""
