"""Inert candidate graph with one child execution owner and no compatibility fallback."""

from dataclasses import dataclass, field

from liquent_platform.application.manifest_handoff_supervisor_child_process import (
    OneShotManifestHandoffSupervisorChildProcess,
)
from liquent_platform.application.manifest_handoff_supervisor_execution_reconciliation import (
    ReadOnlyManifestHandoffSupervisorExecutionReconciler,
)
from liquent_platform.application.manifest_handoff_supervisor_observation_parent import (
    ObservationOnlyManifestHandoffSupervisorPrepareCompletion,
    ObservationOnlyManifestHandoffSupervisorReleaseService,
)
from liquent_platform.application.manifest_handoff_supervisor_observation_terminal import (
    ObservationOnlyManifestHandoffSupervisorTerminalService,
)
from liquent_platform.application.manifest_handoff_supervisor_parent_launch import (
    CandidateObservationOnlyManifestHandoffSupervisorPrepareService,
    PersistentManifestHandoffSupervisorParentLaunchPrefix,
)
from liquent_platform.application.manifest_handoff_supervisor_wrapper_artifact_observer import (
    PersistentManifestHandoffSupervisorWrapperArtifactRecorder,
    ReadOnlyManifestHandoffSupervisorWrapperArtifactObserver,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_control_artifacts import (
    CanonicalManifestHandoffSupervisorControlArtifactCodec,
)
from liquent_platform.transport.manifest_handoff_supervisor_gate_wrapper import (
    FileManifestHandoffSupervisorGateWrapper,
)
from liquent_platform.transport.manifest_handoff_supervisor_launch_document import (
    CanonicalManifestHandoffSupervisorLaunchDocumentCodec,
)


@dataclass(frozen=True, slots=True)
class CandidateManifestHandoffSupervisorGraph:
    prepare: CandidateObservationOnlyManifestHandoffSupervisorPrepareService = field(
        repr=False
    )
    release: ObservationOnlyManifestHandoffSupervisorReleaseService = field(repr=False)
    child: OneShotManifestHandoffSupervisorChildProcess = field(repr=False)
    terminal: ObservationOnlyManifestHandoffSupervisorTerminalService = field(repr=False)
    reconciliation: ReadOnlyManifestHandoffSupervisorExecutionReconciler = field(
        repr=False
    )
    terminal_observation_complete: bool = field(default=True, init=False)
    production_ready: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.prepare) is CandidateObservationOnlyManifestHandoffSupervisorPrepareService,
            type(self.release) is ObservationOnlyManifestHandoffSupervisorReleaseService,
            type(self.child) is OneShotManifestHandoffSupervisorChildProcess,
            type(self.terminal) is ObservationOnlyManifestHandoffSupervisorTerminalService,
            type(self.reconciliation) is ReadOnlyManifestHandoffSupervisorExecutionReconciler,
            self.terminal_observation_complete is True,
            self.production_ready is False,
        )):
            raise ValueError("manifest handoff supervisor candidate graph is invalid")


def compose_candidate_manifest_handoff_supervisor_graph(
    *, journal, runtime_bindings, gate_bindings, supervisor_engine,
    control_artifacts, launch_documents, launch_loader, child_capability_executor,
    clock, monotonic, sleep, maximum_release_wait: float, poll_interval: float,
) -> CandidateManifestHandoffSupervisorGraph:
    """Construct an unselected graph without I/O, fallback, or terminal claims."""
    values = (
        journal, runtime_bindings, gate_bindings, supervisor_engine,
        control_artifacts, launch_documents, launch_loader, child_capability_executor,
    )
    if any(value is None for value in values):
        raise ManifestHandoffRegistryUnavailable
    try:
        codec = CanonicalManifestHandoffSupervisorControlArtifactCodec()
        child_wrapper = FileManifestHandoffSupervisorGateWrapper(
            codec=codec, publisher=control_artifacts, reader=control_artifacts
        )
        observer = ReadOnlyManifestHandoffSupervisorWrapperArtifactObserver(
            reader=control_artifacts, codec=codec
        )
        recorder = PersistentManifestHandoffSupervisorWrapperArtifactRecorder(
            observer=observer, control_artifacts=runtime_bindings
        )
        launch_codec = CanonicalManifestHandoffSupervisorLaunchDocumentCodec()
        launch = PersistentManifestHandoffSupervisorParentLaunchPrefix(
            journal=journal, runtime_bindings=runtime_bindings,
            gate_bindings=gate_bindings, engine=supervisor_engine,
            launch_documents=launch_documents,
            launch_document_codec=launch_codec,
        )
        completion = ObservationOnlyManifestHandoffSupervisorPrepareCompletion(
            journal=journal, runtime_bindings=runtime_bindings,
            gate_bindings=gate_bindings, engine=supervisor_engine,
            wrapper_artifact_recorder=recorder,
        )
        prepare = CandidateObservationOnlyManifestHandoffSupervisorPrepareService(
            launch_prefix=launch, prepare_completion=completion
        )
        release = ObservationOnlyManifestHandoffSupervisorReleaseService(
            journal=journal, runtime_bindings=runtime_bindings,
            control_artifacts=runtime_bindings, gate_bindings=gate_bindings,
            engine=supervisor_engine, codec=codec, publisher=control_artifacts,
            wrapper_artifact_recorder=recorder,
        )
        child = OneShotManifestHandoffSupervisorChildProcess(
            loader=launch_loader, gate_wrapper=child_wrapper,
            executor=child_capability_executor, clock=clock, monotonic=monotonic,
            sleep=sleep, maximum_release_wait=maximum_release_wait,
            poll_interval=poll_interval,
        )
        terminal = ObservationOnlyManifestHandoffSupervisorTerminalService(
            journal=journal, runtime_bindings=runtime_bindings,
            gate_bindings=gate_bindings, engine=supervisor_engine,
            wrapper_artifact_recorder=recorder,
        )
        return CandidateManifestHandoffSupervisorGraph(
            prepare, release, child, terminal,
            ReadOnlyManifestHandoffSupervisorExecutionReconciler(),
        )
    except ManifestHandoffRegistryUnavailable:
        raise
    except Exception:
        raise ManifestHandoffRegistryUnavailable from None
