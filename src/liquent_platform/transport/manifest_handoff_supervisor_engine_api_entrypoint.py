"""Owner-controlled one-shot process boundary for the private Engine API proxy."""

from __future__ import annotations

import argparse
from pathlib import Path

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_composition import (
    compose_manifest_handoff_supervisor_engine_api_proxy_bundle,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_serve_loop import (
    ManifestHandoffSupervisorEngineApiServeResult,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_settings_source import (
    load_manifest_handoff_supervisor_engine_api_proxy_settings,
)


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ManifestHandoffRegistryUnavailable


def run_manifest_handoff_supervisor_engine_api_proxy(
    settings_file: Path,
) -> ManifestHandoffSupervisorEngineApiServeResult:
    """Load, compose and run exactly one explicitly configured proxy process."""
    try:
        if not isinstance(settings_file, Path):
            raise ManifestHandoffRegistryUnavailable
        settings = load_manifest_handoff_supervisor_engine_api_proxy_settings(
            settings_file
        )
        bundle = compose_manifest_handoff_supervisor_engine_api_proxy_bundle(settings)
        result = bundle.process_run.run()
        if (
            type(result) is not ManifestHandoffSupervisorEngineApiServeResult
            or result.reason not in {"stopped", "exchange_limit"}
            or type(result.exchanges) is not int
            or result.exchanges < 0
            or result.exchanges > settings.maximum_exchanges
            or (result.reason == "exchange_limit"
                and result.exchanges != settings.maximum_exchanges)
        ):
            raise ManifestHandoffRegistryUnavailable
        return result
    except ManifestHandoffRegistryUnavailable:
        raise
    except Exception:
        raise ManifestHandoffRegistryUnavailable from None


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(
        prog="liquent-supervisor-engine-api-proxy", add_help=False
    )
    parser.add_argument("--settings-file", required=True, type=Path)
    try:
        arguments = parser.parse_args(argv)
        run_manifest_handoff_supervisor_engine_api_proxy(arguments.settings_file)
        return 0
    except Exception:
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
