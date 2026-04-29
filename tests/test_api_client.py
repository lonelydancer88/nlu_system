"""Tests for APIClientBase - unified HTTP client with retry and error handling."""
import json
import os
import pytest
import sys
from unittest.mock import patch, MagicMock
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestAPIClientBase:
    def test_get_request(self):
        from modules.api_client import APIClientBase
        client = APIClientBase(base_url="https://httpbin.org")
        # Test the _request method builds correct URL and parses JSON
        with patch.object(client, '_request') as mock_req:
            mock_req.return_value = {"status": 0, "data": "ok"}
            result = client.get("/test", {"key": "val"})
            mock_req.assert_called_once_with("GET", "/test", {"key": "val"})

    def test_request_builds_url_with_params(self):
        from modules.api_client import APIClientBase
        client = APIClientBase(base_url="https://restapi.amap.com/v3", api_key="test_key")
        url, params = client._build_request("GET", "/geocode/geo", {"address": "北京"})
        assert "restapi.amap.com" in url
        assert params["key"] == "test_key"
        assert params["address"] == "北京"

    def test_request_timeout_default(self):
        from modules.api_client import APIClientBase
        client = APIClientBase(base_url="https://example.com")
        assert client.timeout == 10

    def test_request_timeout_custom(self):
        from modules.api_client import APIClientBase
        client = APIClientBase(base_url="https://example.com", timeout=30)
        assert client.timeout == 30

    def test_retry_on_network_error(self):
        from modules.api_client import APIClientBase
        client = APIClientBase(base_url="https://example.com", max_retries=2)
        call_count = 0
        original_urlopen = client._urlopen

        def mock_urlopen(req, timeout=None):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("network error")
            resp = MagicMock()
            resp.read.return_value = json.dumps({"status": 0}).encode()
            resp.__enter__ = MagicMock(return_value=resp)
            resp.__exit__ = MagicMock(return_value=False)
            return resp

        client._urlopen = mock_urlopen
        result = client.get("/test")
        assert result["status"] == 0
        assert call_count == 3

    def test_max_retries_exhausted(self):
        from modules.api_client import APIClientBase
        client = APIClientBase(base_url="https://example.com", max_retries=1)

        def mock_urlopen(req, timeout=None):
            raise ConnectionError("persistent error")

        client._urlopen = mock_urlopen
        with pytest.raises(ConnectionError):
            client.get("/test")

    def test_successful_request_no_retry(self):
        from modules.api_client import APIClientBase
        client = APIClientBase(base_url="https://example.com", max_retries=2)
        call_count = 0

        def mock_urlopen(req, timeout=None):
            nonlocal call_count
            call_count += 1
            resp = MagicMock()
            resp.read.return_value = json.dumps({"status": 0}).encode()
            resp.__enter__ = MagicMock(return_value=resp)
            resp.__exit__ = MagicMock(return_value=False)
            return resp

        client._urlopen = mock_urlopen
        client.get("/test")
        assert call_count == 1

    def test_api_error_response(self):
        from modules.api_client import APIClientBase
        client = APIClientBase(base_url="https://example.com")

        def mock_urlopen(req, timeout=None):
            resp = MagicMock()
            resp.read.return_value = json.dumps({"status": "1", "info": "INVALID_USER_KEY"}).encode()
            resp.__enter__ = MagicMock(return_value=resp)
            resp.__exit__ = MagicMock(return_value=False)
            return resp

        client._urlopen = mock_urlopen
        result = client.get("/test")
        assert result["status"] == "1"

    def test_post_request(self):
        from modules.api_client import APIClientBase
        client = APIClientBase(base_url="https://example.com")
        with patch.object(client, '_request') as mock_req:
            mock_req.return_value = {"status": 0}
            client.post("/orders", {"item": "coffee"})
            mock_req.assert_called_once_with("POST", "/orders", {"item": "coffee"})
