"""API client retry semantics: 429/Retry-After handling and size caps."""
from unittest import mock

import pytest
import requests

from exilebot_pickit.api import client


def _resp(status, headers=None, body=b"{}"):
    r = mock.Mock(spec=requests.Response)
    r.status_code = status
    r.headers = headers or {}
    r.iter_content = lambda n: iter([body])
    if status >= 400:
        err = requests.HTTPError(response=r)
        r.raise_for_status = mock.Mock(side_effect=err)
    else:
        r.raise_for_status = mock.Mock()
    return r


def test_non_retryable_raises_immediately():
    with mock.patch.object(client.requests, "get", return_value=_resp(404)) as g:
        with pytest.raises(requests.HTTPError):
            client._request_with_retry("https://x", {})
        assert g.call_count == 1     # no retries on 404


def test_429_honors_retry_after(monkeypatch):
    sleeps = []
    monkeypatch.setattr(client.time, "sleep", sleeps.append)
    responses = [_resp(429, {"Retry-After": "2"}), _resp(200, body=b'{"ok": 1}')]
    with mock.patch.object(client.requests, "get", side_effect=responses):
        out = client._request_with_retry("https://x", {})
    assert out == {"ok": 1}
    assert sleeps == [2.0]           # slept exactly what the server asked


def test_429_with_huge_retry_after_gives_up():
    # Server asks to wait longer than we're willing to hang the run —
    # raise so the caller falls back to the disk cache.
    with mock.patch.object(client.requests, "get",
                           return_value=_resp(429, {"Retry-After": "300"})) as g:
        with pytest.raises(requests.HTTPError):
            client._request_with_retry("https://x", {})
        assert g.call_count == 1


def test_transient_errors_retry_with_backoff(monkeypatch):
    sleeps = []
    monkeypatch.setattr(client.time, "sleep", sleeps.append)
    responses = [requests.ConnectionError(), _resp(200, body=b'{"ok": 2}')]
    with mock.patch.object(client.requests, "get", side_effect=responses):
        out = client._request_with_retry("https://x", {})
    assert out == {"ok": 2}
    assert len(sleeps) == 1


def test_oversized_response_rejected(monkeypatch):
    monkeypatch.setattr(client, "_JSON_MAX_BYTES", 10)
    with mock.patch.object(client.requests, "get",
                           return_value=_resp(200, body=b"x" * 100)):
        with pytest.raises(ValueError):
            client.fetch_json("https://x", {})
