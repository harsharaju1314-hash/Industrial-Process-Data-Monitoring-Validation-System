"""
Unit Tests for PI Web API Authentication & Header Construction.
"""
from src.client.auth import PIAuthHandler


def test_auth_headers():
    handler = PIAuthHandler(auth_mode="mock")
    headers = handler.get_headers()
    assert headers["Accept"] == "application/json"
    assert headers["Content-Type"] == "application/json"
    assert headers["X-Requested-With"] == "XMLHttpRequest"


def test_basic_auth_creation():
    handler = PIAuthHandler(auth_mode="basic", username="testuser", password="secretpassword")
    auth_obj = handler.get_requests_auth()
    assert auth_obj is not None
    assert auth_obj.username == "testuser"
    assert auth_obj.password == "secretpassword"


def test_mock_auth_no_creds():
    handler = PIAuthHandler(auth_mode="mock")
    auth_obj = handler.get_requests_auth()
    assert auth_obj is None
