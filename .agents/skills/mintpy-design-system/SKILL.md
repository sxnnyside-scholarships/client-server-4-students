---
name: mintpy-design-system
description: Extend the CS4S (Client-Server 4 Students) PyQt6 desktop app while preserving the MintPy design system's visual and interaction consistency. Use when adding or modifying any UI in this repository — new windows, dialogs, buttons, panels, or Lab View features.
---

# MintPy Design System — CS4S

This skill applies **exclusively to Client-Server 4 Students (CS4S)**, a PyQt6
educational networking laboratory. MintPy is not a general-purpose design system —
do not generalize its rules beyond this codebase, port it into other projects, or
treat it as CS4S's brand/logo. CS4S is the product; MintPy is the internal design
system that styles it.

The full specification lives in [`docs/DESIGN_SYSTEM.md`](../../docs/DESIGN_SYSTEM.md).
Read it before any non-trivial UI change. This skill summarizes the operational rules
an agent must follow when writing code.

## The one-sentence test

Before adding any visual element, ask: **does this read as "mint the herb" (fresh,
calm, rounded, restrained) or as "generic SaaS gradient dashboard"?** If you can't
articulate why a gradient/color/shape is specifically MintPy and not interchangeable
with any other product's dashboard, don't add it. Two guardrails that keep this
honest:
- Every gradient stays inside the mint family (soft `#A9E8D5`/`#3E8C79` → deep
  `#2F9C86`/`#1B6F5E`, per theme). A second, unrelated accent hue "for contrast"
  (violet, cyan, anything outside mint/sage) is prohibited — it reads as generic
  two-tone SaaS theater, not identity.
- The `leaf`/`grass` icons are reserved for empty states only — never a repeated
  decorative pattern, and never the CS4S application icon/logomark.

## Before touching any UI file

1. Identify the theme tokens you need from `src/ui/themes/tokens.py` (`icon_color`,
   `mint_gradient`, `sage_color`, `status_color`, `surface_colors`) and the two
   stylesheets in `src/ui/themes/` — never invent a new hex color inline.
2. Identify whether the control needs an icon. If it triggers an action, it does.
   Check `src/ui/icons/mingcute/` for an existing vendored icon before adding one.
3. Identify every user-facing string the change introduces. Each one needs a locale
   key in **both** `src/localization/en.json` and `src/localization/es.json` before
   the change is complete.
4. Identify whether the control is one of the atomic components in §"Atomic
   components" below. If it is a button, checkbox, or text input, it must go through
   the shared custom-painted component — never a bare `QPushButton`/`QCheckBox`/
   `QLineEdit` styled only with QSS. That gap (layout changes but the atoms stay
   native Qt) is the single most common way a change quietly breaks MintPy's identity.

## Hard rules (violating any of these is a regression, not a style preference)

### No hardcoded strings
Every string the user can see — button text, tooltip, dialog title, dialog body,
placeholder text, dynamically-formatted status text — must come from
`LocaleManager.get(key, **kwargs)`. Never write:
```python
QPushButton("Force Drop Client")            # WRONG
QMessageBox.question(self, "Confirm", f"Delete '{name}'?")   # WRONG
t("some_key") or "Fallback Text"            # WRONG — hides missing translations
```
If a key is missing, `LocaleManager` renders `[key]` — that visible failure mode is
correct and intentional. Do not paper over it with an `or "fallback"` pattern.

### No emojis, no decorative Unicode glyphs
No 🎉/▶/◀/↑ or similar in code or in locale JSON strings. Every action gets a real
icon from `src.ui.icons.icon_provider.get_icon(name, color, size)`.

### Icons: how to add and use them
```python
from src.ui.icons.icon_provider import get_icon
from src.ui.themes.tokens import icon_color

theme_name = self.config.get("theme", "mint_light")   # already stored as self._theme_name in windows
btn.setIcon(get_icon("upload", icon_color(theme_name, "on-accent")))
btn.setIconSize(QSize(16, 16))
```
- Role `"on-accent"` for icons on a filled button (white). `"default"` for icons on
  neutral surfaces (secondary-text gray). `"muted"` for disabled controls.
