"""
Module: test_cert_util.py
─────────────────────────
Purpose: Validates ephemeral X.509 certificate and RSA private key generation and idempotent caching.

Architectural Role:
Acts as the unit test suite for `src.core.cert_util`, verifying that the zero-dependency SSL certificate
generator creates syntactically valid PEM structures recognized by Python's standard `ssl` library.

Responsibilities:
- Verify that `generate_self_signed_certificate` outputs valid PEM-encoded certificate and private key files.
- Ensure that standard `ssl.SSLContext` loads the generated certificate and key without syntax errors.
- Validate that `ensure_self_signed_cert` reuses existing files idempotently rather than regenerating them.

Dependencies:
- `pathlib.Path`
- `ssl`
- `src.core.cert_util.ensure_self_signed_cert`
- `src.core.cert_util.generate_self_signed_certificate`

Expected Collaborators:
- `tmp_path`: Pytest fixture providing isolated temporary directory storage.

Educational Note: Ephemeral Self-Signed Certificates
For local networking experiments and student labs, creating real CA-signed certificates is impractical.
Generating self-signed X.509 certificates programmatically on startup allows students to practice
TLS encryption concepts locally without needing an external public key infrastructure (PKI).
"""

import ssl
from pathlib import Path

from src.core.cert_util import ensure_self_signed_cert, generate_self_signed_certificate


def test_generate_self_signed_certificate(tmp_path: Path):
    """
    Validates generation of RSA private key and self-signed X.509 PEM files and validates SSL loading.

    Args:
        tmp_path: Pytest temporary directory fixture for certificate output files.

    Returns:
        None.

    Side Effects:
        Writes PEM certificate and private key files to disk and instantiates an SSLContext.

    Failure Behavior:
        Fails if generated files do not contain PEM headers or if `load_cert_chain` raises SSLError.
    """
    cert_path = tmp_path / "cert.pem"
    key_path = tmp_path / "key.pem"

    out_cert, out_key = generate_self_signed_certificate(cert_path, key_path)

    assert out_cert.exists()
    assert out_key.exists()
    assert b"-----BEGIN CERTIFICATE-----" in cert_path.read_bytes()
    assert b"-----BEGIN RSA PRIVATE KEY-----" in key_path.read_bytes()

    # Verify that Python ssl context accepts the generated certificate chain
    ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ctx.load_cert_chain(certfile=str(out_cert), keyfile=str(out_key))


def test_ensure_self_signed_cert_generates_and_reuses(tmp_path: Path):
    """
    Validates that ensure_self_signed_cert generates files when missing and preserves them across re-runs.

    Args:
        tmp_path: Pytest temporary directory fixture for isolated paths.

    Returns:
        None.

    Side Effects:
        Creates parent directories and writes files on initial run.

    Failure Behavior:
        Fails if files are not created or if file timestamps change during subsequent calls.
    """
    cert_path = tmp_path / "certs" / "cert.pem"
    key_path = tmp_path / "certs" / "key.pem"

    # First call: generates
    c1, k1 = ensure_self_signed_cert(cert_path, key_path)
    assert c1.exists()
    assert k1.exists()
    mtime = c1.stat().st_mtime

    # Second call: reuses existing
    c2, k2 = ensure_self_signed_cert(cert_path, key_path)
    assert c2 == c1
    assert k2 == k1
    assert c2.stat().st_mtime == mtime
