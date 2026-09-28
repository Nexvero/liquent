"""Explicit composition of the persistent manifest-handoff supervisor service."""

from collections.abc import Callable
from datetime import datetime

from sqlalchemy import Engine

from liquent_platform.application.manifest_handoff_supervisor_inspect_service import (
    PersistentManifestHandoffSupervisorInspectService,
)
from liquent_platform.application.manifest_handoff_supervisor_prepare_service import (
    PersistentManifestHandoffSupervisorPrepareService,
)
from liquent_platform.application.manifest_handoff_supervisor_release_service import (
    PersistentManifestHandoffSupervisorReleaseService,
)
from liquent_platform.application.manifest_handoff_supervisor_service import (
    PersistentManifestHandoffSupervisorService,
)
from liquent_platform.application.manifest_handoff_supervisor_terminal_service import (
    PersistentManifestHandoffSupervisorTerminalService,
)
from liquent_platform.application.manifest_handoff_supervisor_terminate_service import (
    PersistentManifestHandoffSupervisorTerminateService,
)
from liquent_platform.identity.manifest_handoff_supervisor_correlation import (
    ManifestHandoffSupervisorBackendInstanceId,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.persistence.manifest_handoff_supervisor_gate_bindings import (
    DatabaseManifestHandoffSupervisorGateBindings,
)
from liquent_platform.persistence.manifest_handoff_supervisor_journal import (
    DatabaseManifestHandoffSupervisorJournal,
)
from liquent_platform.persistence.manifest_handoff_supervisor_runtime import (
    DatabaseManifestHandoffSupervisorRuntime,
)
from liquent_platform.transport.manifest_handoff_supervisor_control_artifacts import (
    CanonicalManifestHandoffSupervisorControlArtifactCodec,
)
from liquent_platform.transport.manifest_handoff_supervisor_gate_wrapper import (
    FileManifestHandoffSupervisorGateWrapper,
)


def compose_persistent_manifest_handoff_supervisor_service(
    *,
    database_engine: Engine,
    backend_instance_id: ManifestHandoffSupervisorBackendInstanceId,
    supervisor_engine,
    control_artifacts,
    capability_executor,
    capability_outcomes,
    clock: Callable[[], datetime] | None = None,
) -> PersistentManifestHandoffSupervisorService:
    """Build one inert-until-called service graph from controlled dependencies."""
    if (not isinstance(database_engine, Engine)
            or type(backend_instance_id) is not ManifestHandoffSupervisorBackendInstanceId
            or any(value is None for value in (
                supervisor_engine, control_artifacts, capability_executor,
                capability_outcomes,
            ))
            or (clock is not None and not callable(clock))):
        raise ManifestHandoffRegistryUnavailable
    try:
        codec = CanonicalManifestHandoffSupervisorControlArtifactCodec()
        wrapper = FileManifestHandoffSupervisorGateWrapper(
            codec=codec, publisher=control_artifacts, reader=control_artifacts)
        journal = DatabaseManifestHandoffSupervisorJournal(
            database_engine, backend_instance_id=backend_instance_id, clock=clock)
        runtime = DatabaseManifestHandoffSupervisorRuntime(database_engine, clock=clock)
        gates = DatabaseManifestHandoffSupervisorGateBindings(database_engine, clock=clock)

        prepare = PersistentManifestHandoffSupervisorPrepareService(
            journal=journal, runtime_bindings=runtime, control_artifacts=runtime,
            gate_bindings=gates, engine=supervisor_engine, gate_wrapper=wrapper)
        release = PersistentManifestHandoffSupervisorReleaseService(
            journal=journal, runtime_bindings=runtime, control_artifacts=runtime,
            gate_bindings=gates, engine=supervisor_engine, gate_wrapper=wrapper,
            codec=codec, publisher=control_artifacts, executor=capability_executor)
        inspect = PersistentManifestHandoffSupervisorInspectService(
            journal=journal, runtime_bindings=runtime, control_artifacts=runtime,
            gate_bindings=gates, engine=supervisor_engine,
            reader=control_artifacts, codec=codec)
        terminal = PersistentManifestHandoffSupervisorTerminalService(
            journal=journal, runtime_bindings=runtime, control_artifacts=runtime,
            gate_bindings=gates, engine=supervisor_engine, gate_wrapper=wrapper,
            outcomes=capability_outcomes, inspect_service=inspect,
            reader=control_artifacts, codec=codec)
        terminate = PersistentManifestHandoffSupervisorTerminateService(
            journal=journal, runtime_bindings=runtime, control_artifacts=runtime,
            gate_bindings=gates, engine=supervisor_engine, gate_wrapper=wrapper,
            outcomes=capability_outcomes, inspect_service=inspect,
            reader=control_artifacts, codec=codec, clock=clock)
        return PersistentManifestHandoffSupervisorService(
            prepare=prepare, release=release, inspect=inspect,
            terminate=terminate, terminal=terminal)
    except ManifestHandoffRegistryUnavailable:
        raise
    except Exception:
        raise ManifestHandoffRegistryUnavailable from None
