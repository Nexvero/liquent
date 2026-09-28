"""Persistent immutable supervisor gate bindings and reservations."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from sqlalchemy import Engine, text

from liquent_platform.identity.manifest_handoff_supervisor import ManifestHandoffSupervisorHandleId
from liquent_platform.identity.manifest_handoff_supervisor_correlation import ManifestHandoffSupervisorTerminalObservationId
from liquent_platform.identity.manifest_handoff_supervisor_engine import ManifestHandoffSupervisorEngineProfile
from liquent_platform.identity.manifest_handoff_supervisor_gate_wrapper import StartManifestHandoffSupervisorGateWrapper
from liquent_platform.identity.manifest_handoff_supervisor_journal import ManifestHandoffSupervisorGatedObservationId
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlArtifactId,
    ManifestHandoffSupervisorControlDirectoryId,
)
from liquent_platform.identity.manifest_handoff_supervisor_service import ManifestHandoffSupervisorGateBindingConflict
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


_LOCK = text(
    "LOCK TABLE manifest_handoff_supervisor_journal_jobs,"
    " manifest_handoff_supervisor_runtime_bindings,"
    " manifest_handoff_supervisor_gate_bindings,"
    " manifest_handoff_supervisor_gate_artifact_reservations"
    " IN SHARE ROW EXCLUSIVE MODE"
)
_BINDING_BY_HANDLE = text(
    "SELECT binding.handle_id,binding.profile,binding.gated_observation_id,"
    " binding.terminal_observation_id,binding.bound_at,runtime.control_directory_id,"
    " job.capability FROM manifest_handoff_supervisor_gate_bindings binding"
    " JOIN manifest_handoff_supervisor_runtime_bindings runtime"
    " ON runtime.handle_id=binding.handle_id"
    " JOIN manifest_handoff_supervisor_journal_jobs job"
    " ON job.handle_id=binding.handle_id WHERE binding.handle_id=:handle"
)
_BINDING_BY_ARTIFACT = text(
    "SELECT binding.handle_id,binding.profile,binding.gated_observation_id,"
    " binding.terminal_observation_id,binding.bound_at,runtime.control_directory_id,"
    " job.capability FROM manifest_handoff_supervisor_gate_artifact_reservations artifact"
    " JOIN manifest_handoff_supervisor_gate_bindings binding"
    " ON binding.handle_id=artifact.handle_id"
    " JOIN manifest_handoff_supervisor_runtime_bindings runtime"
    " ON runtime.handle_id=binding.handle_id"
    " JOIN manifest_handoff_supervisor_journal_jobs job"
    " ON job.handle_id=binding.handle_id WHERE artifact.artifact_id=:artifact"
)
_PREREQUISITE = text(
    "SELECT runtime.control_directory_id,job.capability"
    " FROM manifest_handoff_supervisor_runtime_bindings runtime"
    " JOIN manifest_handoff_supervisor_journal_jobs job ON job.handle_id=runtime.handle_id"
    " WHERE runtime.handle_id=:handle"
)
_RESERVATIONS = text(
    "SELECT artifact_id,role FROM manifest_handoff_supervisor_gate_artifact_reservations"
    " WHERE handle_id=:handle"
)
_OCCUPIED_OBSERVATION = text(
    "SELECT handle_id FROM manifest_handoff_supervisor_gate_bindings"
    " WHERE gated_observation_id=:gated OR terminal_observation_id=:terminal"
)
_OCCUPIED_ARTIFACT = text(
    "SELECT artifact_id FROM manifest_handoff_supervisor_gate_artifact_reservations"
    " WHERE artifact_id IN (:ready,:consumed,:terminal_artifact)"
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


class DatabaseManifestHandoffSupervisorGateBindings:
    __slots__ = ("_engine", "_clock")

    def __init__(self, engine: Engine, *, clock: Callable[[], datetime] | None = None) -> None:
        self._engine = engine
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return "DatabaseManifestHandoffSupervisorGateBindings()"

    def bind_gate(self, binding):
        if type(binding) is not StartManifestHandoffSupervisorGateWrapper:
            raise ManifestHandoffRegistryUnavailable
        values = self._values(binding)
        def action(transaction):
            existing = transaction.execute(_BINDING_BY_HANDLE, values).all()
            if existing:
                if len(existing) != 1:
                    raise ManifestHandoffRegistryUnavailable
                reconstructed = self._binding(transaction, existing[0])
                return reconstructed if reconstructed == binding else ManifestHandoffSupervisorGateBindingConflict()
            prerequisites = transaction.execute(_PREREQUISITE, values).all()
            if not prerequisites:
                return None
            if len(prerequisites) != 1:
                raise ManifestHandoffRegistryUnavailable
            prerequisite = prerequisites[0]
            if (prerequisite.control_directory_id != values["control"]
                    or prerequisite.capability != values["profile"]):
                return None
            if (transaction.execute(_OCCUPIED_OBSERVATION, values).first() is not None
                    or transaction.execute(_OCCUPIED_ARTIFACT, values).first() is not None):
                return ManifestHandoffSupervisorGateBindingConflict()
            now = _utc(self._clock())
            transaction.execute(text(
                "INSERT INTO manifest_handoff_supervisor_gate_bindings"
                " (handle_id,profile,gated_observation_id,terminal_observation_id,bound_at)"
                " VALUES (:handle,:profile,:gated,:terminal,:now)"
            ), {**values, "now": now})
            for role, key in (("wrapper_ready", "ready"),
                    ("release_consumed", "consumed"),
                    ("terminal_envelope", "terminal_artifact")):
                transaction.execute(text(
                    "INSERT INTO manifest_handoff_supervisor_gate_artifact_reservations"
                    " (artifact_id,handle_id,role) VALUES (:artifact,:handle,:role)"
                ), {"artifact": values[key], "handle": values["handle"], "role": role})
            return binding
        return self._write(action)

    def resolve_gate(self, handle_id):
        if type(handle_id) is not ManifestHandoffSupervisorHandleId:
            raise ManifestHandoffRegistryUnavailable
        return self._resolve(_BINDING_BY_HANDLE, {"handle": _encode(handle_id)})

    def resolve_gate_artifact(self, artifact_id):
        if type(artifact_id) is not ManifestHandoffSupervisorControlArtifactId:
            raise ManifestHandoffRegistryUnavailable
        return self._resolve(_BINDING_BY_ARTIFACT, {"artifact": _encode(artifact_id)})

    def _resolve(self, query, values):
        def action(connection):
            rows = connection.execute(query, values).all()
            if not rows: return None
            if len(rows) != 1: raise ManifestHandoffRegistryUnavailable
            return self._binding(connection, rows[0])
        return self._read(action)

    @staticmethod
    def _values(binding):
        return {"handle": _encode(binding.handle_id),
            "profile": binding.profile.value,
            "control": _encode(binding.control_directory_id),
            "gated": _encode(binding.gated_observation_id),
            "terminal": _encode(binding.terminal_observation_id),
            "ready": _encode(binding.ready_artifact_id),
            "consumed": _encode(binding.consumed_artifact_id),
            "terminal_artifact": _encode(binding.terminal_artifact_id)}

    @staticmethod
    def _binding(connection, row):
        if row.profile != row.capability:
            raise ManifestHandoffRegistryUnavailable
        reservations = connection.execute(_RESERVATIONS, {"handle": row.handle_id}).all()
        if len(reservations) != 3:
            raise ManifestHandoffRegistryUnavailable
        roles = {}
        for item in reservations:
            if item.role in roles:
                raise ManifestHandoffRegistryUnavailable
            roles[item.role] = ManifestHandoffSupervisorControlArtifactId(_decode(item.artifact_id))
        if set(roles) != {"wrapper_ready", "release_consumed", "terminal_envelope"}:
            raise ManifestHandoffRegistryUnavailable
        _utc(row.bound_at)
        return StartManifestHandoffSupervisorGateWrapper(
            ManifestHandoffSupervisorHandleId(_decode(row.handle_id)),
            ManifestHandoffSupervisorControlDirectoryId(_decode(row.control_directory_id)),
            ManifestHandoffSupervisorEngineProfile(row.profile),
            roles["wrapper_ready"],
            ManifestHandoffSupervisorGatedObservationId(_decode(row.gated_observation_id)),
            roles["release_consumed"], roles["terminal_envelope"],
            ManifestHandoffSupervisorTerminalObservationId(_decode(row.terminal_observation_id)))

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
        elif connection.dialect.name != "sqlite":
            raise ManifestHandoffRegistryUnavailable
