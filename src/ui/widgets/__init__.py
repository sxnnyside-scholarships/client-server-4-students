"""
Package: src.ui.widgets
───────────────────────
Purpose: Provides reusable, self-contained GUI components that are assembled into larger windows.

Architectural Role:
Acts as a component library. By decomposing complex windows into isolated widgets, 
the UI layer remains modular, testable, and free of massive monolithic layouts.

Responsibilities:
- Provide cross-cutting structural elements (e.g., `BrandingFooter`).
- Provide educational visualizations (e.g., `ConnectionGraphWidget`, `ProtocolInspectorWidget`).

Public API:
- `common.BrandingFooter`: Standardized footer across all main windows.
- `common.LabeledInput`: Standardized input field layout.
- `graph.ConnectionGraphWidget`: Real-time topology visualizer.
- `inspector.ProtocolInspectorWidget`: Real-time byte-level protocol visualizer.

Expected Collaborators:
- `src.ui`: The main window classes consume these widgets to compose their central layouts.
"""

from .atoms import (
    MintButton,
    MintTextInput,
    MintStepper,
    MintDropdown,
    MintModeCard,
    EmptyStateWidget,
    MintCheckbox,
    MintIconButton,
    Breadcrumb,
)
