# Changelog

All notable changes to **Client-Server 4 Students** are documented here.

This project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

### Fixed

### Changed

---

## [2.0.0] — 2026-07-21

### Added
- **MintPy Design System**: Introduced a unified UI design language across all components with scalable typography, CSS variables (tokens), and micro-animations.
- **Full Localization (i18n)**: Integrated `python-i18n` with deeply nested JSON dictionaries for real-time switching between English and Spanish.
- **Architectural MVC Standard**: Strictly separated Presentation Layer (`src/ui`) from Business Logic (`src/network` and `src/storage`).
- **Poetry & Just**: Modernized environment management, replacing `requirements.txt` and `Makefile` with `pyproject.toml` and `Justfile`.
- **Comprehensive Testing Suite**: Added exhaustive unit, integration, and GUI tests (`pytest-qt`, `pytest-mock`, `pytest-cov`) across all core modules.
- **Security Hardening**: Implemented strict sandboxing in `FileManager` to prevent path traversal exploits, alongside rate-limiting and a ban registry.
- **Sxnnyside OSS Bundle**: Adopted canonical repository templates (README, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, SUPPORT).
- **GitHub Workflows**: Added automated CI pipelines for linting/testing and automated CD pipelines to build PyInstaller executables on Git tags.
- **AI Agent Skills**: Formalized repository development instructions via `.agents/skills` and `CLAUDE.md`.

### Changed
- Refactored entire codebase to enforce type hinting, thread safety with PyQt signals/slots, and `ruff`/`mypy` conformance.
- Migrated from legacy PyQt5/Tkinter to **PyQt6** as the exclusive GUI framework.
- Transitioned project license to **GPL-3.0** for PyQt6 conformance.
- Upgraded PyInstaller script (`scripts/build_dist.py`) to generate a fully portable `--onefile` executable bundling themes and translations.

### Fixed
- Stabilized file transfers and resolved socket state desynchronization during network interruptions.
- Fixed UI components failing to resolve localization namespaces by implementing fully qualified `retranslate()` paths.

### Removed
- Deleted obsolete manual files (`docs/MANUAL_DE_USUARIO.md`, `docs/USER_MANUAL.md`), replacing them with standard localized docs.

---

[Unreleased]: https://github.com/sxnnyside-scholarships/client-server-4-students/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/sxnnyside-scholarships/client-server-4-students/releases/tag/v2.0.0
