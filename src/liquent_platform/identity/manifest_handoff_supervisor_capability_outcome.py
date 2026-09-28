"""Read-only observations for an already released capability execution."""

from dataclasses import dataclass, field

from .manifest_handoff_supervisor import (
    RunningManifestHandoffRecoveryProcess,
    RunningManifestHandoffWriterProcess,
)
from .manifest_handoff_supervisor_capability_executor import (
    ExecuteManifestHandoffRecoveryCapability,
    ExecuteManifestHandoffWriterCapability,
    ExecutedManifestHandoffRecoveryCapability,
    ExecutedManifestHandoffWriterCapability,
)


@dataclass(frozen=True, slots=True)
class InspectManifestHandoffWriterCapabilityOutcome:
    execution: ExecuteManifestHandoffWriterCapability = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.execution) is not ExecuteManifestHandoffWriterCapability:
            raise ValueError("manifest handoff writer outcome inspection is invalid")


@dataclass(frozen=True, slots=True)
class InspectManifestHandoffRecoveryCapabilityOutcome:
    execution: ExecuteManifestHandoffRecoveryCapability = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.execution) is not ExecuteManifestHandoffRecoveryCapability:
            raise ValueError("manifest handoff recovery outcome inspection is invalid")


@dataclass(frozen=True, slots=True)
class RunningManifestHandoffWriterCapability:
    inspection: InspectManifestHandoffWriterCapabilityOutcome = field(repr=False)
    state: RunningManifestHandoffWriterProcess = field(repr=False)

    def __post_init__(self) -> None:
        if (type(self.inspection) is not InspectManifestHandoffWriterCapabilityOutcome
                or type(self.state) is not RunningManifestHandoffWriterProcess
                or self.state.handle_id != self.inspection.execution.prepared.handle_id
                or self.state.claim_id != self.inspection.execution.prepared.claim_id
                or self.state.owner_id != self.inspection.execution.prepared.owner_id):
            raise ValueError("manifest handoff running writer capability is invalid")


@dataclass(frozen=True, slots=True)
class RunningManifestHandoffRecoveryCapability:
    inspection: InspectManifestHandoffRecoveryCapabilityOutcome = field(repr=False)
    state: RunningManifestHandoffRecoveryProcess = field(repr=False)

    def __post_init__(self) -> None:
        if (type(self.inspection) is not InspectManifestHandoffRecoveryCapabilityOutcome
                or type(self.state) is not RunningManifestHandoffRecoveryProcess
                or self.state.handle_id != self.inspection.execution.prepared.handle_id
                or self.state.claim_id != self.inspection.execution.prepared.claim_id
                or self.state.owner_id != self.inspection.execution.prepared.owner_id):
            raise ValueError("manifest handoff running recovery capability is invalid")


ManifestHandoffWriterCapabilityOutcomeObservation = (
    RunningManifestHandoffWriterCapability | ExecutedManifestHandoffWriterCapability
)
ManifestHandoffRecoveryCapabilityOutcomeObservation = (
    RunningManifestHandoffRecoveryCapability | ExecutedManifestHandoffRecoveryCapability
)
