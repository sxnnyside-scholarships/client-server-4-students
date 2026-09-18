# Client-Server 4 Students

![Version](https://img.shields.io/badge/version-2.1.0-blue)
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

Students often struggle to visualize socket programming and network protocols. CS4S provides a ready-to-use sandbox environment where students can connect, transfer files, and inspect raw protocol traffic without needing complex infrastructure.

It combines a Python/PyQt6 server and client into a single executable, featuring a built-in packet inspector, ladder sequence diagram, guided missions, Wireshark PCAP exporter, educational UDP testbench, and latency/packet loss simulation for real-world testing.

### Philosophy

> *"Pedagogy over performance. Readability over cleverness."*

This is a Sxnnyside Scholarships project, built specifically for educational environments.

## Features

- **Single Executable & Sandbox**: Run Client and Server modes independently, or together in an integrated Dual-Pane Split-Screen Sandbox with instant loopback Quick Connect.
- **Protocol Inspector**: Real-time traffic visualization showing raw ASCII frames, keepalive filtering, and command explanations.
- **Interactive Sequence Diagram**: Visual ladder diagram illustrating client-server lifelines, message deltas, and live RTT latency readouts.
- **Guided Lab Challenges**: In-app mini-missions automatically verifying handshake, authentication, 400 Bad Request injection, 403 path traversal defense, and 429 rate limiting.
- **Wireshark PCAP Exporter**: Export captured traffic as standard `.pcap` files for deep frame inspection in classroom networking tools.
- **UDP vs TCP Comparative Lab**: Educational testbench demonstrating stateless best-effort datagram bursts versus reliable ordered streams with interactive packet loss visualization.
- **Transport Security (TLS)**: GUI toggle for Transport Layer Security with built-in ephemeral X.509 certificate generation.
- **Teacher Tools**: Classroom broadcast messaging to all connected terminals, batch CSV student account import, and simulated network impairment (latency and loss).

## Installation

### Prerequisites

- Python (>= 3.11, < 3.16)
- uv (>= 0.6.0)

### From Source

```bash
git clone https://github.com/sxnnyside-scholarships/client-server-4-students.git
cd client-server-4-students

# Bootstrap dependencies, virtual environment, and git hooks
just install

# Run the development environment
just dev
```

## Usage

```bash
# Run the development application:
just dev

# Or directly via uv:
uv run python main.py

# Select 'Sandbox (Self-Study)', 'Client', or 'Server' from the launcher screen.
```

## Architecture

```
client-server-4-students/
├── src/ui/         # Qt6 Presentation Layer (Views only, zero business logic)
├── src/network/    # Core networking, TCP/UDP sockets, TLS, and threading handlers
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
