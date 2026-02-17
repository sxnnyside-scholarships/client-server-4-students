# Security Policy

## Important Disclaimer

**Client-Server 4 Students (C4SS)** is an **educational project** developed by **Sxnnyside Scholarships**, designed exclusively for classroom and laboratory use. It is **not** intended for production, internet-facing, or security-critical environments.

The authentication system uses SHA-256 hashing (not bcrypt/argon2), and the communication protocol transmits data in plain text without encryption. These are deliberate simplifications to keep the codebase accessible to beginners.

## Supported Versions

| Version | Supported |
|---|---|
| 1.0.x | Yes |

## Reporting a Vulnerability

If you discover a security issue — even in an educational project, responsible disclosure matters:

1. **Do NOT** open a public GitHub issue.
2. Email the security team at: **[security.sxnnyside@sxnnysideproject.com](mailto:security.sxnnyside@sxnnysideproject.com)**
3. Include:
   - A clear description of the vulnerability.
   - Steps to reproduce.
   - Potential impact.
4. We will acknowledge your report within **72 hours** and work to address it in a timely manner.

> **Note:** This email address is exclusively for security-related reports. For general questions, bugs, or feature requests, please use **[support.sxnnyside@sxnnysideproject.com](mailto:support.sxnnyside@sxnnysideproject.com)** or open a [GitHub Issue](https://github.com/HoujouSxnnyside/client-server-4-students/issues).

## What We Consider In-Scope

- Path traversal allowing file access outside user sandboxes.
- Authentication bypass.
- Denial of service against the server.
- Any crash that could be triggered by a malicious client.

## What We Consider Out-of-Scope

- Lack of TLS/SSL encryption (known design limitation).
- Weak password hashing algorithm (known, documented, educational choice).
- Attacks requiring local access to the configuration files.

## Acknowledgements

We appreciate anyone who takes the time to report security issues, even in an educational context. Responsible disclosure helps everyone learn better.

Thank you for helping keep this project safe for students!

---

<sub>© 2026 Sxnnyside Scholarships · [Sxnnyside Project](https://www.sxnnysideproject.com)</sub>
