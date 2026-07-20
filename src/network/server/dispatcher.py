"""
Module: dispatcher.py
─────────────────────
Purpose: Routes parsed commands to their registered handlers and manages authentication barriers.

Architectural Role:
Acts as the central traffic controller for the server. It decouples the `ClientConnectionHandler` 
(which just reads strings from a socket) from the `handlers` (which perform business logic like 
disk I/O or authentication).

Responsibilities:
- Maintain a registry of supported protocol commands mapped to handler functions.
- Enforce the authentication barrier (rejecting protected commands if `username` is None).
- Increment `SecurityContext` abuse thresholds for invalid commands.

Expected Collaborators:
- `src.network.server.connection` (calls this dispatcher).
- `src.network.server.handlers` (registers functions with this dispatcher).
"""

import logging
from typing import Callable, Tuple, Any

from src.core.protocol import (
    CMD_AUTH,
    CMD_DELETE,
    CMD_DOWNLOAD,
    CMD_LIST,
    CMD_MKDIR,
    CMD_MOVE,
    CMD_PING,
    CMD_QUIT,
    CMD_RENAME,
    CMD_UPLOAD,
    CODE_BAD_REQ,
    CODE_FORBIDDEN,
    CODE_GOODBYE,
    CODE_OK,
    GOODBYE,
    ProtocolHandler,
    STATUS_ERROR,
    STATUS_OK,
)
from src.network.security import BanRegistry, SecurityContext, SecurityEvent, SecurityEventCategory, SecuritySeverity

logger = logging.getLogger("server.dispatcher")

class CommandDispatcher:
    """
    Routes commands to their registered handlers and manages authentication barriers.

    Why it exists:
    Hardcoding a massive `if/elif` block in the connection read loop becomes unmaintainable. 
    A dynamic registry allows handler logic to be split into separate files.

    Responsibilities:
    - Executing mapped functions based on the string command prefix.
    - Blocking privileged commands from unauthenticated sessions.

    Non-Responsibilities (Anti-Goals):
    - It does NOT parse the protocol bytes (delegated to `ProtocolHandler`).
    - It does NOT perform the actual file system operations.
    """

    def __init__(self):
        # Maps command -> (handler_func, requires_auth)
        self._handlers: dict[str, Tuple[Callable, bool]] = {}
        # Per-instance ban registry, shared with the owning ServerNetworkEngine
        # so bans stay scoped to this server rather than leaking across
        # processes/tests via module-level state.
        self.ban_registry = BanRegistry()

    def register(self, cmd: str, handler: Callable, requires_auth: bool = True):
        """
        Binds a protocol command string to a specific execution function.

        Args:
            cmd: The string command (e.g., 'LIST').
            handler: The callable function that will process the command payload.
            requires_auth: Whether this command requires an active session to execute.

        Returns:
            None.

        Side Effects:
            Mutates the internal `_handlers` dictionary.

        Failure Behavior:
            If a command is re-registered, the old handler is silently overwritten.
        """
        self._handlers[cmd.upper()] = (handler, requires_auth)

    def dispatch(
        self, 
        cmd: str, 
        parts: list, 
        proto: ProtocolHandler, 
        username: str | None, 
        sec_ctx: SecurityContext, 
        engine
    ) -> Tuple[bool, str | None]:
        """
        Validates and executes the appropriate handler for an incoming command.

        Args:
            cmd: The parsed protocol command (e.g., 'AUTH').
            parts: The full parsed payload list, including the command.
            proto: The client's active protocol handler.
            username: The current authenticated username, or None.
            sec_ctx: The active security tracking context.
            engine: The parent server engine for logging and signals.

        Returns:
            A tuple of `(should_disconnect: bool, new_username: str | None)`.

        Side Effects:
            May mutate `sec_ctx` abuse thresholds.
            May invoke disk I/O through downstream handlers.

        Failure Behavior:
            Returns `(True, username)` if the command limit is exceeded or an exception is caught.
        """
        if cmd == CMD_QUIT:
            proto.send_message(CODE_GOODBYE, STATUS_OK, GOODBYE)
            return True, username

        if cmd == CMD_PING:
            # Lightweight round-trip probe for the client's RTT measurement.
            # Answered unconditionally (no auth barrier, no handler registry
            # entry) since it carries no payload and must stay as cheap as
            # possible to keep the latency reading honest.
            proto.send_message(CODE_OK, STATUS_OK, "PONG")
            return False, username

        if cmd not in self._handlers:
            proto.send_message(CODE_BAD_REQ, STATUS_ERROR, "Unknown command")
            evt = SecurityEvent(
                category=SecurityEventCategory.MALFORMED_INPUT.value,
                severity=SecuritySeverity.WARNING.value,
                message=f"Invalid command: {cmd}",
                client_address=sec_ctx.client_address
            )
            engine.on_security_alert(evt.to_dict())
            if sec_ctx.record_invalid_command():
                logger.warning("Dropping client %s due to malformed input limit", sec_ctx.client_address)
                return True, username
            return False, username

        handler, requires_auth = self._handlers[cmd]

        if requires_auth and not self._require_auth(proto, username, sec_ctx, engine):
            if sec_ctx.record_invalid_command():
                return True, username
            return False, username

        try:
            # The handler signature varies. 
            # CMD_AUTH returns (username, drop)
            if cmd == CMD_AUTH:
                new_username, drop = handler(proto, parts, sec_ctx, engine)
                if drop:
                    self.ban_registry.ban(sec_ctx.client_address.split(':')[0])
                    return True, username
                if new_username:
                    return False, new_username
                return False, username
            else:
                # Other handlers return None
                handler(proto, parts, username, engine)
                return False, username
        except Exception as exc:
            logger.error("Error executing %s: %s", cmd, exc)
            return False, username

    def _require_auth(self, proto: ProtocolHandler, username: str | None, sec_ctx: SecurityContext, engine) -> bool:
        """
        Internal barrier to enforce session authentication.

        Args:
            proto: The client's active protocol handler.
            username: The current authenticated username.
            sec_ctx: The active security context.
            engine: The parent engine.

        Returns:
            True if authorized, False otherwise.

        Side Effects:
            Sends a `CODE_FORBIDDEN` message back to the client if unauthorized.
            Emits a `SESSION_VIOLATION` security alert to the UI.

        Failure Behavior:
            None.
        """
        if username is None:
            proto.send_message(CODE_FORBIDDEN, STATUS_ERROR, "Not authenticated")
            evt = SecurityEvent(
                category=SecurityEventCategory.SESSION_VIOLATION.value,
                severity=SecuritySeverity.WARNING.value,
                message="Attempted privileged operation without authentication",
                client_address=sec_ctx.client_address
            )
            engine.on_security_alert(evt.to_dict())
            return False
        return True
