"""Persistent Docker-runtime and private control-artifact correlations."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from sqlalchemy import Engine, text

from liquent_platform.identity.manifest_handoff_supervisor import ManifestHandoffSupervisorHandleId
from liquent_platform.identity.manifest_handoff_supervisor_correlation import (
    ManifestHandoffSupervisorReleaseId, ManifestHandoffSupervisorTerminalObservationId,
)
from liquent_platform.identity.manifest_handoff_supervisor_journal import ManifestHandoffSupervisorGatedObservationId
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    BindManifestHandoffSupervisorRuntime, BoundManifestHandoffSupervisorRuntime,
    ManifestHandoffSupervisorControlArtifactFacts, ManifestHandoffSupervisorControlArtifactId,
    ManifestHandoffSupervisorControlArtifactRole, ManifestHandoffSupervisorControlDirectoryId,
    ManifestHandoffSupervisorCreationId, ManifestHandoffSupervisorImageDigest,
    ManifestHandoffSupervisorRuntimeConflict, ManifestHandoffSupervisorRuntimeContainerId,
    RecordManifestHandoffSupervisorReadyArtifact,
    RecordManifestHandoffSupervisorReleaseConsumedArtifact,
    RecordManifestHandoffSupervisorReleaseTokenArtifact,
    RecordManifestHandoffSupervisorTerminalEnvelopeArtifact,
    RecordedManifestHandoffSupervisorControlArtifact,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


_LOCK = text(
    "LOCK TABLE manifest_handoff_supervisor_journal_jobs,"
    " manifest_handoff_supervisor_journal_transitions,"
    " manifest_handoff_supervisor_runtime_bindings,"
    " manifest_handoff_supervisor_control_artifacts IN SHARE ROW EXCLUSIVE MODE"
)
_JOB = text("SELECT handle_id FROM manifest_handoff_supervisor_journal_jobs WHERE handle_id=:handle")
_RUNTIME_BY_HANDLE = text("SELECT * FROM manifest_handoff_supervisor_runtime_bindings WHERE handle_id=:handle")
_RUNTIME_BY_CREATION = text("SELECT * FROM manifest_handoff_supervisor_runtime_bindings WHERE creation_id=:creation")
_RUNTIME_OCCUPIED = text(
    "SELECT handle_id FROM manifest_handoff_supervisor_runtime_bindings"
    " WHERE runtime_container_id=:container OR control_directory_id=:control"
)
_ARTIFACT_BY_ID = text("SELECT * FROM manifest_handoff_supervisor_control_artifacts WHERE artifact_id=:artifact")
_ARTIFACT_BY_ROLE = text(
    "SELECT * FROM manifest_handoff_supervisor_control_artifacts"
    " WHERE handle_id=:handle AND role=:role"
)
_TRANSITION = text(
    "SELECT transition_id FROM manifest_handoff_supervisor_journal_transitions"
    " WHERE handle_id=:handle AND kind=:kind AND transition_id=:correlation"
)
_TRANSITION_KIND_EXISTS = text(
    "SELECT transition_id FROM manifest_handoff_supervisor_journal_transitions"
    " WHERE handle_id=:handle AND kind=:kind"
)


def _encode(value: object) -> bytes:
    raw = value.value if hasattr(value, "value") else value
    if type(raw) is not str or not raw:
        raise ManifestHandoffRegistryUnavailable
    return raw.encode("utf-8")


def _decode(value: object) -> str:
    try:
        if not isinstance(value, (bytes, bytearray, memoryview)) or not value:
            raise ManifestHandoffRegistryUnavailable
        result = bytes(value).decode("utf-8")
    except UnicodeError:
        raise ManifestHandoffRegistryUnavailable from None
    if not result:
        raise ManifestHandoffRegistryUnavailable
    return result


def _utc(value: object) -> datetime:
    if type(value) is str:
        try: value = datetime.fromisoformat(value)
        except ValueError: raise ManifestHandoffRegistryUnavailable from None
    if type(value) is not datetime:
        raise ManifestHandoffRegistryUnavailable
    value = value.replace(tzinfo=value.tzinfo or timezone.utc)
    if value.utcoffset() != timedelta(0):
        raise ManifestHandoffRegistryUnavailable
    return value


class DatabaseManifestHandoffSupervisorRuntime:
    """Persist correlations only; never access Docker or control files."""

    __slots__ = ("_engine", "_clock")

    def __init__(self, engine: Engine, *, clock: Callable[[], datetime] | None = None) -> None:
        self._engine = engine
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return "DatabaseManifestHandoffSupervisorRuntime()"

    def bind_runtime(self, request):
        if type(request) is not BindManifestHandoffSupervisorRuntime:
            raise ManifestHandoffRegistryUnavailable
        values = {"handle": _encode(request.handle_id), "creation": _encode(request.creation_id),
            "container": _encode(request.runtime_container_id), "control": _encode(request.control_directory_id),
            "image": request.image_digest.value}
        def action(transaction):
            rows = transaction.execute(_RUNTIME_BY_HANDLE, values).all()
            if rows:
                if len(rows) != 1 or not self._same_runtime(rows[0], values):
                    return ManifestHandoffSupervisorRuntimeConflict()
                return self._runtime(rows[0])
            creation = transaction.execute(_RUNTIME_BY_CREATION, values).all()
            if creation or transaction.execute(_RUNTIME_OCCUPIED, values).first() is not None:
                return ManifestHandoffSupervisorRuntimeConflict()
            if transaction.execute(_JOB, values).first() is None:
                return None
            now = _utc(self._clock())
            transaction.execute(text(
                "INSERT INTO manifest_handoff_supervisor_runtime_bindings"
                " (handle_id,creation_id,runtime_container_id,control_directory_id,image_digest,bound_at)"
                " VALUES (:handle,:creation,:container,:control,:image,:now)"
            ), {**values, "now": now})
            return BoundManifestHandoffSupervisorRuntime(request.handle_id, request.creation_id,
                request.runtime_container_id, request.control_directory_id, request.image_digest, now)
        return self._write(action)

    @staticmethod
    def _same_runtime(row, values):
        return row.creation_id == values["creation"] and row.runtime_container_id == values["container"] and row.control_directory_id == values["control"] and row.image_digest == values["image"]

    def resolve_runtime(self, handle_id):
        if type(handle_id) is not ManifestHandoffSupervisorHandleId: raise ManifestHandoffRegistryUnavailable
        return self._resolve_runtime(_RUNTIME_BY_HANDLE, {"handle": _encode(handle_id)})

    def resolve_creation(self, creation_id):
        if type(creation_id) is not ManifestHandoffSupervisorCreationId: raise ManifestHandoffRegistryUnavailable
        return self._resolve_runtime(_RUNTIME_BY_CREATION, {"creation": _encode(creation_id)})

    def _resolve_runtime(self, query, values):
        def action(connection):
            rows = connection.execute(query, values).all()
            if not rows: return None
            if len(rows) != 1: raise ManifestHandoffRegistryUnavailable
            return self._runtime(rows[0])
        return self._read(action)

    @staticmethod
    def _runtime(row):
        return BoundManifestHandoffSupervisorRuntime(
            ManifestHandoffSupervisorHandleId(_decode(row.handle_id)),
            ManifestHandoffSupervisorCreationId(_decode(row.creation_id)),
            ManifestHandoffSupervisorRuntimeContainerId(_decode(row.runtime_container_id)),
            ManifestHandoffSupervisorControlDirectoryId(_decode(row.control_directory_id)),
            ManifestHandoffSupervisorImageDigest(row.image_digest), _utc(row.bound_at))

    def record_ready(self, request):
        return self._artifact(request, RecordManifestHandoffSupervisorReadyArtifact, ManifestHandoffSupervisorControlArtifactRole.WRAPPER_READY, "launch_committed", correlate_transition=False)

    def record_release_token(self, request):
        return self._artifact(request, RecordManifestHandoffSupervisorReleaseTokenArtifact, ManifestHandoffSupervisorControlArtifactRole.RELEASE_TOKEN, "release_committed")

    def record_release_consumed(self, request):
        return self._artifact(request, RecordManifestHandoffSupervisorReleaseConsumedArtifact, ManifestHandoffSupervisorControlArtifactRole.RELEASE_CONSUMED, "release_committed", require_token=True)

    def record_terminal_envelope(self, request):
        return self._artifact(request, RecordManifestHandoffSupervisorTerminalEnvelopeArtifact, ManifestHandoffSupervisorControlArtifactRole.TERMINAL_ENVELOPE, None)

    def _artifact(self, request, request_type, role, prerequisite, require_token=False, correlate_transition=True):
        if type(request) is not request_type: raise ManifestHandoffRegistryUnavailable
        values = {"artifact": _encode(request.artifact_id), "handle": _encode(request.handle_id),
            "role": role.value, "correlation": _encode(request.correlation_id),
            "digest": request.facts.sha256, "count": request.facts.byte_count}
        def action(transaction):
            rows = transaction.execute(_ARTIFACT_BY_ID, values).all()
            if rows:
                if len(rows) != 1 or not self._same_artifact(rows[0], values):
                    return ManifestHandoffSupervisorRuntimeConflict()
                return self._artifact_record(rows[0])
            if transaction.execute(_ARTIFACT_BY_ROLE, values).first() is not None:
                return ManifestHandoffSupervisorRuntimeConflict()
            if transaction.execute(_RUNTIME_BY_HANDLE, values).first() is None:
                return None
            if prerequisite is not None:
                values["kind"] = prerequisite
                transition_query = _TRANSITION if correlate_transition else _TRANSITION_KIND_EXISTS
                if transaction.execute(transition_query, values).first() is None:
                    return None
            if require_token:
                token_values = {**values, "role": ManifestHandoffSupervisorControlArtifactRole.RELEASE_TOKEN.value}
                token = transaction.execute(_ARTIFACT_BY_ROLE, token_values).first()
                if token is None or token.correlation_id != values["correlation"]:
                    return None
            now = _utc(self._clock())
            transaction.execute(text(
                "INSERT INTO manifest_handoff_supervisor_control_artifacts"
                " (artifact_id,handle_id,role,correlation_id,artifact_sha256,byte_count,published_at)"
                " VALUES (:artifact,:handle,:role,:correlation,:digest,:count,:now)"
            ), {**values, "role": role.value, "now": now})
            return RecordedManifestHandoffSupervisorControlArtifact(request.artifact_id, request.handle_id,
                role, request.correlation_id, request.facts, now)
        return self._write(action)

    @staticmethod
    def _same_artifact(row, values):
        return row.handle_id == values["handle"] and row.role == values["role"] and row.correlation_id == values["correlation"] and row.artifact_sha256 == values["digest"] and row.byte_count == values["count"]

    def resolve_artifact(self, artifact_id):
        if type(artifact_id) is not ManifestHandoffSupervisorControlArtifactId: raise ManifestHandoffRegistryUnavailable
        return self._resolve_artifact(_ARTIFACT_BY_ID, {"artifact": _encode(artifact_id)})

    def resolve_artifact_role(self, handle_id, role):
        if type(handle_id) is not ManifestHandoffSupervisorHandleId or type(role) is not ManifestHandoffSupervisorControlArtifactRole: raise ManifestHandoffRegistryUnavailable
        return self._resolve_artifact(_ARTIFACT_BY_ROLE, {"handle": _encode(handle_id), "role": role.value})

    def _resolve_artifact(self, query, values):
        def action(connection):
            rows = connection.execute(query, values).all()
            if not rows: return None
            if len(rows) != 1: raise ManifestHandoffRegistryUnavailable
            return self._artifact_record(rows[0])
        return self._read(action)

    @staticmethod
    def _artifact_record(row):
        role = ManifestHandoffSupervisorControlArtifactRole(row.role)
        correlation_type = {ManifestHandoffSupervisorControlArtifactRole.WRAPPER_READY: ManifestHandoffSupervisorGatedObservationId,
            ManifestHandoffSupervisorControlArtifactRole.RELEASE_TOKEN: ManifestHandoffSupervisorReleaseId,
            ManifestHandoffSupervisorControlArtifactRole.RELEASE_CONSUMED: ManifestHandoffSupervisorReleaseId,
            ManifestHandoffSupervisorControlArtifactRole.TERMINAL_ENVELOPE: ManifestHandoffSupervisorTerminalObservationId}[role]
        return RecordedManifestHandoffSupervisorControlArtifact(
            ManifestHandoffSupervisorControlArtifactId(_decode(row.artifact_id)),
            ManifestHandoffSupervisorHandleId(_decode(row.handle_id)), role,
            correlation_type(_decode(row.correlation_id)),
            ManifestHandoffSupervisorControlArtifactFacts(row.artifact_sha256, row.byte_count),
            _utc(row.published_at))

    def _write(self, action):
        try:
            with self._engine.begin() as connection:
                self._dialect(connection, True); return action(connection)
        except ManifestHandoffRegistryUnavailable as error:
            if error.__cause__ is None and error.__context__ is None: raise
        except Exception: pass
        raise ManifestHandoffRegistryUnavailable

    def _read(self, action):
        try:
            with self._engine.connect() as connection:
                self._dialect(connection, False); return action(connection)
        except ManifestHandoffRegistryUnavailable as error:
            if error.__cause__ is None and error.__context__ is None: raise
        except Exception: pass
        raise ManifestHandoffRegistryUnavailable

    @staticmethod
    def _dialect(connection, lock):
        if connection.dialect.name == "postgresql":
            if lock: connection.execute(_LOCK)
        elif connection.dialect.name != "sqlite": raise ManifestHandoffRegistryUnavailable
