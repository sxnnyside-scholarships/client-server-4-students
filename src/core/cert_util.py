"""
Module: cert_util.py
────────────────────
Purpose: Provides automated generation and management of self-signed X.509 SSL/TLS certificates.

Architectural Role:
Acts as a cryptographic utility in the core layer. It ensures the server has valid TLS certificates
without requiring external OpenSSL CLI binaries or third-party certificate authorities, enabling
seamless plug-and-play laboratory exercises in classroom environments.

Dependencies:
- `cryptography.x509`
- `cryptography.hazmat.primitives`

Expected Collaborators:
- `src.network.server.engine`
- `src.network.server_backend`
- `src.ui.server_window`

Important Implementation Notes:
Self-signed certificates are generated with Subject Alternative Names (SAN) for both `localhost`
and `127.0.0.1`. The certificate is valid for 365 days. In client connections, an unverified SSL
context is used because educational self-signed certificates lack a root CA signature.
"""

import datetime
import ipaddress
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


def generate_self_signed_certificate(cert_path: Path, key_path: Path) -> tuple[Path, Path]:
    """
    Generates a new self-signed X.509 certificate and RSA private key pair and saves them to disk.

    ## Educational Note: Public Key Infrastructure (PKI) & Self-Signed Certificates
    In production environments, a trusted Certificate Authority (CA) signs certificates to vouch
    for the server's identity, preventing Man-in-the-Middle (MitM) attacks. In an isolated educational
    laboratory, creating and installing custom root CAs on student machines introduces immense setup
    friction. Self-signed certificates allow students to observe transport-layer encryption (confidentiality)
    and protocol framing differences without requiring public internet access or root CA configuration.

    Args:
        cert_path: Target filesystem path where the PEM certificate will be written.
        key_path: Target filesystem path where the PEM private key will be written.

    Returns:
        tuple[Path, Path]: A tuple containing the absolute paths to (cert_path, key_path).

    Side Effects:
        Creates parent directories if necessary and writes two files to disk. Sets file
        permissions on the private key to owner-read/write only (0o600).

    Failure Behavior:
        Raises `OSError` if the filesystem paths cannot be written to.
    """
    cert_path = cert_path.resolve()
    key_path = key_path.resolve()

    cert_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Generate an RSA 2048-bit Private Key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # 2. Build Subject & Issuer Names
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "CS4S Educational Laboratory"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ]
    )

    # 3. Assemble the X.509 Certificate with SAN extensions
    san_extension = x509.SubjectAlternativeName(
        [
            x509.DNSName("localhost"),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
            x509.IPAddress(ipaddress.IPv6Address("::1")),
        ]
    )

    now = datetime.datetime.now(datetime.timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=365))
        .add_extension(san_extension, critical=False)
        .sign(private_key, hashes.SHA256())
    )

    # 4. Serialize Private Key (PEM format)
    key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )

    # 5. Serialize Certificate (PEM format)
    cert_bytes = certificate.public_bytes(serialization.Encoding.PEM)

    # 6. Write to disk
    key_path.write_bytes(key_bytes)
    key_path.chmod(0o600)

    cert_path.write_bytes(cert_bytes)

    return cert_path, key_path


def ensure_self_signed_cert(cert_path: Path | None = None, key_path: Path | None = None) -> tuple[Path, Path]:
    """
    Ensures that a valid TLS certificate and private key exist, generating them if absent.

    Args:
        cert_path: Optional explicit certificate path. Defaults to `~/.cs4s/certs/cert.pem`.
        key_path: Optional explicit private key path. Defaults to `~/.cs4s/certs/key.pem`.

    Returns:
        tuple[Path, Path]: Absolute paths to the existing or newly created (cert, key).

    Side Effects:
        May create files in `~/.cs4s/certs/` if they do not exist.

    Failure Behavior:
        Raises `OSError` if directories or files cannot be created.
    """
    if cert_path is None:
        cert_path = Path.home() / ".cs4s" / "certs" / "cert.pem"
    if key_path is None:
        key_path = Path.home() / ".cs4s" / "certs" / "key.pem"

    if not cert_path.exists() or not key_path.exists():
        return generate_self_signed_certificate(cert_path, key_path)

    return cert_path.resolve(), key_path.resolve()
