"""Single-signal joint owner for polling Engine API proxy and health runtimes."""

from __future__ import annotations

import threading

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_poll_runtime_composition import ManifestHandoffSupervisorEngineApiHealthPollRuntimeBundle
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_poll_runtime_composition import ManifestHandoffSupervisorEngineApiPollRuntimeBundle
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_stop_source import OwnedManifestHandoffSupervisorEngineApiSignalStopSource


class JointManifestHandoffSupervisorEngineApiProcessOwner:
    __slots__ = ("_claimed", "_health", "_join_timeout", "_lock", "_proxy", "_signals")

    def __init__(self, proxy: ManifestHandoffSupervisorEngineApiPollRuntimeBundle,
                 health: ManifestHandoffSupervisorEngineApiHealthPollRuntimeBundle,
                 *, join_timeout_seconds: float) -> None:
        if (type(proxy) is not ManifestHandoffSupervisorEngineApiPollRuntimeBundle
                or type(health) is not ManifestHandoffSupervisorEngineApiHealthPollRuntimeBundle
                or health.health.process_bundle is not proxy.observed_bundle
                or type(join_timeout_seconds) not in (int, float)
                or isinstance(join_timeout_seconds, bool) or join_timeout_seconds <= 0):
            raise ManifestHandoffRegistryUnavailable
        self._proxy, self._health = proxy, health
        self._join_timeout = float(join_timeout_seconds)
        self._signals = OwnedManifestHandoffSupervisorEngineApiSignalStopSource()
        self._lock, self._claimed = threading.Lock(), False

    def run(self):
        with self._lock:
            if self._claimed: raise ManifestHandoffRegistryUnavailable
            self._claimed = True
        stop = threading.Event()
        health_outcome = []
        installed = False
        def requested(): return stop.is_set() or self._signals.requested()
        def run_health():
            try: health_outcome.append(("ok", self._health.process_run.run(requested)))
            except Exception: health_outcome.append(("failed", None))
            finally: stop.set()
        thread = threading.Thread(target=run_health, name="liquent-engine-api-health", daemon=False)
        proxy_result = None
        failed = False
        try:
            self._signals.install(); installed = True
            thread.start()
            proxy_result = self._proxy.process_run.run(requested)
        except Exception:
            failed = True
        stop.set()
        if thread.ident is not None:
            thread.join(self._join_timeout)
            if thread.is_alive(): failed = True
        if installed:
            try: self._signals.restore()
            except Exception: failed = True
        if (failed or proxy_result is None or len(health_outcome) != 1
                or health_outcome[0][0] != "ok"):
            raise ManifestHandoffRegistryUnavailable from None
        return proxy_result, health_outcome[0][1]

    def __repr__(self) -> str:
        return "JointManifestHandoffSupervisorEngineApiProcessOwner()"
