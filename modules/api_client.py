"""Unified HTTP client base with retry, timeout, and error handling."""
import json
import urllib.request
import urllib.error
import urllib.parse
from typing import Any, Dict, Optional


class APIClientBase:
    def __init__(self, base_url: str, api_key: str = "", timeout: int = 10, max_retries: int = 1):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self._urlopen = urllib.request.urlopen

    def _build_request(self, method: str, path: str, params: Dict = None) -> tuple:
        params = dict(params or {})
        if self.api_key and "key" not in params:
            params["key"] = self.api_key

        if method == "GET":
            query = urllib.parse.urlencode(params)
            url = f"{self.base_url}{path}?{query}" if params else f"{self.base_url}{path}"
            return url, params
        else:
            url = f"{self.base_url}{path}"
            return url, params

    def _request(self, method: str, path: str, params: Dict = None) -> Dict:
        url, params = self._build_request(method, path, params)
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                if method == "GET":
                    req = urllib.request.Request(url, method="GET")
                else:
                    data = json.dumps(params).encode("utf-8")
                    req = urllib.request.Request(
                        url, data=data,
                        headers={"Content-Type": "application/json"},
                        method=method
                    )

                with self._urlopen(req, timeout=self.timeout) as resp:
                    body = resp.read().decode("utf-8")
                    return json.loads(body)

            except (ConnectionError, urllib.error.URLError, TimeoutError) as e:
                last_error = e
                if attempt < self.max_retries:
                    continue
                raise

        raise last_error

    def get(self, path: str, params: Dict = None) -> Dict:
        return self._request("GET", path, params)

    def post(self, path: str, params: Dict = None) -> Dict:
        return self._request("POST", path, params)
