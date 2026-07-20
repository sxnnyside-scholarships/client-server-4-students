"""
Module: test_auth.py
────────────────────
Purpose: Validates credential persistence and verification.

Architectural Role:
Unit testing for the `AuthManager` component.

Responsibilities:
- Verify that users can be safely added and validated.
- Ensure state persists correctly to the underlying JSON file.

Expected Collaborators:
- `pytest` (test runner).
- `src.storage.auth.AuthManager` (the subject under test).
"""

from src.storage.auth import AuthManager


def test_auth_manager_lifecycle(mock_users_file):
    """
    Validates the full lifecycle of an AuthManager instance.

    Args:
        mock_users_file: Pytest fixture providing a safe JSON sandbox.

    Returns:
        None.

    Side Effects:
        Writes JSON files to the temporary directory.

    Failure Behavior:
        Fails if users are improperly validated or persistence breaks.
        
    Ensure users can be added, verified, and that data persists across 
    manager instances (simulating server restarts).
    """
    auth = AuthManager(mock_users_file)
    
    # Defaults are created if file doesn't exist
    assert auth.verify("student", "student") is True
    
    # Adding a new valid user
    assert auth.add_user("test1", "password123") is True
    assert auth.verify("test1", "password123") is True
    assert auth.verify("test1", "wrong") is False
    
    # Invalid usernames are rejected deterministically
    assert auth.add_user("../admin", "hack") is False
    
    # Duplicate users are rejected
    assert auth.add_user("test1", "other") is False
    
    # Verify persistence by loading a fresh instance from the same mock file
    auth2 = AuthManager(mock_users_file)
    assert auth2.verify("test1", "password123") is True
