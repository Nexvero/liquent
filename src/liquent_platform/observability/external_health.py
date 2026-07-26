"""Small external liveness probe for deployment smoke checks."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from time import monotonic
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ExternalHealthResult:
    ok: bool
    status_code: int
    duration_ms: float
    reason: str


def check_external_health(
    url: str,
    *,
    timeout: float = 5.0,
    allow_http: bool = False,
) -> ExternalHealthResult:
    parsed = urlsplit(url)
    allowed_schemes = {"https"} | ({"http"} if allow_http else set())
    if parsed.scheme not in allowed_schemes or not parsed.hostname or parsed.username:
        return ExternalHealthResult(False, 0, 0.0, "invalid_url")

    started = monotonic()
    request = Request(url, headers={"User-Agent": "liquent-health-check/1"})
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - URL validated above
            status_code = int(response.status)
            payload = json.loads(response.read(4096))
    except Exception:
        return ExternalHealthResult(
            False,
            0,
            round((monotonic() - started) * 1000, 3),
            "request_failed",
        )
    duration_ms = round((monotonic() - started) * 1000, 3)
    if status_code != 200 or payload != {"status": "ok", "service": "liquent-control-plane"}:
        return ExternalHealthResult(False, status_code, duration_ms, "unexpected_response")
    return ExternalHealthResult(True, status_code, duration_ms, "healthy")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check Liquent public liveness.")
    parser.add_argument("url", help="HTTPS URL ending in /health/live")
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()
    result = check_external_health(args.url, timeout=args.timeout)
    print(json.dumps(asdict(result), separators=(",", ":")))
    raise SystemExit(0 if result.ok else 1)


if __name__ == "__main__":
    main()
