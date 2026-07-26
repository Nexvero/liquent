"""Production control-plane entry point."""

from __future__ import annotations

from pathlib import Path

import uvicorn

from liquent_platform.application.local_csv import LocalCsvMidBreakoutV0Resolver
from liquent_platform.configuration import PlatformSettings
from liquent_platform.observability.logging import configure_logging
from liquent_platform.transport.http.app import create_app


def build_app(settings: PlatformSettings):
    """Build the configured app; local research remains explicit opt-in."""

    resolver = None
    if settings.research_data_root is not None:
        resolver = LocalCsvMidBreakoutV0Resolver(settings.research_data_root)
    return create_app(settings, research_resolver=resolver)


def main() -> None:
    settings = PlatformSettings(_secrets_dir=Path("/run/secrets"))
    configure_logging(settings.log_level.value, settings.log_format)
    uvicorn.run(
        build_app(settings),
        host=settings.http_host,
        port=settings.http_port,
        log_level=settings.log_level.value.lower(),
        access_log=True,
    )


if __name__ == "__main__":
    main()
