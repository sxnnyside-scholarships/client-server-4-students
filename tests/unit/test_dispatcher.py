"""
Module: test_dispatcher.py
───────────────────────────
Purpose: Validates the `CommandDispatcher` routing rules and abuse counters.

Architectural Role:
Unit testing for `dispatcher.py`, isolated from real sockets. Uses a stub
`ProtocolHandler` and `engine` so the routing/auth-barrier/abuse-tracking
logic can be exercised deterministically.

Expected Collaborators:
- `pytest` (test runner).
- `src.network.server.dispatcher.CommandDispatcher` (the subject under test).
"""

from src.core.protocol import CODE_BAD_REQ, STATUS_ERROR
from src.network.security import SecurityContext
from src.network.server.dispatcher import CommandDispatcher


class _StubProto:
    def __init__(self):
        self.sent = []

    def send_message(self, *args):
        self.sent.append(args)


class _StubEngine:
    def __init__(self):
        self.alerts = []

    def on_security_alert(self, evt):
        self.alerts.append(evt)


def test_dispatch_unknown_command_sends_bad_request():
    """
    Unknown commands must return CODE_BAD_REQ and raise a security alert,
    without dropping the connection until the invalid-command threshold trips.
    """
    dispatcher = CommandDispatcher()
    proto = _StubProto()
    engine = _StubEngine()
    sec_ctx = SecurityContext("127.0.0.1")

    should_disconnect, username = dispatcher.dispatch(
        "BOGUS", ["BOGUS"], proto, None, sec_ctx, engine
    )

    assert should_disconnect is False
    assert username is None
    assert proto.sent == [(CODE_BAD_REQ, STATUS_ERROR, "Unknown command")]
    assert len(engine.alerts) == 1
    assert sec_ctx.invalid_commands == 1


def test_dispatch_unknown_command_drops_after_threshold():
    """
    Repeated unknown commands must eventually trip the invalid-command
    threshold and signal the caller to disconnect the client.
    """
    dispatcher = CommandDispatcher()
    proto = _StubProto()
    engine = _StubEngine()
    sec_ctx = SecurityContext("127.0.0.1")

    should_disconnect = False
    for _ in range(sec_ctx.max_invalid_commands):
        should_disconnect, _ = dispatcher.dispatch(
            "BOGUS", ["BOGUS"], proto, None, sec_ctx, engine
        )

    assert should_disconnect is True


def test_dispatch_requires_auth_for_protected_commands():
    """
    A registered command marked `requires_auth=True` must be rejected when
    no username is present on the session, without invoking the handler.
    """
    dispatcher = CommandDispatcher()
    handler_calls = []
    dispatcher.register("LIST", lambda *a: handler_calls.append(a), requires_auth=True)

    proto = _StubProto()
    engine = _StubEngine()
    sec_ctx = SecurityContext("127.0.0.1")

    should_disconnect, username = dispatcher.dispatch(
        "LIST", ["LIST"], proto, None, sec_ctx, engine
    )

    assert should_disconnect is False
    assert username is None
    assert handler_calls == []
