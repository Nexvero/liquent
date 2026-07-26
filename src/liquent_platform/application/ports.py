"""Small stable ports shared by platform application workflows.

Ports describe capabilities needed by workflows. Concrete filesystem,
database, HTTP, or object-storage implementations belong to adapters and must
not leak into this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class ArtifactReference:
    """Immutable reference to content stored outside the domain model."""

    key: str
    sha256: str
    media_type: str
    size_bytes: int


class ArtifactStore(Protocol):
    """Storage boundary for immutable experiment and evidence artifacts."""

    def put(
        self,
        *,
        key: str,
        content: bytes,
        media_type: str,
    ) -> ArtifactReference: ...

    def get(self, reference: ArtifactReference) -> bytes: ...


class Clock(Protocol):
    """Explicit time source for deterministic application workflows."""

    def now(self) -> datetime: ...


class IdentifierFactory(Protocol):
    """Stable boundary for generating persistent object identities."""

    def new(self) -> str: ...
