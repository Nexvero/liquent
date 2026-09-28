"""One-shot child-owned load, gate, execute, and terminal sequence."""

from datetime import datetime, timezone

from liquent_platform.identity.manifest_handoff_supervisor import (
    ManifestHandoffRecoverySupervisorRequest,
    ManifestHandoffWriterSupervisorRequest,
    PreparedManifestHandoffRecoveryProcess,
    PreparedManifestHandoffWriterProcess,
)
from liquent_platform.identity.manifest_handoff_supervisor_capability_executor import (
    ExecuteManifestHandoffRecoveryCapability,
    ExecuteManifestHandoffWriterCapability,
    ExecutedManifestHandoffRecoveryCapability,
    ExecutedManifestHandoffWriterCapability,
)
from liquent_platform.identity.manifest_handoff_supervisor_engine import (
    ManifestHandoffSupervisorEngineProfile,
)
from liquent_platform.identity.manifest_handoff_supervisor_gate_wrapper import (
    AcceptedManifestHandoffSupervisorReleaseToken,
    CompleteManifestHandoffSupervisorGateWrapper,
    CompletedManifestHandoffSupervisorGateWrapper,
    ManifestHandoffSupervisorGateWrapperConflict,
    ReadyManifestHandoffSupervisorGateWrapper,
    ReleasedManifestHandoffSupervisorGateWrapper,
)
from liquent_platform.identity.manifest_handoff_supervisor_launch_document import (
    ManifestHandoffSupervisorLaunchDocumentExpectation,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


class OneShotManifestHandoffSupervisorChildProcess:
    """Own one bounded wrapper lifetime; never accepts caller authority."""

    __slots__ = (
        "_clock", "_executor", "_loader", "_maximum_wait", "_monotonic",
        "_poll_interval", "_sleep", "_wrapper",
    )

    def __init__(self, *, loader, gate_wrapper, executor, clock, monotonic,
                 sleep, maximum_release_wait: float, poll_interval: float) -> None:
        if (loader is None or gate_wrapper is None or executor is None
                or not callable(clock) or not callable(monotonic) or not callable(sleep)
                or type(maximum_release_wait) not in (int, float)
                or type(poll_interval) not in (int, float)
                or maximum_release_wait <= 0 or poll_interval <= 0
                or poll_interval > maximum_release_wait):
            raise ManifestHandoffRegistryUnavailable
        self._loader, self._wrapper, self._executor = loader, gate_wrapper, executor
        self._clock, self._monotonic, self._sleep = clock, monotonic, sleep
        self._maximum_wait = float(maximum_release_wait)
        self._poll_interval = float(poll_interval)

    def __repr__(self) -> str:
        return "OneShotManifestHandoffSupervisorChildProcess()"

    def run_writer(self, expectation):
        return self._run(
            expectation, ManifestHandoffSupervisorEngineProfile.WRITER,
            ManifestHandoffWriterSupervisorRequest,
            PreparedManifestHandoffWriterProcess,
            ExecuteManifestHandoffWriterCapability,
            ExecutedManifestHandoffWriterCapability,
            self._executor.execute_writer,
        )

    def run_recovery(self, expectation):
        return self._run(
            expectation, ManifestHandoffSupervisorEngineProfile.RECOVERY,
            ManifestHandoffRecoverySupervisorRequest,
            PreparedManifestHandoffRecoveryProcess,
            ExecuteManifestHandoffRecoveryCapability,
            ExecutedManifestHandoffRecoveryCapability,
            self._executor.execute_recovery,
        )

    def _run(self, expectation, profile, request_type, prepared_type,
             execution_type, executed_type, execute):
        if (type(expectation) is not ManifestHandoffSupervisorLaunchDocumentExpectation
                or expectation.profile is not profile):
            raise ManifestHandoffRegistryUnavailable
        try:
            document = self._loader.load(expectation)
            if (document.gate.profile is not profile
                    or type(document.request) is not request_type):
                raise ManifestHandoffRegistryUnavailable
            ready = self._wrapper.publish_ready(document.gate)
            if type(ready) is ManifestHandoffSupervisorGateWrapperConflict:
                return ready
            if type(ready) is not ReadyManifestHandoffSupervisorGateWrapper:
                raise ManifestHandoffRegistryUnavailable
            token = self._wait_release(ready)
            released = self._wrapper.publish_consumed(token)
            if type(released) is ManifestHandoffSupervisorGateWrapperConflict:
                return released
            if type(released) is not ReleasedManifestHandoffSupervisorGateWrapper:
                raise ManifestHandoffRegistryUnavailable
            prepared_at = self._clock()
            if (type(prepared_at) is not datetime or prepared_at.tzinfo is None
                    or prepared_at.utcoffset() != timezone.utc.utcoffset(prepared_at)):
                raise ManifestHandoffRegistryUnavailable
            request = document.request
            prepared = prepared_type(
                document.gate.handle_id, request.claim_id, request.owner_id, prepared_at
            )
            executed = execute(execution_type(released, prepared, request))
            if type(executed) is not executed_type:
                raise ManifestHandoffRegistryUnavailable
            terminal = self._wrapper.publish_terminal(
                CompleteManifestHandoffSupervisorGateWrapper(released, executed.outcome)
            )
            if type(terminal) is ManifestHandoffSupervisorGateWrapperConflict:
                return terminal
            if type(terminal) is not CompletedManifestHandoffSupervisorGateWrapper:
                raise ManifestHandoffRegistryUnavailable
            return terminal
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def _wait_release(self, ready):
        started = self._monotonic()
        if type(started) not in (int, float):
            raise ManifestHandoffRegistryUnavailable
        deadline = float(started) + self._maximum_wait
        while True:
            token = self._wrapper.await_release(ready)
            if token is not None:
                if type(token) is not AcceptedManifestHandoffSupervisorReleaseToken:
                    raise ManifestHandoffRegistryUnavailable
                return token
            current = self._monotonic()
            if type(current) not in (int, float) or current < started:
                raise ManifestHandoffRegistryUnavailable
            if current >= deadline:
                raise ManifestHandoffRegistryUnavailable
            self._sleep(min(self._poll_interval, deadline - current))
