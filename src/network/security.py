"""
Module: security.py
───────────────────
Purpose: Centralized security rules, event tracking, and session hardening.

Architectural Role:
Acts as the central authority for connection validation and threat detection. It isolates
malicious behavior tracking (e.g., brute-force attempts) from the normal business logic
of the ProtocolHandler.

Responsibilities:
- Provide strict regex-based validation for usernames.
- Track failed authentication attempts per connection.
- Track malformed input thresholds to detect fuzzing or buggy clients.
- Maintain a temporal IP ban list.

Expected Collaborators:
- `src.network.server.engine`
- `src.network.server.handlers.auth`
"""

import re
import time
from dataclasses import dataclass
from enum import Enum


class SecurityEventCategory(Enum):
    """
    Categorizes the type of security infraction detected by the server.
    """

    AUTH_FAILURE = "auth_failure"
    INVALID_COMMAND = "invalid_command"
    PATH_TRAVERSAL = "path_traversal"
    DOS_ATTEMPT = "dos_attempt"
    MALFORMED_INPUT = "malformed_input"
    SESSION_VIOLATION = "session_violation"


class SecuritySeverity(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class SecurityEvent:
    """
    Structured payload for logging and transmitting security alerts.

    Why it exists:
    Instead of passing loose strings around, this dataclass ensures all security
    events carry the necessary forensic metadata (severity, IP, timestamp).

    Responsibilities:
    - Encapsulate alert data.
    - Serialize to dictionary for Qt signal transmission.

    Non-Responsibilities (Anti-Goals):
    - It does NOT decide what to do with the event (e.g., it doesn't write to disk).
    """

    category: str
    severity: str
    message: str
    client_address: str

    def to_dict(self) -> dict:
        """
        Converts the dataclass instance to a primitive dictionary.

        Args:
            None.

        Returns:
            A dictionary containing the event attributes and a generated timestamp.

        Side Effects:
            Reads the current system time.

        Failure Behavior:
            None.
        """
        return {
            "category": self.category,
            "severity": self.severity,
            "message": self.message,
            "client_address": self.client_address,
            "timestamp": time.time(),
        }


# Strict validation: Alphanumeric, underscores, hyphens, 3 to 32 chars.
# Explicitly rejects any path separators, dots, or control characters.
_USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_-]{3,32}$")


def is_valid_username(username: str) -> bool:
    """
    Returns True if the username is safe for filesystem and application use.

    Args:
        username: The string to validate.

    Returns:
        True if the string strictly matches the alphanumeric allow-list.

    Side Effects:
        None.

    Failure Behavior:
        Fails closed (returns False) on empty strings or malicious characters.

    Educational Note:
    We use an explicit allow-list regex rather than trying to strip out
    dangerous characters. This deterministic approach completely eliminates
    path-traversal threats (e.g. `../../root`).
    """
    if not username:
        return False
    return bool(_USERNAME_REGEX.match(username))


BAN_DURATION_SEC = 60.0


class BanRegistry:
    """
    Tracks temporarily banned IP addresses for a single server instance.

    Why it exists:
    IP bans must be scoped to the server that issued them rather than to the
    Python process. A module-level dictionary would leak bans across
    independent `ServerNetworkEngine` instances (e.g. between test runs),
    causing order-dependent test failures.

    Responsibilities:
    - Recording a temporary ban for an IP address.
    - Reporting whether an IP is currently serving a ban, expiring stale entries.

    Non-Responsibilities (Anti-Goals):
    - It does NOT decide when to ban an IP (delegated to the dispatcher/engine).
    """

    def __init__(self, ban_duration_sec: float = BAN_DURATION_SEC):
        self._banned_ips: dict[str, float] = {}
        self.ban_duration_sec = ban_duration_sec

    def is_banned(self, ip: str) -> bool:
        """
        Checks if a remote IP address is currently serving a time penalty.

        Args:
            ip: The string IP address to check.

        Returns:
            True if the IP is actively banned.

        Side Effects:
            If a ban has naturally expired, it cleans up the entry.

        Failure Behavior:
            None.
        """
        if ip in self._banned_ips:
            if time.time() < self._banned_ips[ip]:
                return True
            del self._banned_ips[ip]
        return False

    def ban(self, ip: str):
        """
        Places an IP address on a temporary ban list for abusive behavior.

        Args:
            ip: The string IP address to penalize.

        Returns:
            None.

        Side Effects:
            Mutates the instance's ban dictionary.

        Failure Behavior:
            None.
        """
        self._banned_ips[ip] = time.time() + self.ban_duration_sec


class SecurityContext:
    """
    Tracks security-related state for a single client connection.

    Why it exists:
    Because TCP sockets are persistent, a malicious client might try to brute-force
    a password or send garbage data to crash the server. This state machine tracks
    abuse thresholds per-connection to know when to drop them.

    Responsibilities:
    - Tallying failed authentications.
    - Tallying invalid command structures.

    Non-Responsibilities (Anti-Goals):
    - It does NOT actually drop the socket (delegated to the ServerNetworkEngine).
    """

    def __init__(self, client_address: str):
        self.client_address = client_address
        self.failed_auth_attempts = 0
        self.invalid_commands = 0
        self.max_auth_failures = 5
        self.max_invalid_commands = 10

    def record_auth_failure(self) -> bool:
        """
        Increments the failed authentication counter.

        Args:
            None.

        Returns:
            True if the connection has exceeded its maximum allowed attempts.

        Side Effects:
            Mutates `failed_auth_attempts`.

        Failure Behavior:
            None.
        """
        self.failed_auth_attempts += 1
        return self.failed_auth_attempts >= self.max_auth_failures

    def record_invalid_command(self) -> bool:
        """
        Increments the malformed command counter.

        Args:
            None.

        Returns:
            True if the connection has exceeded its maximum allowed garbage inputs.

        Side Effects:
            Mutates `invalid_commands`.

        Failure Behavior:
            None.
        """
        self.invalid_commands += 1
        return self.invalid_commands >= self.max_invalid_commands
