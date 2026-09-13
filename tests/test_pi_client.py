"""
Unit Tests for PIWebApiClient HTTP operations, error handling, and simulation fallback.
"""
import pytest
from unittest.mock import MagicMock
import requests
from requests.exceptions import Timeout, ConnectionError

from src.client.pi_client import PIWebApiClient
from src.client.exceptions import (
    PIException,
    PIAuthenticationError,
    PINotFoundError,
    PIResponseError,
    PITimeoutError,
    PIConnectionError
)


def test_mock_mode_connection():
    client = PIWebApiClient(force_mock=True)
    res = client.test_connection()
    assert res["status"] == "CONNECTED_SIMULATED"
    assert res["is_mock"] is True


def test_mock_get_point_by_path():
    client = PIWebApiClient(force_mock=True)
    point = client.get_point_by_path(r"\\PIDATA01\REACTOR_01_TEMP")
    assert point["Name"] == "REACTOR_01_TEMP"
    assert "WebId" in point


def test_mock_get_stream_value():
    client = PIWebApiClient(force_mock=True)
    dp = client.get_stream_value(web_id="TEST_WEBID", tag_name="REACTOR_01_TEMP")
    assert dp.tag_name == "REACTOR_01_TEMP"
    assert dp.numeric_value is not None
    assert dp.good is True


def test_mock_get_stream_recorded():
    client = PIWebApiClient(force_mock=True)
    stream = client.get_stream_recorded("TEST_WEBID", max_count=30, tag_name="REACTOR_01_TEMP")
    assert len(stream.items) == 30
    assert stream.items[0].tag_name == "REACTOR_01_TEMP"


def test_http_401_authentication_error():
    client = PIWebApiClient(base_url="https://live-pi.com/piwebapi", force_mock=False)
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized Access"
    with pytest.raises(PIAuthenticationError) as exc_info:
        client._handle_response(mock_resp)
    assert "Authentication Failed" in str(exc_info.value)


def test_http_404_not_found_error():
    client = PIWebApiClient(base_url="https://live-pi.com/piwebapi", force_mock=False)
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.text = "Point not found"
    with pytest.raises(PINotFoundError) as exc_info:
        client._handle_response(mock_resp)
    assert "404" in str(exc_info.value)


def test_http_500_server_error():
    client = PIWebApiClient(base_url="https://live-pi.com/piwebapi", force_mock=False)
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "PI Archive Subsystem offline"
    with pytest.raises(PIResponseError) as exc_info:
        client._handle_response(mock_resp)
    assert "500" in str(exc_info.value)