- If the action needs a glyph that doesn't exist yet in `src/ui/icons/mingcute/`,
  find the matching icon in the real MingCute set
  (https://github.com/mingcute-design/mingcute-icons, `svg/<category>/<name>_line.svg`),
  download it, verify it uses the same single-fill-color pattern (`fill="#09244B"` on
  the visible path, `fill="none"` on the frame path — check with
  `grep -o 'fill="[^"]*"' file.svg | sort -u`), save it as
  `src/ui/icons/mingcute/<cs4s-name>.svg`, and add a row to
  `src/ui/icons/mingcute/ATTRIBUTION.md`. Never hand-draw a substitute icon.

### Atomic components — never bare Qt widgets
MintPy defines a border-radius **scale** (`xs` 5px / `sm` 8px / `md` 10px / `lg`
14px — see `docs/DESIGN_SYSTEM.md § 4.4`) and every interactive atom is custom-painted
against it:

| Widget you need | Use | Radius step |
|---|---|---|
| Any clickable action | The shared Button component (Primary/Secondary/Danger/icon-only) | `md` (10px) |
| A binary lifecycle action (start/stop, connect/disconnect) | `src.ui.widgets.toggle_button.ToggleActionButton` | `md` (10px) |
| A boolean setting | The shared Checkbox component | `xs` (5px) |
| Text/numeric entry | Text input / spinbox styling (unified 8px radius + focus glow) | `sm` (8px) |
| A content panel | `src.ui.widgets.section_card.SectionCard` (never `QGroupBox`) | `lg` (14px) |

If you reach for a raw `QPushButton()`/`QCheckBox()`/`QLineEdit()` styled only through
a QSS object-name selector, stop — that's the exact gap that makes a screen "look
like PyQt with mint paint" even after the surrounding layout is redesigned.

### Tooltips are a teaching surface, not accessibility filler
Every icon-only or non-obvious control needs a `setToolTip()` call, and the copy must
explain the **networking concept or wire behavior**, not restate the label. One
sentence max — longer explanations belong in the Protocol Inspector's
command-explanation panel.

### Layout: nav rail + mode switch, not a toolbar
Client and Server windows are built from `src.ui.widgets.nav_rail.NavRail` (identity,
`StatusBadge`, primary form, mode switcher) plus a central content area that swaps
entire modes via a `QStackedWidget` — see `docs/DESIGN_SYSTEM.md § 3` and § 6.1–6.2.
Do not add a new top toolbar row or a splitter-based collapsible panel; if a feature
is educational/advanced, register it as a new nav rail mode instead of squeezing it
into the primary view.

### Consolidate before adding a panel
Before adding a new `SectionCard`, check whether an existing panel already shows
materially the same information. Two panels are redundant if one is a strict subset
of what the other displays (see `docs/DESIGN_SYSTEM.md § 3`, "Consolidate before you
add a panel").

### Empty states are required, not optional
Any list/table/log that can legitimately render with zero items needs a real empty
state (`leaf`/`grass` icon, muted tint, one localized sentence) — never a bare
rectangle. See `docs/DESIGN_SYSTEM.md § 6.5`.

### Motion: rare, brief, tied to a real state change
Use the exact durations in `docs/DESIGN_SYSTEM.md § 4.7` (nav highlight 150ms,
button hover 100ms, button press 80ms, checkbox 120ms, mode-swap cross-fade 150ms).
Do not add motion beyond that table without confirming it survives "an hour of real
use" (§1 of the design doc) — no loops, nothing that keeps drawing the eye back to
itself after the first time it's seen.

### Accessibility checklist for any new control
- Reachable by Tab in a logical order; every rail action also gets a File/View/Help
  menu-bar path with a mnemonic.
- Icon-only buttons still have a `setToolTip()`.
- Text/background contrast matches the palette pairs in `docs/DESIGN_SYSTEM.md § 4.1`
  in both themes.

## Workflow for adding a new screen or panel

1. Reuse the existing shell: `NavRail` + mode-switched central content (§ 3). Don't
   invent a new top-level layout pattern.
2. If the feature is educational/advanced, register it as a Lab View mode rather than
   adding it to the primary view.
3. Build every control from the atomic component table above — never a bare Qt widget.
4. Wire every button through: icon (theme-aware color) → locale text → tooltip →
   signal connection, in that order.
5. Add any new locale keys to **both** `en.json` and `es.json` in the same change.
6. If you introduced a new reusable component, add it to
   `docs/DESIGN_SYSTEM.md § 6 Product Component Catalog` in the same change.
7. Run `pytest tests/ -q` — GUI tests in `tests/gui/` catch missing widgets or broken
   signal wiring; there is no separate "design system test," consistency is enforced
   by following this skill, not by a linter.
