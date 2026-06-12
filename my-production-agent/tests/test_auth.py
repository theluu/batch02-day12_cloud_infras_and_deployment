"""Unit tests — authentication."""
import pytest
from fastapi import HTTPException

from app.auth import verify_api_key


def test_valid_single_key_returns_default_user():
    assert verify_api_key("test-key") == "default"


def test_valid_mapped_key_returns_user_id():
    assert verify_api_key("alice-key") == "alice"
    assert verify_api_key("bob-key") == "bob"


def test_missing_key_raises_401():
    with pytest.raises(HTTPException) as exc:
        verify_api_key(None)
    assert exc.value.status_code == 401


def test_invalid_key_raises_401():
    with pytest.raises(HTTPException) as exc:
        verify_api_key("wrong-key")
    assert exc.value.status_code == 401
