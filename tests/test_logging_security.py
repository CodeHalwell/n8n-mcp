"""Test sensitive data sanitization in audit logs."""
import pytest
from core.logging import _sanitize_dict, SENSITIVE_FIELDS


def test_sanitize_simple_dict():
    """Test sanitization of simple dictionary with sensitive fields."""
    data = {
        "name": "test-credential",
        "password": "secret123",
        "api_key": "abc123xyz",
        "type": "oauth2",
    }

    sanitized = _sanitize_dict(data)

    assert sanitized["name"] == "test-credential"
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["type"] == "oauth2"


def test_sanitize_nested_dict():
    """Test sanitization of nested dictionary."""
    data = {
        "credential": {
            "name": "my-cred",
            "data": {
                "username": "user",
                "password": "secret",
                "apiKey": "key123",
            },
        },
        "metadata": {
            "id": 42,
            "token": "bearer_xyz",
        },
    }

    sanitized = _sanitize_dict(data)

    assert sanitized["credential"]["name"] == "my-cred"
    assert sanitized["credential"]["data"] == "[REDACTED]"
    assert sanitized["metadata"]["id"] == 42
    assert sanitized["metadata"]["token"] == "[REDACTED]"


def test_sanitize_list_of_dicts():
    """Test sanitization of list containing dictionaries."""
    data = [
        {"name": "cred1", "secret": "abc"},
        {"name": "cred2", "password": "xyz"},
    ]

    sanitized = _sanitize_dict(data)

    assert sanitized[0]["name"] == "cred1"
    assert sanitized[0]["secret"] == "[REDACTED]"
    assert sanitized[1]["name"] == "cred2"
    assert sanitized[1]["password"] == "[REDACTED]"


def test_sanitize_max_depth():
    """Test that excessive recursion is prevented."""
    # Create a deeply nested structure
    data = {"level1": {"level2": {"level3": {"level4": {"level5": {"level6": {"level7": {"level8": {"level9": {"level10": {"level11": "too deep"}}}}}}}}}}}

    sanitized = _sanitize_dict(data)

    # Should stop at depth 10 and return special marker
    assert "[MAX_DEPTH_EXCEEDED]" in str(sanitized)


def test_sanitize_preserves_non_sensitive():
    """Test that non-sensitive data is preserved."""
    data = {
        "workflow_id": "123",
        "name": "My Workflow",
        "active": True,
        "nodes": [
            {"type": "webhook", "name": "Trigger"},
        ],
        "tags": ["production", "important"],
    }

    sanitized = _sanitize_dict(data)

    assert sanitized == data  # Should be identical


def test_all_sensitive_fields_covered():
    """Test that all common sensitive field names are covered."""
    common_sensitive_fields = {
        "password", "api_key", "apiKey", "secret", "token",
        "accessToken", "refreshToken", "privateKey", "clientSecret"
    }

    # Check that all common fields are in SENSITIVE_FIELDS
    assert common_sensitive_fields.issubset(SENSITIVE_FIELDS)


def test_sanitize_primitives():
    """Test sanitization of primitive values (should pass through)."""
    assert _sanitize_dict("string") == "string"
    assert _sanitize_dict(123) == 123
    assert _sanitize_dict(True) is True
    assert _sanitize_dict(None) is None
