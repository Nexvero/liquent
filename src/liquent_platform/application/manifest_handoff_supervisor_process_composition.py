"""Process-owned, inert composition of the exclusive supervisor candidate."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
import time

from sqlalchemy import Engine

from liquent_platform.application.manifest_handoff_supervisor_candidate_composition import (
    CandidateManifestHandoffSupervisorGraph,
    compose_candidate_manifest_handoff_supervisor_graph,
)
from liquent_platform.application.health import Readiness
from liquent_platform.application.manifest_handoff_supervisor_child_capabilities import (
    LocalManifestHandoffSupervisorChildCapabilityExecutor,
)
from liquent_platform.capabilities.private_manifest_handoff import handoff_manifest
from liquent_platform.capabilities.private_manifest_handoff_reconcile import (
    reconcile_manifest_handoff,
)
from liquent_platform.configuration import PlatformSettings
from liquent_platform.identity.manifest_handoff_supervisor_correlation import (
    ManifestHandoffSupervisorBackendInstanceId,
)
from liquent_platform.identity.manifest_handoff_supervisor_launch_identity import (
    ManifestHandoffSupervisorLaunchIdentityPolicy,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.persistence.manifest_handoff_supervisor_control_directories import (
    DatabaseManifestHandoffSupervisorControlDirectories,
)
from liquent_platform.persistence.manifest_handoff_supervisor_gate_bindings import (
    DatabaseManifestHandoffSupervisorGateBindings,
)
from liquent_platform.persistence.manifest_handoff_supervisor_journal import (
    DatabaseManifestHandoffSupervisorJournal,
)
from liquent_platform.persistence.manifest_handoff_supervisor_runtime import (
    DatabaseManifestHandoffSupervisorRuntime,
)
from liquent_platform.transport.local_docker_engine_http_client import (
    LocalDockerEngineHttpClient,
)
from liquent_platform.transport.manifest_handoff_supervisor_control_artifacts import (
    AtomicLocalManifestHandoffSupervisorControlArtifacts,
    CanonicalManifestHandoffSupervisorControlArtifactCodec,
)
from liquent_platform.transport.manifest_handoff_supervisor_control_directories import (
    SafeLocalManifestHandoffSupervisorControlDirectories,
)
from liquent_platform.transport.manifest_handoff_supervisor_launch_document import (
    CanonicalManifestHandoffSupervisorLaunchDocumentCodec,
)
from liquent_platform.transport.manifest_handoff_supervisor_launch_file import (
    AtomicLocalManifestHandoffSupervisorLaunchDocuments,
)
from liquent_platform.transport.manifest_handoff_supervisor_launch_loader import (
    ReadOnlyManifestHandoffSupervisorLaunchDocumentLoader,
)


_WRITER_COMMAND = ("liquent-supervisor-writer-wrapper",)
_RECOVERY_COMMAND = ("liquent-supervisor-recovery-wrapper",)
_CHILD_LAUNCH_ROOT = Path("/run/liquent/launch")
_CHILD_SOURCE_ROOT = Path("/run/liquent/source")
_CHILD_TARGET_ROOT = Path("/run/liquent/target")
_MAXIMUM_RELEASE_WAIT = 300.0
_POLL_INTERVAL = 0.25


class ManifestHandoffSupervisorCandidateProcess:
    """Own one candidate graph and exactly its local Docker client."""

    __slots__ = ("_client", "_closed", "_graph")

    def __init__(self, graph: CandidateManifestHandoffSupervisorGraph, client) -> None:
        if (
            type(graph) is not CandidateManifestHandoffSupervisorGraph
            or client is None
            or not callable(getattr(client, "close", None))
        ):
            raise ManifestHandoffRegistryUnavailable
        self._graph = graph
        self._client = client
        self._closed = False

    def __repr__(self) -> str:
        return "ManifestHandoffSupervisorCandidateProcess()"

    @property
    def graph(self) -> CandidateManifestHandoffSupervisorGraph:
        return self._graph

    @property
    def production_ready(self) -> bool:
        return False

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._client.close()
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None


class ManifestHandoffSupervisorCandidateReadinessProbe:
    """Expose only the candidate's closed production-readiness statement."""

    __slots__ = ("_process",)

    def __init__(self, process: ManifestHandoffSupervisorCandidateProcess) -> None:
        if type(process) is not ManifestHandoffSupervisorCandidateProcess:
            raise ManifestHandoffRegistryUnavailable
        self._process = process

    def __repr__(self) -> str:
        return "ManifestHandoffSupervisorCandidateReadinessProbe()"

    @property
    def process(self) -> ManifestHandoffSupervisorCandidateProcess:
        return self._process

    def check(self) -> Readiness:
        try:
            if self._process.production_ready is True:
                return Readiness(True, "ready")
            return Readiness(False, "manifest_handoff_supervisor_not_ready")
        except Exception:
            return Readiness(False, "manifest_handoff_supervisor_unavailable")


