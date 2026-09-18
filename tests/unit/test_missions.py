"""
Module: test_missions.py
────────────────────────
Purpose: Unit validation of the Guided Lab Missions state machine, packet pattern matching, and progress tracking.

Architectural Role:
Acts as the test suite for `MissionsManager`, verifying that students' network interactions (handshakes,
auth challenges, malicious packet injections, directory traversals, and rate limits) trigger automated mission completion.

Responsibilities:
- Verify initial mission states (0/6 completed).
- Verify packet sequence pattern detection for M1 (Handshake: HELLO -> 220).
- Verify authentication state detection for M2 (AUTH -> 230).
- Verify error code handling for M3 (400 Bad Request) and M4 (403 Path Traversal).
- Verify rate limiting detection for M5 (429 Too Many Requests).
- Verify TLS secure channel activation for M6.
- Verify progress counter calculations and mission state reset functionality.

Dependencies:
- `src.ui.widgets.missions.MissionsManager`

Expected Collaborators:
- `MissionsManager`: Core state machine tracking lab challenges.

Educational Note: Automated Lab Verification
Interactive challenges transform passive networking lectures into active discovery labs. Verifying that the
state machine accurately detects protocol errors (e.g. 400 Bad Request, 403 Forbidden) gives students immediate
reinforcement when they successfully craft specific network events.
"""

from src.ui.widgets.missions import MissionsManager


def test_missions_manager_initial_state():
    """
    Validates initial mission collection count and default incomplete state.

    Args:
        None.

    Returns:
        None.

    Side Effects:
        Instantiates MissionsManager.

    Failure Behavior:
        Fails if initial mission count is not 6 or if any mission begins marked as completed.
    """
    mgr = MissionsManager()
    comp, tot = mgr.get_progress()
    assert comp == 0
    assert tot == 6
    assert all(not m.is_completed for m in mgr.missions)


def test_missions_manager_handshake():
    """
    Validates mission M1 completion upon observing a successful HELLO handshake round-trip.

    Args:
        None.

    Returns:
        None.

    Side Effects:
        Feeds synthetic TX and RX packet strings into the manager.

    Failure Behavior:
        Fails if mission 'm1_handshake' remains incomplete or missing timestamp.
    """
    mgr = MissionsManager()
    mgr.on_packet_tx("HELLO|CS4S/2.0")
    mgr.on_packet_rx("220 HELLO|CS4S/2.0")
    m1 = mgr.get_mission("m1_handshake")
    assert m1 is not None
    assert m1.is_completed is True
    assert m1.completed_at != ""


def test_missions_manager_auth():
    """
    Validates mission M2 completion upon receiving a successful 230 AUTH_OK server response.

    Args:
        None.

    Returns:
        None.

    Side Effects:
        Feeds synthetic AUTH commands into the manager.

    Failure Behavior:
        Fails if mission 'm2_auth' is not marked as completed.
    """
    mgr = MissionsManager()
    mgr.on_packet_tx("AUTH|admin|admin123")
    mgr.on_packet_rx("230 AUTH_OK")
    m2 = mgr.get_mission("m2_auth")
    assert m2 is not None
    assert m2.is_completed is True


def test_missions_manager_bad_request():
    """
    Validates mission M3 completion upon receiving a 400 BAD_REQUEST response.

    Args:
        None.

    Returns:
        None.

    Side Effects:
        Feeds synthetic invalid command and 400 response.

    Failure Behavior:
        Fails if mission 'm3_bad_req' is not marked as completed.
    """
    mgr = MissionsManager()
    mgr.on_packet_tx("INVALID_CMD")
    mgr.on_packet_rx("400 BAD_REQUEST|Unknown command")
    m3 = mgr.get_mission("m3_bad_req")
    assert m3 is not None
    assert m3.is_completed is True


def test_missions_manager_forbidden():
    """
    Validates mission M4 completion upon detecting path traversal injection and a 403 response.

    Args:
        None.

    Returns:
        None.

    Side Effects:
        Feeds path traversal command and 403 response.

    Failure Behavior:
        Fails if mission 'm4_forbidden' is not marked as completed.
    """
    mgr = MissionsManager()
    mgr.on_packet_tx("DOWNLOAD|../../secret")
    mgr.on_packet_rx("403 FORBIDDEN|Path traversal detected")
    m4 = mgr.get_mission("m4_forbidden")
    assert m4 is not None
    assert m4.is_completed is True


def test_missions_manager_rate_limit():
    """
    Validates mission M5 completion upon receiving a 429 TOO_MANY_REQUESTS response.

    Args:
        None.

    Returns:
        None.

    Side Effects:
        Feeds 429 rate limit response.

    Failure Behavior:
        Fails if mission 'm5_rate_limit' is not marked as completed.
    """
    mgr = MissionsManager()
    mgr.on_packet_rx("429 TOO_MANY_REQUESTS|Rate limit exceeded")
    m5 = mgr.get_mission("m5_rate_limit")
    assert m5 is not None
    assert m5.is_completed is True


def test_missions_manager_tls():
    """
    Validates mission M6 completion upon TLS channel connection event.

    Args:
        None.

    Returns:
        None.

    Side Effects:
        Calls on_tls_connected on the manager.

    Failure Behavior:
        Fails if mission 'm6_tls' is not marked as completed.
    """
    mgr = MissionsManager()
    mgr.on_tls_connected()
    m6 = mgr.get_mission("m6_tls")
    assert m6 is not None
    assert m6.is_completed is True


def test_missions_manager_reset():
    """
    Validates that reset restores all missions to incomplete status.

    Args:
        None.

    Returns:
        None.

    Side Effects:
        Resets internal mission state flags.

    Failure Behavior:
        Fails if completed mission count is non-zero after reset.
    """
    mgr = MissionsManager()
    mgr.on_auth_success()
    comp, _ = mgr.get_progress()
    assert comp == 1
    mgr.reset()
    comp, _ = mgr.get_progress()
    assert comp == 0
