"""
Unit tests for src.core.cert_util.
Validates generation and validity of self-signed TLS certificates.
"""

import ssl
from pathlib import Path

from src.core.cert_util import ensure_self_signed_cert, generate_self_signed_certificate


def test_generate_self_signed_certificate(tmp_path: Path):
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
