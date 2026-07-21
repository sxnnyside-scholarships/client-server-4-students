"""
Module: auth.py
───────────────
Purpose: Validates client credentials against the server's authentication storage.

Architectural Role:
Acts as the execution handler for the `CMD_AUTH` protocol command. It sits between
the `CommandDispatcher` (which routed the request) and the `AuthManager` (which checks the disk).

Responsibilities:
- Validate that usernames conform to security constraints.
- Invoke `AuthManager.verify()` to check credentials.
- Update `SecurityContext` abuse thresholds if login fails.
- Emit `CODE_AUTH_OK` or `CODE_AUTH_FAIL` messages back to the client.

Expected Collaborators:
- `src.network.server.dispatcher` (invokes this module).
- `src.storage.auth.AuthManager` (provides the actual credential validation).
- `src.network.security.SecurityContext` (records failures for rate limiting).
"""

import logging
from typing import Tuple

from src.core.protocol import (
    AUTH_FAIL,
    AUTH_OK,
    CODE_AUTH_FAIL,
    CODE_AUTH_OK,
    CODE_BAD_REQ,
    ProtocolHandler,
    STATUS_ERROR,
    STATUS_OK,
)
from src.network.security import (
    SecurityContext,
    SecurityEvent,
    SecurityEventCategory,
    SecuritySeverity,
    is_valid_username,
)
from src.storage.auth import AuthManager

logger = logging.getLogger("server.auth")


class AuthCommandHandler:
    """
    Executes the authentication phase of the client-server protocol.

    Why it exists:
    Because authentication logic involves reading from disk and updating rate-limit
    counters, it is too complex to sit inside the main dispatch switch statement.
    Isolating it makes security auditing easier.

    Responsibilities:
    - Checking if provided credentials match the user database.
    - Emitting security alerts for brute-force attempts.

    Non-Responsibilities (Anti-Goals):
    - It does NOT encrypt or decrypt passwords (handled by `AuthManager`).
    - It does NOT drop the socket directly (it returns a `drop` boolean signal).
    """

    def __init__(self, auth_manager: AuthManager):
        self.auth = auth_manager

    def handle(self, proto: ProtocolHandler, parts: list, sec_ctx: SecurityContext, engine) -> Tuple[str | None, bool]:
        """
        Executes the authentication request.

        Args:
            proto: The client's protocol handler.
            parts: The parsed command payload from the client.
            sec_ctx: The client's active security context.
            engine: The parent server engine for emitting logs and alerts.

        Returns:
            A tuple of `(username, should_drop_connection)`.

        Side Effects:
            Mutates the `sec_ctx` authentication failure counter on bad attempts.
            Sends a protocol response over the socket.

        Failure Behavior:
            Returns `(None, True)` if the client exceeds the brute-force threshold,
            signaling the dispatcher to sever the connection.
        """
        if len(parts) < 3:
            proto.send_message(CODE_BAD_REQ, STATUS_ERROR, AUTH_FAIL)
            drop = sec_ctx.record_auth_failure()
            return None, drop

        user, pwd = parts[1], parts[2]

        if not is_valid_username(user):
            proto.send_message(CODE_BAD_REQ, STATUS_ERROR, AUTH_FAIL)
            evt = SecurityEvent(
                category=SecurityEventCategory.MALFORMED_INPUT.value,
                severity=SecuritySeverity.WARNING.value,
                message=f"Invalid username format: {user}",
                client_address=sec_ctx.client_address,
            )
            engine.on_security_alert(evt.to_dict())
            drop = sec_ctx.record_auth_failure()
            return None, drop

        if self.auth.verify(user, pwd):
            proto.send_message(CODE_AUTH_OK, STATUS_OK, AUTH_OK)
            engine.on_log_message(f"User '{user}' authenticated")
            logger.info("User '%s' authenticated", user)
            return user, False

        proto.send_message(CODE_AUTH_FAIL, STATUS_ERROR, AUTH_FAIL)
        evt = SecurityEvent(
            category=SecurityEventCategory.AUTH_FAILURE.value,
            severity=SecuritySeverity.INFO.value,
            message=f"Failed authentication for user: {user}",
            client_address=sec_ctx.client_address,
        )
        engine.on_security_alert(evt.to_dict())
        engine.on_log_message(f"Auth failed for '{user}'")
        drop = sec_ctx.record_auth_failure()
        if drop:
            logger.warning("Dropping client %s due to auth failure limit", sec_ctx.client_address)
        return None, drop
