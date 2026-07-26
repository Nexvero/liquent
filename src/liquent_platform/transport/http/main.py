"""Production control-plane entry point."""

from __future__ import annotations

from pathlib import Path

import uvicorn

from liquent_platform.configuration import PlatformSettings
from liquent_platform.observability.logging import configure_logging
from liquent_platform.transport.http.app import create_app


def main() -> None:
    settings = PlatformSettings(_secrets_dir=Path("/run/secrets"))
    configure_logging(settings.log_level.value, settings.log_format)
    uvicorn.run(
        create_app(settings),
        host=settings.http_host,
        port=settings.http_port,
        log_level=settings.log_level.value.lower(),
        access_log=True,
    )


if __name__ == "__main__":
    main()
