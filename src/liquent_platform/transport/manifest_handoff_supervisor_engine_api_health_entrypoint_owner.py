"""One-shot owner for an explicitly composed Engine API health entrypoint."""

from __future__ import annotations

import threading

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_entrypoint_bundle import ManifestHandoffSupervisorEngineApiHealthEntrypointBundle
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_serve_loop import ManifestHandoffSupervisorEngineApiHealthServeResult


class ManifestHandoffSupervisorEngineApiHealthEntrypointOwner:
    __slots__ = ("_bundle", "_claimed", "_lock")

    def __init__(self, bundle: ManifestHandoffSupervisorEngineApiHealthEntrypointBundle) -> None:
        if type(bundle) is not ManifestHandoffSupervisorEngineApiHealthEntrypointBundle:
            raise ManifestHandoffRegistryUnavailable
        self._bundle = bundle
        self._claimed = False
        self._lock = threading.Lock()

    def __repr__(self) -> str:
        return "ManifestHandoffSupervisorEngineApiHealthEntrypointOwner()"

    def run(self) -> ManifestHandoffSupervisorEngineApiHealthServeResult:
        with self._lock:
            if self._claimed:
                raise ManifestHandoffRegistryUnavailable
            self._claimed = True
        try:
            result = self._bundle.process_run.run()
            maximum = self._bundle.transport.serve_loop._maximum
            if (type(result) is not ManifestHandoffSupervisorEngineApiHealthServeResult
                    or result.exchanges > maximum
                    or (result.reason == "exchange_limit" and result.exchanges != maximum)):
                raise ManifestHandoffRegistryUnavailable
            return result
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
