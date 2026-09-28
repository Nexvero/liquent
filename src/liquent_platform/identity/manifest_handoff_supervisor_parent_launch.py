"""Closed result of the parent-owned registration and runtime launch prefix."""

from dataclasses import dataclass, field

from .manifest_handoff_supervisor_engine import (
    ManifestHandoffSupervisorEngineState,
    ObservedManifestHandoffSupervisorContainer,
)
from .manifest_handoff_supervisor_gate_wrapper import (
    StartManifestHandoffSupervisorGateWrapper,
)
from .manifest_handoff_supervisor_journal import (
    ManifestHandoffRecoveryJournalView,
    ManifestHandoffSupervisorJournalState,
    ManifestHandoffWriterJournalView,
)
from .manifest_handoff_supervisor_runtime import BoundManifestHandoffSupervisorRuntime


@dataclass(frozen=True, slots=True)
class LaunchedManifestHandoffSupervisorParentPrefix:
    journal: ManifestHandoffWriterJournalView | ManifestHandoffRecoveryJournalView = field(
        repr=False
    )
    runtime: BoundManifestHandoffSupervisorRuntime = field(repr=False)
    gate: StartManifestHandoffSupervisorGateWrapper = field(repr=False)
    observation: ObservedManifestHandoffSupervisorContainer = field(repr=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.journal) in (
                ManifestHandoffWriterJournalView, ManifestHandoffRecoveryJournalView
            ),
            self.journal.state in {
                ManifestHandoffSupervisorJournalState.LAUNCH_COMMITTED,
                ManifestHandoffSupervisorJournalState.PREPARED_GATED,
            },
            type(self.runtime) is BoundManifestHandoffSupervisorRuntime,
            type(self.gate) is StartManifestHandoffSupervisorGateWrapper,
            type(self.observation) is ObservedManifestHandoffSupervisorContainer,
            self.runtime.handle_id == self.gate.handle_id == self.journal.registration.handle_id,
            self.runtime.control_directory_id == self.gate.control_directory_id,
            self.observation.runtime_container_id == self.runtime.runtime_container_id,
            self.observation.creation_id == self.runtime.creation_id,
            self.observation.image_digest == self.runtime.image_digest,
            self.observation.profile is self.gate.profile,
            self.observation.state is ManifestHandoffSupervisorEngineState.RUNNING,
        )):
            raise ValueError("manifest handoff supervisor parent launch prefix is invalid")
