from __future__ import annotations

from io import BytesIO

import pytest

from liquent_platform.observability import external_health


class _Response(BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def test_external_health_accepts_exact_expected_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        external_health,
        "urlopen",
        lambda request, timeout: _Response(
            b'{"status":"ok","service":"liquent-control-plane"}'
        ),
    )
    result = external_health.check_external_health("https://liquent.ai/health/live")
    assert result.ok is True
    assert result.status_code == 200
    assert result.reason == "healthy"


@pytest.mark.parametrize(
    "url",
    (
        "http://liquent.ai/health/live",
        "https://user:pass@liquent.ai/health/live",
        "/health/live",
    ),
)
def test_external_health_rejects_unsafe_urls(url: str) -> None:
    result = external_health.check_external_health(url)
    assert result.ok is False
    assert result.reason == "invalid_url"


def test_external_health_fails_closed_on_bad_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        external_health,
        "urlopen",
        lambda request, timeout: _Response(b'{"status":"degraded"}'),
    )
    result = external_health.check_external_health("https://liquent.ai/health/live")
    assert result.ok is False
    assert result.reason == "unexpected_response"


def test_external_health_fails_closed_on_transport_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(request: object, timeout: float) -> None:
        raise TimeoutError

    monkeypatch.setattr(external_health, "urlopen", fail)
    result = external_health.check_external_health("https://liquent.ai/health/live")
    assert result.ok is False
    assert result.reason == "request_failed"
