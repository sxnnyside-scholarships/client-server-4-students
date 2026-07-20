# MintPy Design System

**The canonical visual language of Client-Server 4 Students (CS4S).**

MintPy is not a general-purpose UI framework, and it is not the product's brand. CS4S is
the product — a desktop networking laboratory built with PyQt6. MintPy is the internal
design system that gives its Launcher, Client, and Server console one coherent,
professional identity. Every rule here exists to serve that one application; nothing in
this document should ever appear as a logo, splash screen, or marketing mark for CS4S
itself.

---

## 1. Design Philosophy

CS4S teaches sockets, protocols, and client-server architecture, in sessions that often
run long (a lab exercise, a full class period). Two things have to be true at once:

1. **It has to feel fresh, not sterile.** "Mint" is not a hex code choice — it's the
   herb: calm, organic, a little alive. That shows up as rounded, soft-edged surfaces,
   a color palette that stays inside one botanical family (mint → a warmer "sage"
   relative, never an unrelated accent hue bolted on for "pop"), and restrained
   decorative touches (a leaf glyph in an empty state, never on every screen at once).
2. **It has to survive an hour of real use.** Freshness is not an excuse for
   saturation, motion, or clutter that tires the eyes. Colors stay pastel/muted rather
   than neon, decoration is rare and purposeful, and motion is brief and calm (see
   §4.7) — never a loop, never something that draws the eye back to itself once you've
   already seen it.

MintPy also has to survive being built entirely out of PyQt6 widgets. A design system
that only changes layout and leaves `QCheckBox`, `QPushButton`, and `QLineEdit` in their
native OS skin isn't a design system — it's a color swap with better spacing. **Every
interactive atom is custom-painted** (see §5), not just the panels around them.

## 2. Interaction Principles

- **Discoverability over memorization.** Every icon-only or ambiguous control has a
  tooltip (see §8). Hover states exist everywhere a click is possible.
- **Immediate feedback.** State transitions (connecting → authenticated, idle →
  transferring) are reflected within one UI tick — no silent waiting.
- **Reversible by default.** Destructive actions (delete, remove user, force-drop) are
  confirmed or use the danger visual treatment; nothing destructive is a single
  accidental click away without a distinguishing color.
- **Keyboard parity with mouse.** Primary actions (e.g. directory refresh via `F5`) are
  reachable without a pointer wherever the underlying workflow supports it. A real
  menu bar (§3) backs every rail action with a keyboard/menu path.
- **One state, one control.** Two buttons that are never both meaningfully clickable at
  once (Start/Stop Server, Connect/Disconnect) are a single toggle control, not a pair
  competing for the same space.

## 3. Layout Philosophy

- **The window is the canvas, not a dialog.** CS4S is a desktop tool used for real
  work, not a utility popup. The Client and Server windows open **maximized** by
  default — the size is a consequence of the content being real information density,
  not an arbitrary pixel dimension.
- **A persistent nav rail, not a toolbar.** Both windows are built from a fixed-width
  left rail (identity, live status, the primary connect/start form, and a mode
  switcher) plus a central content area that fills the rest of the window. This
  replaces a horizontal strip of mixed-purpose buttons with a real hierarchy: identity
  at the top, state always visible, actions grouped, navigation explicit.
- **Lab View is a mode, not a panel.** Switching to Lab View swaps the *entire*
  central content (via the mode switcher), so it gets the whole window's worth of
  space. It never shares a splitter with the primary workflow and can never squeeze it
  down to a sliver.
- **A real menu bar backs the rail.** File / View / Help give every rail action a
  standard desktop-app path (and a keyboard mnemonic), and consolidate window-level
  actions (Back, Exit, About) that don't need to live in the rail itself.
- **Consolidate before you add a panel.** Two panels that show materially the same
  information (e.g. a bare "Connected Clients" address list next to a "Socket States"
  list showing the same addresses plus a state) get merged into one. A new panel is
  only justified when it shows something no existing panel already shows.
