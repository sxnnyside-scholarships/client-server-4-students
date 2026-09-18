# Changelog

All notable changes to **Client-Server 4 Students** are documented here.

This project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [2.1.0] — 2026-09-18

### Added
- **Educational UDP Channel ("Canal UDP Educativo")**:
  - `UDPEducatorServer` background companion echo server on adjacent UDP port (`tcp_port + 1`) with simulated latency and packet loss.
  - `UDPProbeClient` supporting burst transmissions, packet loss tracking, per-datagram RTT calculation, and throughput measurement.
  - `UDPComparisonWidget` added as the 5th tab in the Client Lab View, featuring configurable bursts, side-by-side TCP (reliable stream) vs UDP (best-effort datagram) comparative cards, interactive visual packet matrix of individual datagram chips, and educational insight callouts.
- **Teacher Tools ("Herramientas para el Docente")**:
  - **Broadcast Announcements**: Server UI announcement bar and `ServerEngine.broadcast_message` broadcasting instant notices to all connected client terminals via protocol push with modal alerts on the client side.
  - **Batch Student Import via CSV**: Teacher user management interface now features a one-click CSV import button supporting header rows, duplicate checking, and validation feedback.
- **Interactive Sequence Diagram (Ladder Diagram)**: Temporal message sequence visualizer (`LadderDiagramWidget`) plotting Client ⇄ Server vertical lifelines with chronological request/response arrows, protocol codes, timestamps, delta latencies, and RTT display.
- **Guided Lab Challenges (Misiones Guiadas)**: Integrated laboratory challenge system (`LabMissionsWidget` & `MissionsManager`) with automated real-time evaluation of networking tasks (Handshake, Authentication, 400 Bad Request injection, 403 Forbidden path traversal defense, 429 Too Many Requests rate limiting, and TLS encryption).
- **Wireshark PCAP Exporter (`.pcap`)**: Pure-Python Libpcap 2.4 binary generator (`src.core.pcap_util.PCAPExporter`) generating standard Ethernet II, IPv4 (with RFC 1071 checksums), and TCP frames for classroom network packet analysis.
- **Python Sockets Code Generator Tab ("Ver Código Python")**: Interactive code generator tab (`PythonCodeWidget`) providing standalone, runnable standard-library Python scripts (`import socket`, `import ssl`) dynamically linked to active client connection parameters with one-click copy and script export.
- **Multi-Tab Lab Hub**: Segmented tab bar in Client's Lab View hosting the Protocol Inspector, Ladder Diagram, Guided Challenges, Python Code Tab, and UDP vs TCP Lab.
- **Interactive TLS Controls**: Added `MintCheckbox` controls in Client and Server connection panels to easily wrap socket streams in TLS/SSL.
- **Ephemeral Self-Signed Certificate Generator**: Introduced `src.core.cert_util` powered by `cryptography` to generate valid, self-contained X.509 certificates and keys on the fly without requiring OpenSSL CLI.
- **Interactive Sandbox (Split-Screen) Mode**: Added a third start mode in Launcher providing a synchronized, dual-pane `QSplitter` view embedding both Server and Client with a one-click loopback Quick Connect.
- **Phase 3 Test Suite**: Added dedicated unit and GUI test coverage for UDP server and probe client, packet loss simulation, teacher broadcast announcement delivery, batch CSV student account ingestion, and comparison UI rendering.


### Changed
- Migrated dependency management and toolchain from Poetry to `uv` and PEP 621 (`hatchling`), providing deterministic lockfiles (`uv.lock`) and `.python-version` pinning.
- Configured local pre-commit git hooks for automated formatting and linting (`.pre-commit-config.yaml`).
- Updated Educator Guides (`EDUCATOR_GUIDE.md` and `GUIA_DEL_EDUCADOR.md`) to reflect the in-app TLS controls and Classroom Projection / Sandbox mode for Lab B.
- **UI/UX Polish & Layout Rebalance**:
  - Eliminated Qt font alias lookup warning and 85ms start lag via native `get_monospace_font()`.
  - Added compact NavRail mode (`rail.set_compact(True)`) for embedded multi-pane views.
  - Resolved dual-pane sandbox overlap on screens smaller than 2400px by decoupling minimum sizes (`embedded=True`).
  - Added responsive display geometry scaling up to 1720x1020px for 16-inch and high-resolution monitors.
  - Added live Metrics Summary Bar (TX, RX, Active Connections, Total Packets) across the top of Server Overview.
  - Converted Server Overview logs and client list to an interactive resizable `QSplitter` with `NoWrap` logs.
  - Streamlined Lab Hub tab buttons and inspector toolbar with concise labels and rich bilingual tooltips.
  - Ensured idempotent credential initialization (`student:student123`) via `AuthManager.set_password()`.

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