def compose_manifest_handoff_supervisor_candidate_process(
    *,
    settings: PlatformSettings,
    database_engine: Engine,
    backend_instance_id: ManifestHandoffSupervisorBackendInstanceId,
    clock: Callable[[], datetime] | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> ManifestHandoffSupervisorCandidateProcess:
    """Build the complete unselected process graph without operational I/O."""
    if (
        type(settings) is not PlatformSettings
        or not settings.manifest_handoff_supervisor_enabled
        or not isinstance(database_engine, Engine)
        or type(backend_instance_id) is not ManifestHandoffSupervisorBackendInstanceId
        or (clock is not None and not callable(clock))
        or not callable(monotonic)
        or not callable(sleep)
    ):
        raise ManifestHandoffRegistryUnavailable
    client = None
    try:
        current_clock = clock or (lambda: datetime.now(timezone.utc))
        identity = _identity_policy(settings)
        registry = DatabaseManifestHandoffSupervisorControlDirectories(
            database_engine, clock=current_clock
        )
        directories = SafeLocalManifestHandoffSupervisorControlDirectories(
            _required_path(settings.manifest_handoff_supervisor_control_root),
            lookup=registry.resolve_control_directory,
        )
        codec = CanonicalManifestHandoffSupervisorControlArtifactCodec()
        artifacts = AtomicLocalManifestHandoffSupervisorControlArtifacts(
            _required_path(settings.manifest_handoff_supervisor_control_root),
            resolve_directory=directories.resolve_active,
            codec=codec,
        )
        launch_documents = AtomicLocalManifestHandoffSupervisorLaunchDocuments(
            _required_path(settings.manifest_handoff_supervisor_control_root),
            resolve_directory=directories.resolve_active,
            codec=CanonicalManifestHandoffSupervisorLaunchDocumentCodec(),
            identity_policy=identity,
        )
        client = LocalDockerEngineHttpClient(
            _required_path(settings.manifest_handoff_supervisor_docker_socket),
            control_directory_resolver=directories.resolve_active,
            writer_command=_WRITER_COMMAND,
            recovery_command=_RECOVERY_COMMAND,
            identity_policy=identity,
        )
        journal = DatabaseManifestHandoffSupervisorJournal(
            database_engine, backend_instance_id=backend_instance_id,
            clock=current_clock,
        )
        runtime = DatabaseManifestHandoffSupervisorRuntime(
            database_engine, clock=current_clock
        )
        gates = DatabaseManifestHandoffSupervisorGateBindings(
            database_engine, clock=current_clock
        )
        launch_loader = ReadOnlyManifestHandoffSupervisorLaunchDocumentLoader(
            _CHILD_LAUNCH_ROOT,
            codec=CanonicalManifestHandoffSupervisorLaunchDocumentCodec(),
            identity_policy=identity,
        )
        child_executor = LocalManifestHandoffSupervisorChildCapabilityExecutor(
            source_root=_CHILD_SOURCE_ROOT,
            target_root=_CHILD_TARGET_ROOT,
            writer=handoff_manifest,
            reconciler=reconcile_manifest_handoff,
            clock=current_clock,
        )
        graph = compose_candidate_manifest_handoff_supervisor_graph(
            journal=journal,
            runtime_bindings=runtime,
            gate_bindings=gates,
            supervisor_engine=client,
            control_artifacts=artifacts,
            launch_documents=launch_documents,
            launch_loader=launch_loader,
            child_capability_executor=child_executor,
            clock=current_clock,
            monotonic=monotonic,
            sleep=sleep,
            maximum_release_wait=_MAXIMUM_RELEASE_WAIT,
            poll_interval=_POLL_INTERVAL,
        )
        return ManifestHandoffSupervisorCandidateProcess(graph, client)
    except ManifestHandoffRegistryUnavailable:
        _close_after_failure(client)
        raise
    except Exception:
        _close_after_failure(client)
        raise ManifestHandoffRegistryUnavailable from None


def _identity_policy(settings: PlatformSettings):
    return ManifestHandoffSupervisorLaunchIdentityPolicy(
        settings.manifest_handoff_supervisor_host_owner_uid,
        settings.manifest_handoff_supervisor_reader_gid,
        settings.manifest_handoff_supervisor_wrapper_uid,
        settings.manifest_handoff_supervisor_wrapper_gid,
    )


def _required_path(value: Path | None) -> Path:
    if not isinstance(value, Path):
        raise ManifestHandoffRegistryUnavailable
    return value


def _close_after_failure(client) -> None:
    if client is None:
        return
    try:
        client.close()
    except Exception:
        pass
