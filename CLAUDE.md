# CS4S AI Guidelines

This file provides system instructions for AI coding assistants (like Claude, ChatGPT, or custom internal agents) contributing to the Client-Server 4 Students (CS4S) repository.

## 1. Core Principles
- **Educational Value First:** This is an educational networking laboratory. The source code is part of the product. Do not prioritize raw performance or "clever" one-liners if it sacrifices readability for a Computer Science student.
- **MVC Enforced:** `src/ui/` files must contain ZERO business logic. They are "Views" and must delegate all socket/network logic to the `ClientBackend` or `ServerBackend`.
- **Thread Safety:** The GUI runs on the Qt Main Thread. Network loops run on daemon background threads. You MUST use PyQt signals/slots to bridge data across these threads to prevent freezing the UI.

## 2. Technical Stack (DXQE v2 Canonical)
- **Python:** strictly `>=3.11, <3.16` (to maintain PyInstaller compatibility).
- **GUI:** `PyQt6` ONLY. Do not use PySide6 or Tkinter.
- **Dependency Management:** Managed strictly via `Poetry` (`pyproject.toml`). Do not run raw `pip install`.
- **Task Runner:** `just` (use `just build`, `just check`, `just test`, etc.)

## 3. Design System (MintPy)
- All UI modifications must use the foundational `MintPy` widgets located in `src/ui/widgets/atoms.py` (e.g., `MintButton`, `MintTextInput`).
- **DO NOT** use generic `QPushButton` or `QLineEdit` directly.
- **DO NOT** use raw CSS/QSS to handle hover/focus states; the `atoms.py` classes handle microinteractions via custom `paintEvent` overrides and `QVariantAnimation`.

## 4. Documentation Standard
- The repository follows strict documentation rules (DDAQ standard).
- Every public class and method must have a docstring explaining its responsibility.
- For complex algorithms or multi-threading boundaries, include an `## Educational Note` in the docstring to teach the underlying CS concept.

## 5. Security & Localization
- **Security:** Do not use plain text passwords unless explicitly demonstrating a plaintext protocol. Avoid hardcoded paths; use `FileManager` sandbox boundaries to prevent path traversal.
- **Localization:** Do not write hardcoded strings in the UI. All user-facing text must be fetched via `self.locale.get("namespace.key")` using the `python-i18n` setup, so dynamic language switching works instantly without app restart.

## 6. Code Style
- Max line length is 120 (enforced via `ruff`).
- No trailing whitespaces.
- Explicit type hinting is highly encouraged (`def get(self, key: str) -> str:`).

When making modifications, assume you are teaching a junior developer how to build production-grade desktop applications in Python.

## 7. AI Agent Skills
- AI coding assistants working on this repository MUST consult the `.agents/skills/` directory for task-specific instructions.
- Key skills include `localization` (for managing i18n rules), `mintpy-design-system` (for consistent UI styling), and `cs4s-code-documentation` (for DDAQ-compliant docstrings).
