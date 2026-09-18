from src.ui.widgets.missions import MissionsManager


def test_missions_manager_initial_state():
    mgr = MissionsManager()
    comp, tot = mgr.get_progress()
    assert comp == 0
    assert tot == 6
    assert all(not m.is_completed for m in mgr.missions)


def test_missions_manager_handshake():
    mgr = MissionsManager()
    mgr.on_packet_tx("HELLO|CS4S/2.0")
    mgr.on_packet_rx("220 HELLO|CS4S/2.0")
    m1 = mgr.get_mission("m1_handshake")
    assert m1 is not None
    assert m1.is_completed is True
    assert m1.completed_at != ""


def test_missions_manager_auth():
    mgr = MissionsManager()
    mgr.on_packet_tx("AUTH|admin|admin123")
    mgr.on_packet_rx("230 AUTH_OK")
    m2 = mgr.get_mission("m2_auth")
    assert m2 is not None
    assert m2.is_completed is True


def test_missions_manager_bad_request():
    mgr = MissionsManager()
    mgr.on_packet_tx("INVALID_CMD")
    mgr.on_packet_rx("400 BAD_REQUEST|Unknown command")
    m3 = mgr.get_mission("m3_bad_req")
    assert m3 is not None
    assert m3.is_completed is True


def test_missions_manager_forbidden():
    mgr = MissionsManager()
    mgr.on_packet_tx("DOWNLOAD|../../secret")
    mgr.on_packet_rx("403 FORBIDDEN|Path traversal detected")
    m4 = mgr.get_mission("m4_forbidden")
    assert m4 is not None
    assert m4.is_completed is True


def test_missions_manager_rate_limit():
    mgr = MissionsManager()
    mgr.on_packet_rx("429 TOO_MANY_REQUESTS|Rate limit exceeded")
    m5 = mgr.get_mission("m5_rate_limit")
    assert m5 is not None
    assert m5.is_completed is True


def test_missions_manager_tls():
    mgr = MissionsManager()
    mgr.on_tls_connected()
    m6 = mgr.get_mission("m6_tls")
    assert m6 is not None
    assert m6.is_completed is True


def test_missions_manager_reset():
    mgr = MissionsManager()
    mgr.on_auth_success()
    comp, _ = mgr.get_progress()
    assert comp == 1
    mgr.reset()
    comp, _ = mgr.get_progress()
    assert comp == 0
