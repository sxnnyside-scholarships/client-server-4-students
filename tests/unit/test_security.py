"""
Module: test_security.py
────────────────────────
Purpose: Validates deterministic behavior of input sanitization and rate limit systems.

Architectural Role:
Unit testing for the `security.py` module. 

Responsibilities:
- Verify that `is_valid_username` correctly blocks traversal attacks (`../`).
- Verify that `SecurityContext` abuse thresholds trigger socket drops when exceeded.

Expected Collaborators:
- `pytest` (test runner).
- `src.network.security` (the subject under test).
"""

from src.network.security import BanRegistry, SecurityContext, is_valid_username


def test_is_valid_username():
    """
    Validates the strict alphanumeric allow-list for usernames.

    Args:
        None.

    Returns:
        None.

    Side Effects:
        None.

    Failure Behavior:
        Fails if spaces or traversal characters (`.`, `/`, `\\`) bypass the regex.
    """
    assert is_valid_username("student123") is True
    assert is_valid_username("valid-name_") is True
    assert is_valid_username("abc") is True
    assert is_valid_username("a" * 32) is True
    
    assert is_valid_username("") is False
    assert is_valid_username("ab") is False  # too short
    assert is_valid_username("a" * 33) is False  # too long
    assert is_valid_username("student name") is False
    assert is_valid_username("../root") is False
    assert is_valid_username("name/other") is False
    assert is_valid_username("user\0") is False


def test_security_context_rate_limits(mocker):
    """
    Validates per-connection abuse thresholds.

    Args:
        mocker: Pytest mock fixture.

    Returns:
        None.

    Side Effects:
        Mocks `time.sleep` to bypass temporal IP bans quickly during tests.

    Failure Behavior:
        Fails if the context object returns False on the 5th bad auth attempt.
    """
    mocker.patch("time.sleep")
    
    ctx = SecurityContext("127.0.0.1")
    
    # 5 auth failures drops the connection
    for _ in range(4):
        assert ctx.record_auth_failure() is False
    assert ctx.record_auth_failure() is True
    
    # 10 invalid commands drops the connection
    ctx2 = SecurityContext("127.0.0.1")
    for _ in range(9):
        assert ctx2.record_invalid_command() is False
    assert ctx2.record_invalid_command() is True


def test_ban_registry_is_instance_scoped():
    """
    Regression test: IP bans must not leak across separate server instances.

    Previously `_BANNED_IPS` was a module-level global, so a ban recorded by
    one `ServerNetworkEngine`/test would silently persist into any other
    instance sharing the process. Each `CommandDispatcher` now owns its own
    `BanRegistry`, so two independent registries must not see each other's bans.
    """
    registry_a = BanRegistry()
    registry_b = BanRegistry()

    registry_a.ban("10.0.0.5")

    assert registry_a.is_banned("10.0.0.5") is True
    assert registry_b.is_banned("10.0.0.5") is False


def test_ban_registry_expiry(mocker):
    """
    Validates that a ban expires and is cleaned up after its duration elapses.
    """
    registry = BanRegistry(ban_duration_sec=10.0)
    fake_time = mocker.patch("src.network.security.time.time")

    fake_time.return_value = 1000.0
    registry.ban("10.0.0.5")
    assert registry.is_banned("10.0.0.5") is True

    fake_time.return_value = 1011.0
    assert registry.is_banned("10.0.0.5") is False
