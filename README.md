# Client-Server 4 Students

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![License](https://img.shields.io/badge/License-GPLv3-green)
[![CI](https://github.com/sxnnyside-scholarships/client-server-4-students/workflows/CI/badge.svg)](https://github.com/sxnnyside-scholarships/client-server-4-students/actions)

<p align="center">
  <strong>Educational focus ✦ Zero setup required ✦ Fully standalone</strong><br>
  <em>A cross-platform desktop application designed to teach foundational client-server networking to Computer Science students.</em>
</p>

<p align="center">
  <a href="#about">About</a> ✦
  <a href="#features">Features</a> ✦
  <a href="#installation">Installation</a> ✦
  <a href="#usage">Usage</a> ✦
  <a href="#architecture">Architecture</a> ✦
  <a href="#contributing">Contributing</a>
</p>

---

## About

**Client-Server 4 Students** is an educational networking laboratory.

Students often struggle to visualize socket programming and network protocols. CS4S provides a ready-to-use, sandbox environment where students can connect, transfer files, and inspect raw protocol traffic without needing complex infrastructure.

It combines a Python/PyQt6 server and client into a single executable, featuring a built-in packet inspector and latency simulation for real-world testing.

### Philosophy

> *"Pedagogy over performance. Readability over cleverness."*

This is a Sxnnyside Scholarships project, built specifically for educational environments.

## Features

- **Single Executable**: Both Client and Server modes run from the same application.
- **Protocol Inspector**: Real-time traffic visualization for teaching socket communication.
- **Network Simulation**: Built-in latency and packet loss simulation for testing edge cases.
- **Sandboxed Storage**: File transfers are strictly isolated to temporary directories to prevent host system modification.

## Installation

### Prerequisites

None! The application is distributed as a standalone portable executable.

### From Source

```bash
git clone https://github.com/sxnnyside-scholarships/client-server-4-students.git
cd client-server-4-students

# Install dependencies using Poetry
poetry install

# Run the development environment
just dev
```

## Usage

```bash
# To run the pre-built application:
./CS4S

# Select either 'Client' or 'Server' from the launcher screen.
```

## Architecture

```
client-server-4-students/
├── src/ui/         # Qt6 Presentation Layer (Views only, zero business logic)
├── src/network/    # Core networking, TCP sockets, and threading handlers
└── src/storage/    # Sandboxed file manager and auth registry
```

For a detailed breakdown, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Contributing

Contributions are accepted. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

Before contributing, read the [Code of Conduct](CODE_OF_CONDUCT.md).

## License

This project is licensed under the GPL-3.0 License — see the [LICENSE](LICENSE) file for details. Icons provided by [Mingcute Icons](https://github.com/Richard9394/MingCute_Icon).

---

<p align="center">
  <strong>Client-Server 4 Students</strong> — A Sxnnyside Scholarships Project<br>
  <em>&copy; 2026 Sxnnyside Project</em>
</p>
