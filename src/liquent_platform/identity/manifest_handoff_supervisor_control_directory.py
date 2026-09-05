"""Closed values for persistent private supervisor control directories."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import re

from .manifest_handoff_supervisor import ManifestHandoffSupervisorHandleId
from .manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlDirectoryId,
)


def _require_utc(value: object) -> None:
    if (type(value) is not datetime or value.tzinfo is None
            or value.utcoffset() != timezone.utc.utcoffset(value)):
        raise ValueError("manifest handoff supervisor control directory time is invalid")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorControlDirectoryLeaf:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        if (type(self.value) is not str
                or re.fullmatch(r"[0-9a-f]{64}", self.value) is None):
            raise ValueError("manifest handoff supervisor control directory leaf is invalid")


class ManifestHandoffSupervisorControlDirectoryState(str, Enum):
    RESERVED = "reserved"
    ACTIVE = "active"
    RETIRED = "retired"


@dataclass(frozen=True, slots=True)
class ReserveManifestHandoffSupervisorControlDirectory:
    directory_id: ManifestHandoffSupervisorControlDirectoryId = field(repr=False)
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)

    def __post_init__(self) -> None:
        _validate_binding(self)


@dataclass(frozen=True, slots=True)
class ReservedManifestHandoffSupervisorControlDirectory:
    directory_id: ManifestHandoffSupervisorControlDirectoryId = field(repr=False)
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)
    leaf: ManifestHandoffSupervisorControlDirectoryLeaf = field(repr=False)
    reserved_at: datetime
    state: ManifestHandoffSupervisorControlDirectoryState = field(
        default=ManifestHandoffSupervisorControlDirectoryState.RESERVED, init=False)

    def __post_init__(self) -> None:
        _validate_binding(self)
        if type(self.leaf) is not ManifestHandoffSupervisorControlDirectoryLeaf:
            raise ValueError("manifest handoff supervisor control directory reservation is invalid")
        _require_utc(self.reserved_at)


@dataclass(frozen=True, slots=True)
class ActivateManifestHandoffSupervisorControlDirectory:
    reservation: ReservedManifestHandoffSupervisorControlDirectory = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.reservation) is not ReservedManifestHandoffSupervisorControlDirectory:
            raise ValueError("manifest handoff supervisor control directory activation is invalid")


@dataclass(frozen=True, slots=True)
class ActiveManifestHandoffSupervisorControlDirectory:
    reservation: ReservedManifestHandoffSupervisorControlDirectory = field(repr=False)
    activated_at: datetime
    state: ManifestHandoffSupervisorControlDirectoryState = field(
        default=ManifestHandoffSupervisorControlDirectoryState.ACTIVE, init=False)

    def __post_init__(self) -> None:
        if type(self.reservation) is not ReservedManifestHandoffSupervisorControlDirectory:
            raise ValueError("manifest handoff supervisor active control directory is invalid")
        _require_utc(self.activated_at)
        if self.activated_at < self.reservation.reserved_at:
            raise ValueError("manifest handoff supervisor active control directory is invalid")

    @property
    def directory_id(self): return self.reservation.directory_id

    @property
    def handle_id(self): return self.reservation.handle_id

    @property
    def leaf(self): return self.reservation.leaf


@dataclass(frozen=True, slots=True)
class RetireManifestHandoffSupervisorControlDirectory:
    active: ActiveManifestHandoffSupervisorControlDirectory = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.active) is not ActiveManifestHandoffSupervisorControlDirectory:
            raise ValueError("manifest handoff supervisor control directory retirement is invalid")


@dataclass(frozen=True, slots=True)
class RetiredManifestHandoffSupervisorControlDirectory:
    active: ActiveManifestHandoffSupervisorControlDirectory = field(repr=False)
    retired_at: datetime
    state: ManifestHandoffSupervisorControlDirectoryState = field(
        default=ManifestHandoffSupervisorControlDirectoryState.RETIRED, init=False)

    def __post_init__(self) -> None:
        if type(self.active) is not ActiveManifestHandoffSupervisorControlDirectory:
            raise ValueError("manifest handoff supervisor retired control directory is invalid")
        _require_utc(self.retired_at)
        if self.retired_at < self.active.activated_at:
            raise ValueError("manifest handoff supervisor retired control directory is invalid")

    @property
    def directory_id(self): return self.active.directory_id

    @property
    def handle_id(self): return self.active.handle_id

    @property
    def leaf(self): return self.active.leaf


ManifestHandoffSupervisorControlDirectoryLifecycle = (
    ReservedManifestHandoffSupervisorControlDirectory
    | ActiveManifestHandoffSupervisorControlDirectory
    | RetiredManifestHandoffSupervisorControlDirectory
)


def _validate_binding(value: object) -> None:
    if not all((
        type(value.directory_id) is ManifestHandoffSupervisorControlDirectoryId,
        type(value.handle_id) is ManifestHandoffSupervisorHandleId,
    )):
        raise ValueError("manifest handoff supervisor control directory binding is invalid")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorControlDirectoryConflict:
    """Detail-free divergent identity, leaf, state, or physical facts."""
