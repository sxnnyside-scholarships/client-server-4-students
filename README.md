<p align="center">
  <strong>Client-Server 4 Students (C4SS)</strong><br>
  <em>A clean, minimal, FTP-like client-server for the classroom</em><br>
  <sub>v1.0.0 — First Stable Release</sub>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/release-v1.0.0-brightgreen?style=flat-square" alt="v1.0.0">
  <img src="https://img.shields.io/badge/python-3.12%2B-blue?style=flat-square" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/GUI-PyQt6-green?style=flat-square" alt="PyQt6">
  <img src="https://img.shields.io/badge/license-MIT-orange?style=flat-square" alt="MIT">
  <img src="https://img.shields.io/badge/i18n-en%20%7C%20es-purple?style=flat-square" alt="EN & ES">
</p>

<p align="center">
  A project by <strong><a href="https://www.sxnnysideproject.com">Sxnnyside Scholarships</a></strong>
</p>

---

## What Is This?

**Client-Server 4 Students (C4SS)** is a basic, clean FTP-like server designed exclusively for academic purposes. It allows students to practically understand the fundamentals of the client-server paradigm: connections, requests, responses, simple authentication, and file handling. Its minimalist interface and intuitive configuration make it a perfect laboratory to experiment without fear of breaking anything critical. It is an accessible gateway to real-world networking, without the hardcore complexity that usually scares beginners.

