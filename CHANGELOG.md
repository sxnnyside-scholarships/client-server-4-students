# Changelog

All notable changes to **Client-Server 4 Students (C4SS)** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] — 2026-02-17

### First Stable Release

This is the first official production-ready release of Client-Server 4 Students (C4SS), an educational FTP-like client-server application developed by **Sxnnyside Scholarships**.

### Added

- **Launcher** — Single entry point to choose Client or Server mode.
- **Client GUI** — Connect, browse, upload, download files, and create folders.
- **Server GUI** — Start/stop the server, manage users, view real-time logs, and monitor connected clients.
- **TCP-based protocol** — Simple text-line protocol (`COMMAND|param1|param2\n`) for educational clarity.
- **Authentication** — SHA-256 + salt password hashing with per-user file sandboxing.
- **File transfer** — Upload and download files with progress indication.
- **Directory browsing** — Navigate server-side folder structures from the client.
- **Per-user sandboxing** — Each user has an isolated file area on the server.
- **Internationalisation (i18n)** — English and Spanish, hot-swappable at runtime.
- **Theming** — Mint Light and Mint Dark themes via QSS stylesheets, switchable at runtime.
- **Configuration** — Human-readable `config/settings.json` for all preferences.
- **Documentation** — Full user manuals in English and Spanish, contributing guide, code of conduct, and security policy.
- **Branding footer** — "Developed by Sxnnyside Scholarships · Sxnnyside Project" visible across all application windows.

### Security

- Passwords are hashed with SHA-256 + random salt (educational, not production-grade).
- Per-user file sandboxing prevents path traversal between user directories.
- Communication is plaintext by design (documented educational limitation).

### Notes

- Requires **Python 3.12+** and **PyQt6 >= 6.6.0**.
- Designed exclusively for academic and classroom use.
- Licensed under the **MIT License**.

---

**Repository:** [https://github.com/HoujouSxnnyside/client-server-4-students](https://github.com/HoujouSxnnyside/client-server-4-students)
**Website:** [https://www.sxnnysideproject.com](https://www.sxnnysideproject.com)

[1.0.0]: https://github.com/HoujouSxnnyside/client-server-4-students/releases/tag/v1.0.0
