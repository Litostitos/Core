import requests


class CoreAPIClient:
    """
    Core client for the Store API.
    Handles base URL, JWT token, headers and HTTP requests.
    """
    def __init__(self, base_url, token=None, timeout=10):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def _headers(self):
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _request(self, method, path, **kwargs):
        url = self.base_url + path
        resp = requests.request(
            method,
            url,
            headers=self._headers(),
            timeout=self.timeout,
            **kwargs
        )

        # Basic error handling
        if resp.status_code >= 400:
            try:
                data = resp.json()
            except Exception:
                data = {"message": resp.text}

            raise Exception(f"API Error {resp.status_code}: {data}")

        # Assume JSON API
        return resp.json()

    def get(self, path, **kwargs):
        return self._request("GET", path, **kwargs)

    def post(self, path, json=None, **kwargs):
        return self._request("POST", path, json=json, **kwargs)

    def put(self, path, json=None, **kwargs):
        return self._request("PUT", path, json=json, **kwargs)

    def delete(self, path, **kwargs):
        return self._request("DELETE", path, **kwargs)