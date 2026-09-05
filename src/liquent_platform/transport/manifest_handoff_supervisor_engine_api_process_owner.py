"""Single-claim run and concurrent health ownership for one proxy bundle."""

from __future__ import annotations

import threading

from liquent_platform.application.health import Readiness
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_composition import (
    ManifestHandoffSupervisorEngineApiProcessBundle,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_process_status import (
    ManifestHandoffSupervisorEngineApiProcessSnapshot,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_serve_loop import (
    ManifestHandoffSupervisorEngineApiServeResult,
)


class ManifestHandoffSupervisorEngineApiProcessOwner:
    """Allow one run claimant while exposing read-only concurrent health."""

    __slots__ = ("_bundle", "_claim_lock", "_claimed")

    def __init__(self, bundle: ManifestHandoffSupervisorEngineApiProcessBundle) -> None:
        if type(bundle) is not ManifestHandoffSupervisorEngineApiProcessBundle:
            raise ManifestHandoffRegistryUnavailable
        self._bundle = bundle
        self._claim_lock = threading.Lock()
        self._claimed = False

    def __repr__(self) -> str:
        return "ManifestHandoffSupervisorEngineApiProcessOwner()"

    def run(self) -> ManifestHandoffSupervisorEngineApiServeResult:
        with self._claim_lock:
            if self._claimed:
                raise ManifestHandoffRegistryUnavailable
            self._claimed = True
        try:
            result = self._bundle.process_run.run()
            if type(result) is not ManifestHandoffSupervisorEngineApiServeResult:
                raise ManifestHandoffRegistryUnavailable
            return result
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def readiness(self) -> Readiness:
        try:
            result = self._bundle.readiness.check()
            if type(result) is not Readiness:
                raise ManifestHandoffRegistryUnavailable
            return result
        except Exception:
            return Readiness(
                False, "manifest_handoff_supervisor_engine_api_unavailable"
            )

    def snapshot(self) -> ManifestHandoffSupervisorEngineApiProcessSnapshot:
        try:
            result = self._bundle.status.snapshot()
            if type(result) is not ManifestHandoffSupervisorEngineApiProcessSnapshot:
                raise ManifestHandoffRegistryUnavailable
            return result
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
