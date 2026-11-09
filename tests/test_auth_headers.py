"""Tests for the shared Bearer header builder (spec AC-10, AC-11)."""

from src.utils.auth_headers import auth_headers


def test_auth_headers_returns_bearer_for_key():
    assert auth_headers("sk-abc") == {"Authorization": "Bearer sk-abc"}


def test_auth_headers_empty_for_none():
    assert auth_headers(None) == {}


def test_auth_headers_empty_for_empty_string():
    assert auth_headers("") == {}