- **Empty is a state, not an absence.** Any list, table, or log that can legitimately
  be empty (no clients yet, no files, no log lines) renders a real empty state — an
  icon plus one calm sentence — never a bare white rectangle.

## 4. Design Tokens

MintPy's source of truth is split deliberately: `.qss` files own styling expressible in
Qt Style Sheets; [`src/ui/themes/tokens.py`](../src/ui/themes/tokens.py) owns values
Python must read directly (custom-painted widgets have no access to the active
stylesheet), and both are kept in sync with this document.

### 4.1 Color Palette

| Token | Light | Dark | Usage |
|---|---|---|---|
| Mint (primary accent) | `#45B7A0` | `#45B7A0` | Primary actions, focus, selection, "on" state |
| Mint soft (gradient stop) | `#A9E8D5` | `#3E8C79` | Gradient start — rail seam, active nav pill, brand mark |
| Mint deep (gradient stop) | `#2F9C86` | `#1B6F5E` | Gradient end — same surfaces as above |
| Sage (Lab View / advanced accent) | `#7C9473` | `#9CB88F` | Marks Lab View panels as "a different herb," never an unrelated hue |
| Background | `#F7F8FA` | `#1B1F2B` | Window background |
| Surface | `#FFFFFF` | `#232838` | Cards, inputs, tables |
| Text | `#2D3436` | `#E8ECEF` | Body text |
| Text secondary | `#636E72` | `#8A94A6` | Captions, form labels, icon default tint |
| Text muted | `#B2BEC3` | `#4A5568` | Disabled text, muted icon tint |
| Border | `#DFE6E9` | `#2E3548` | Control borders |
| Status: connecting | `#E1A73C` | `#E8B84B` | Status badge, transitional states |
| Status: error | `#D63031` | `#E17055` | Status badge, danger buttons |

**MintPy never introduces a hue outside this family.** Every gradient runs mint-soft →
mint-deep. Sage exists solely to distinguish Lab View surfaces and reads as a relative
of mint (lower saturation, warmer), not a second brand color. A second, unrelated
accent hue (violet, cyan, anything outside the mint/sage family) is prohibited: it is
the single fastest way to make an interface read as generic-SaaS gradient theater
instead of a considered, single-family palette.

### 4.2 Typography

| Role | Family | Size |
|---|---|---|
| Body | "Inter", "Segoe UI", "SF Pro Text", system-ui, sans-serif | 13px |
| Caption / form label | same | 11px |
| Title | same | 24px, weight 700 |
| Monospace (logs, protocol console, RTT, throughput) | "JetBrains Mono", "Cascadia Code", "Fira Code", "Menlo", monospace | 12–13px |

### 4.3 Iconography

[`src/ui/icons/`](../src/ui/icons/) vendors real **MingCute** icons (Apache-2.0; see
`mingcute/ATTRIBUTION.md` for every source path) — never hand-drawn approximations,
never emoji, never decorative Unicode glyphs (▶ ◀ ↑). Two icons (`leaf`, `grass`) are
the system's **decorative accent set**: used only inside empty states and similarly
quiet, single-instance moments, never as a repeated pattern and never as the CS4S
application icon/logomark — CS4S's identity is the product; MintPy's leaf is an
internal design accent, not a brand mark. Icons are tinted per-theme/role via
`tokens.icon_color(theme, role)` — `default` (secondary-text gray), `on-accent`
(white), `muted` (disabled).

### 4.4 Border Radius Scale

A real scale, not ad-hoc numbers per widget:

| Step | Radius | Used by |
|---|---|---|
| xs | 5px | Checkbox |
| sm | 8px | Inputs, spinboxes, tooltips, scrollbar thumbs |
| md | 10px | Buttons (all variants), active nav pill |
| lg | 14px | SectionCard, other primary content panels |

Every new component's radius comes from this scale — never an arbitrary value picked
to "look right" in isolation.

### 4.5 Spacing Scale