This project is developed and maintained by **Sxnnyside Scholarships** as part of the [Sxnnyside Project](https://www.sxnnysideproject.com).

> **⚠️ Academic use only** — This project is not designed for production or internet-facing deployments. Security and protocol simplicity were chosen to favour learning.

---

## Features

| Feature | Description |
|---|---|
| **Launcher** | Choose Client or Server mode from a single entry point |
| **File Transfer** | Upload and download files through a GUI |
| **Directory Browsing** | Navigate folders on the server visually |
| **Authentication** | Simple user/password system |
| **Per-User Sandbox** | Each user has their own isolated file area |
| **Two Themes** | Mint Light and Mint Dark, switchable at runtime |
| **Two Languages** | English and Spanish, switchable at runtime |
| **Cross-Platform** | Windows, macOS, Linux |

---

## Quick Start

### Prerequisites

- **Python 3.12** or newer
- **pip** (comes with Python)

### 1. Clone the Repository

```bash
git clone https://github.com/HoujouSxnnyside/client-server-4-students.git
cd client-server-4-students
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

> The only external dependency is **PyQt6**. Everything else uses the Python standard library.

### 3. Run the Application

```bash
python main.py
```

The **Launcher** window will appear. From there you can:

- **Start as Server** — starts listening for connections.
- **Start as Client** — connect to a running server.

### 4. Default Credentials

| Username | Password |
|---|---|
| `student` | `student` |
| `teacher` | `teacher` |

These accounts are created automatically on first run. You can add or remove users from the Server window.

---

## Project Structure

```
client-server-4-students/
├── main.py                        ← Entry point (run this!)
├── requirements.txt
├── config/
│   └── settings.json              ← Human-readable settings
├── src/
│   ├── core/
│   │   ├── config.py              ← Configuration manager
│   │   ├── logger.py              ← Logging utilities
│   │   └── protocol.py            ← Communication protocol
│   ├── network/
│   │   ├── server_backend.py      ← Server networking engine
│   │   └── client_backend.py      ← Client networking engine
│   ├── storage/
│   │   ├── auth.py                ← User authentication
│   │   └── file_manager.py        ← File sandbox management
│   ├── localization/
│   │   ├── locale_manager.py      ← i18n engine
│   │   ├── en.json                ← English strings
│   │   └── es.json                ← Spanish strings
│   └── ui/
│       ├── launcher.py            ← Launcher window
│       ├── server_window.py       ← Server GUI
│       ├── client_window.py       ← Client GUI
│       ├── widgets/
│       │   └── common.py          ← Shared helpers
│       └── themes/
│           ├── theme_manager.py   ← Theme engine
│           ├── mint_light.qss     ← Light theme
│           └── mint_dark.qss      ← Dark theme
├── server_files/                  ← Per-user file storage
├── logs/                          ← Server/client logs
├── docs/
│   ├── USER_MANUAL.md             ← English manual
│   └── MANUAL_DE_USUARIO.md       ← Spanish manual
├── LICENSE                        ← MIT License
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
└── SECURITY.md
```

---

## Architecture Overview

```
┌────────────┐         ┌────────────────────────────────┐
│  Launcher   │────────▶│  Client Window   OR   Server   │
│  (PyQt6)    │◀────────│  Window (PyQt6)                │
└────────────┘         └───────────┬────────────────────┘
                                   │
                        ┌──────────▼──────────┐
                        │   Network Backend    │
                        │  (TCP + Protocol)    │
                        └──────────┬──────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                     │
     ┌────────▼─────┐   ┌─────────▼──────┐   ┌─────────▼──────┐
     │   Storage     │   │  Localization   │   │    Theming      │
     │ (Auth + Files)│   │  (JSON i18n)    │   │  (QSS Sheets)   │
     └──────────────┘   └────────────────┘   └────────────────┘
```

- **Launcher** is the single entry point. It creates the Client or Server window on demand.
- **Network backends** run socket operations in background threads and communicate with the UI via Qt signals.
- **Protocol** is a simple text-line format: `COMMAND|param1|param2\n`.
- **Storage** uses plain JSON files — human-readable and easy to inspect.
- **Themes** and **Localization** are hot-swappable at runtime.

---

## Communication Protocol

All messages are single UTF-8 text lines terminated by `\n`.
Fields are separated by `|`.

| Direction | Command | Format |
|---|---|---|
| Client → Server | Authenticate | `AUTH\|username\|password` |
| Client → Server | List files | `LIST\|subpath` |
| Client → Server | Upload file | `UPLOAD\|filename\|size` → raw bytes |
| Client → Server | Download file | `DOWNLOAD\|filename` |
| Client → Server | Create folder | `MKDIR\|dirname` |
| Client → Server | Disconnect | `QUIT` |

Server replies follow: `OK|data` or `ERROR|reason`.

---

## Configuration

All settings live in `config/settings.json` and are auto-created on first run:

```json
{
    "locale": "en",
    "theme": "mint_light",
    "server": {
        "host": "0.0.0.0",
        "port": 2121,
        "max_connections": 5
    },
    "client": {
        "default_host": "localhost",
        "default_port": 2121
    }
}
```

You can edit this file by hand or through the GUI.

---

## Learning Outcomes

By exploring and running this project, students will learn:

1. How **client-server communication** works over TCP sockets.
2. How to build a **graphical interface** with PyQt6.
3. How a simple **text-based protocol** structures requests and responses.
4. How **authentication** and **file sandboxing** provide basic security.
5. How **i18n** and **theming** make software accessible.
6. How a real open-source project is organised (README, LICENSE, CONTRIBUTING, etc.).

---

## Dependencies

| Package | Why |
|---|---|
| **PyQt6** | Cross-platform GUI framework with mature widget set and QSS styling |

That's it. One dependency. Everything else is Python standard library.

---

## License

Copyright © 2026 **Sxnnyside Scholarships**. This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for details.

**Why MIT?** It's the most permissive and beginner-friendly open-source license. Students and teachers can freely use, modify, and share this project without legal concerns.

---

## Documentation

- [User Manual (English)](docs/USER_MANUAL.md)
- [Manual de Usuario (Español)](docs/MANUAL_DE_USUARIO.md)
- [Changelog](CHANGELOG.md)
- [Contributing Guide](CONTRIBUTING.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Security Policy](SECURITY.md)

---

## Contact

- **Website:** [https://www.sxnnysideproject.com](https://www.sxnnysideproject.com)
- **General support:** [support.sxnnyside@sxnnysideproject.com](mailto:support.sxnnyside@sxnnysideproject.com)
- **Security issues:** [security.sxnnyside@sxnnysideproject.com](mailto:security.sxnnyside@sxnnysideproject.com)
- **Repository:** [https://github.com/HoujouSxnnyside/client-server-4-students](https://github.com/HoujouSxnnyside/client-server-4-students)

---

<p align="center">
  <em>Built with ❤️ for students and teachers everywhere.</em><br>
  <sub>© 2026 Sxnnyside Scholarships · <a href="https://www.sxnnysideproject.com">Sxnnyside Project</a></sub>
</p>
