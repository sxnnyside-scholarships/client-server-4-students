# Client-Server 4 Students

![Version](https://img.shields.io/badge/version-2.1.0-blue)
![License](https://img.shields.io/badge/License-GPLv3-green)
[![CI](https://github.com/sxnnyside-scholarships/client-server-4-students/workflows/CI/badge.svg)](https://github.com/sxnnyside-scholarships/client-server-4-students/actions)

<p align="center">
  <strong>Educational focus ✦ Zero setup required ✦ Fully standalone</strong><br>
  <em>A desktop laboratory for learning client-server networking and socket programming.</em>
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

**Client-Server 4 Students** is an educational networking laboratory for teaching socket programming.

Students often struggle to visualize network protocols and transport-layer behavior. CS4S provides a local sandbox to inspect raw frames, analyze request-response flows, and test failure modes without external infrastructure.

It combines a server and client into a single executable featuring an integrated protocol inspector, sequence ladder diagram, guided lab challenges, Wireshark PCAP exporter, and an educational UDP testbench.

### Philosophy

> *"Pedagogy over performance. Readability over cleverness."*

This is a Sxnnyside Scholarships project, built specifically for educational environments.

## Features

- **Integrated Sandbox**: Run client and server side-by-side with local loopback quick-connect.
- **Protocol Inspector**: Real-time traffic visualization showing raw ASCII frames and protocol codes.
- **Sequence Diagram**: Visual ladder diagram displaying client-server lifelines, message deltas, and live RTT.
- **Guided Challenges**: In-app mini-missions validating handshakes, auth, bad requests, path traversal, and rate limits.
- **Wireshark PCAP Export**: Export captured session traffic as standard `.pcap` files for deep packet analysis.
- **UDP vs TCP Lab**: Educational testbench comparing stream-oriented TCP with connectionless UDP packet bursts.
- **Transport Security (TLS)**: Toggle TLS encryption with automatic ephemeral certificate generation.
- **Teacher Tools**: Classroom broadcast announcements, batch CSV student onboarding, and simulated network impairment.

## Installation

### Prerequisites

- Python (>= 3.11, < 3.16)
- uv (>= 0.6.0)

### From Source

```bash
git clone https://github.com/sxnnyside-scholarships/client-server-4-students.git
cd client-server-4-students

just install
just dev
```

## Usage

```bash
# Run the application launcher
just dev

# Or directly with uv
uv run python main.py
```

## Architecture

```
client-server-4-students/
├── src/ui/         # Qt6 presentation layer
├── src/network/    # Socket engines, protocol framing, and TLS transport
└── src/storage/    # Sandboxed file manager and credential store
```

## Contributing

Contributions are accepted. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

Before contributing, read the [Code of Conduct](CODE_OF_CONDUCT.md).

## License

This project is licensed under the GPL-3.0 License — see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  <strong>Client-Server 4 Students</strong> — A Sxnnyside Scholarships Project<br>
  <em>&copy; 2026 Sxnnyside Project</em>
</p>