8px base unit (`tokens.SPACING_UNIT`). Layout margins/spacing resolve to `4, 8, 12, 16,
20, 24` — never an arbitrary value outside this scale.

### 4.6 Elevation & Shadows

Depth comes from soft, accent-tinted shadows (`QGraphicsDropShadowEffect`), not flat
borders alone: SectionCard uses a mint/sage-tinted shadow (28px blur, 6px y-offset,
~18% opacity) standing in for a hard edge. Inputs gain a soft mint glow only on focus
(a lighter version of the same technique) — depth appears when something becomes
active, not as permanent chrome.

### 4.7 Animation Timing

Motion is rare, brief, and always tied to a real state change — never decorative or
looping:

| Interaction | Duration | Easing |
|---|---|---|
| Nav rail active-item highlight fade-in | 150ms | Ease-out |
| Button hover background fade | 100ms | Ease-out |
| Button press | 80ms | Scale to 97%, ease-in |
| Checkbox check/uncheck | 120ms | Scale + fade, ease-out |
| Lab View / mode content swap | 150ms | Cross-fade |

If a future interaction needs motion beyond this table, it must justify itself against
§1's "survives an hour of use" rule before being added.

### 4.8 Window Metrics & Density

| Window | Size |
|---|---|
| Launcher | Fixed 520×430 (a deliberately dialog-sized entry point) |
| Client | Maximized on open, sane minimum size as a floor |
| Server | Maximized on open, sane minimum size as a floor |
| Rail width | 252px fixed |
| Control height | ~34px (buttons, inputs) |
| Icon size | 16px inline, 18–28px for primary launcher actions |

---

## 5. Atomic Component Layer

This is the layer that makes MintPy visible at the smallest scale — the thing that's
still wrong if only panels and layout change. Every one of these is custom-painted;
none of them is a native Qt widget wearing a stylesheet.

### 5.1 Button (Primary / Secondary / Danger / Icon-only)
- **Shape:** 10px radius (scale `md`), consistent height across all variants.
- **Primary:** Filled mint. **Danger:** Filled status-error red. **Secondary:**
  Surface fill, bordered, text-colored icon/label.
- **Interaction:** Hover fades the fill toward its "soft" tone over 100ms (not an
  instant color snap). Press scales the button to 97% over 80ms — a tactile
  micro-response, not a static state.
- **Rule:** At most one primary button per logical action group.

### 5.2 Toggle Action Button
- **Purpose:** Collapses a binary lifecycle action (Start/Stop Server, Connect/
  Disconnect) into one control instead of two competing buttons.
- **Visual:** "Off" renders as Primary (mint — safe to start); "On" renders as Danger
  (red — stopping/disconnecting is disruptive). The color *is* the state.
- **Rule:** The owning window syncs the toggle to the real backend state
  (`set_checked_silently`) — the button's checked state never lies about what's
  actually running.

### 5.3 Checkbox
- **Shape:** 5px radius (scale `xs`) — deliberately the smallest step, since it's the
  smallest control.
- **Unchecked:** A quiet outlined square, border-only. **Checked:** Mint-soft →
  mint-deep gradient fill with a white check glyph.
- **Interaction:** The check mark scales in from 80%→100% while fading in over 120ms —
  it *appears*, rather than snapping into existence. This is the single clearest
  "this is not the OS checkbox" signal in the whole system.

### 5.4 Text Input / Spinbox
- **Shape:** 8px radius (scale `sm`), unified across `QLineEdit` and `QDoubleSpinBox`.
- **Focus:** Border shifts to mint **and** a soft mint glow appears around the field
  (a lighter sibling of the SectionCard shadow technique) — focus is felt, not just
  outlined.

### 5.5 Scrollbar & Tooltip
- Both use the `sm` (8px) radius step, and mint-on-hover for the scrollbar thumb —
  every small control shares one radius step rather than picking its own value.

---

## 6. Product Component Catalog

