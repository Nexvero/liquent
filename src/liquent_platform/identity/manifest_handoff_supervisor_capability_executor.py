"""Closed execution requests admitted only by a released wrapper gate."""

from dataclasses import dataclass, field

from .manifest_handoff_supervisor import (
    CompletedManifestHandoffRecoveryProcess,
    CompletedManifestHandoffWriterProcess,
    ManifestHandoffRecoverySupervisorRequest,
    ManifestHandoffWriterSupervisorRequest,
    PreparedManifestHandoffRecoveryProcess,
    PreparedManifestHandoffWriterProcess,
)
from .manifest_handoff_supervisor_engine import ManifestHandoffSupervisorEngineProfile
from .manifest_handoff_supervisor_gate_wrapper import ReleasedManifestHandoffSupervisorGateWrapper


@dataclass(frozen=True, slots=True)
class ExecuteManifestHandoffWriterCapability:
    gate: ReleasedManifestHandoffSupervisorGateWrapper = field(repr=False)
    prepared: PreparedManifestHandoffWriterProcess = field(repr=False)
    request: ManifestHandoffWriterSupervisorRequest = field(repr=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.gate) is ReleasedManifestHandoffSupervisorGateWrapper,
            type(self.prepared) is PreparedManifestHandoffWriterProcess,
            type(self.request) is ManifestHandoffWriterSupervisorRequest,
            self.gate.token.ready.binding.profile is ManifestHandoffSupervisorEngineProfile.WRITER,
            self.gate.token.ready.binding.handle_id == self.prepared.handle_id,
            self.prepared.claim_id == self.request.claim_id,
            self.prepared.owner_id == self.request.owner_id,
        )):
            raise ValueError("manifest handoff writer capability execution is invalid")


@dataclass(frozen=True, slots=True)
class ExecuteManifestHandoffRecoveryCapability:
    gate: ReleasedManifestHandoffSupervisorGateWrapper = field(repr=False)
    prepared: PreparedManifestHandoffRecoveryProcess = field(repr=False)
    request: ManifestHandoffRecoverySupervisorRequest = field(repr=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.gate) is ReleasedManifestHandoffSupervisorGateWrapper,
            type(self.prepared) is PreparedManifestHandoffRecoveryProcess,
            type(self.request) is ManifestHandoffRecoverySupervisorRequest,
            self.gate.token.ready.binding.profile is ManifestHandoffSupervisorEngineProfile.RECOVERY,
            self.gate.token.ready.binding.handle_id == self.prepared.handle_id,
            self.prepared.claim_id == self.request.claim_id,
            self.prepared.owner_id == self.request.owner_id,
        )):
            raise ValueError("manifest handoff recovery capability execution is invalid")


@dataclass(frozen=True, slots=True)
class ExecutedManifestHandoffWriterCapability:
    execution: ExecuteManifestHandoffWriterCapability = field(repr=False)
    outcome: CompletedManifestHandoffWriterProcess = field(repr=False)

    def __post_init__(self) -> None:
        if (type(self.execution) is not ExecuteManifestHandoffWriterCapability
                or type(self.outcome) is not CompletedManifestHandoffWriterProcess
                or self.outcome.handle_id != self.execution.prepared.handle_id
                or self.outcome.claim_id != self.execution.prepared.claim_id
                or self.outcome.owner_id != self.execution.prepared.owner_id):
            raise ValueError("manifest handoff writer capability outcome is invalid")


@dataclass(frozen=True, slots=True)
class ExecutedManifestHandoffRecoveryCapability:
    execution: ExecuteManifestHandoffRecoveryCapability = field(repr=False)
    outcome: CompletedManifestHandoffRecoveryProcess = field(repr=False)

    def __post_init__(self) -> None:
        if (type(self.execution) is not ExecuteManifestHandoffRecoveryCapability
                or type(self.outcome) is not CompletedManifestHandoffRecoveryProcess
                or self.outcome.handle_id != self.execution.prepared.handle_id
                or self.outcome.claim_id != self.execution.prepared.claim_id
                or self.outcome.owner_id != self.execution.prepared.owner_id):
            raise ValueError("manifest handoff recovery capability outcome is invalid")