### 6.1 NavRail
- **Purpose:** The persistent left rail shared by Client and Server — identity, live
  `StatusBadge`, the primary connect/start form, and the mode switcher.
- **Visual:** Fixed 252px column; a soft mint-gradient seam (soft→deep) traces its
  right edge instead of a flat 1px border.
- **Rule:** The rail never contains content-area widgets (file table, logs) — it is
  chrome and controls only.

### 6.2 Mode Switcher (Nav Items)
- **Purpose:** Switches the central content area between a window's modes (Files/Lab
  View on Client; Overview/Lab View on Server).
- **Visual:** The active item's background is a soft mint-gradient pill that **fades
  in** over 150ms when selected (§4.7) — the one intentionally animated moment in the
  rail, marking a real navigation event.

### 6.3 SectionCard
- **Purpose:** MintPy's primary content panel, replacing `QGroupBox`.
- **Visual:** 14px rounded corners (scale `lg`), a 3px accent bar on the left edge
  (mint for primary panels, sage for Lab View panels), soft accent-tinted shadow.

### 6.4 Status Badge
- **Purpose:** An always-visible connection/server-state indicator (dot + label) in
  the rail — replacing "no persistent state feedback, only a status-bar message that
  disappears after 8 seconds."
- **Visual:** A small color-coded dot (with a soft matching glow) plus a label; color
  comes from the Status tokens (§4.1).

### 6.5 Empty State
- **Purpose:** What an empty list/table/log renders instead of a bare rectangle.
- **Visual:** A centered `leaf` or `grass` icon (muted tint) plus one calm, localized
  sentence ("No clients connected yet.").
- **Rule:** Never used more than once on screen at a time — an empty state is a quiet
  moment, not a decorative pattern repeated across every panel.

### 6.6 Menu Bar
- **Purpose:** Standard File / View / Help menu backing the rail's actions with
  keyboard-accessible, conventional desktop-app affordances.
- **Rule:** Every menu action already exists as a rail control — the menu is a second
  path to the same action, never a place for functionality that lives nowhere else.

---

## 7. Iconography Rules

1. Every action-triggering control has an icon from `src/ui/icons/mingcute/`. No
   emoji, no decorative Unicode.
2. Icons are requested through `icon_provider.get_icon(name, color, size)` — never
   inlined as raw SVG at the call site.
3. `leaf` / `grass` are reserved for empty states only — never repeated as a pattern,
   never used as the CS4S application icon.
4. New icons are added only when CS4S gains a new distinct action or empty state —
   this stays exactly as large as the product needs.

## 8. Localization Rules

1. **No hardcoded user-facing strings, ever.** Every string is a key in
   `src/localization/en.json` and `es.json`.
2. Dynamic values interpolate via `LocaleManager.get(key, **kwargs)` — never Python
   f-strings concatenated with a translated fragment.
3. A missing key renders visibly as `[key]` rather than silently falling back to a
   hardcoded string — a visible bug beats a wrong microcopy choice.
4. Every new locale key is added to **both** `en.json` and `es.json` in the same change.

## 9. Tooltip Philosophy

1. Every icon-only or non-obvious control has a tooltip.
2. A tooltip explains what happens on the wire, not just the UI action.
3. One sentence. Longer explanations belong in the Protocol Inspector's
   command-explanation panel.
4. Tooltip copy lives in locale files under a `tooltip_*` key.

## 10. Accessibility

- **Keyboard navigation:** Tab order follows visual layout order. `F5` refreshes the
  file listing. Every rail action also has a menu-bar path with a mnemonic.
- **Focus states:** Inputs render a visible mint border plus glow on focus (§5.4).
- **Contrast:** Text/background pairs meet WCAG AA in both themes.
- **Scalable typography:** All sizes are stylesheet `px` values; icons are SVG,
  rasterized at 2x for HiDPI.
- **Interaction targets:** Controls maintain ~34px height even icon-only, meeting
  WCAG's 24×24px minimum.
