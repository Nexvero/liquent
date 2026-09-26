"""Opaque revision-bound control contract for one revocation fixture."""

from dataclasses import dataclass, field
import re
from typing import Protocol


_OPAQUE = re.compile(r"[A-Za-z0-9._~-]{16,256}\Z")


def _validate_opaque(value: object) -> None:
    if type(value) is not str or _OPAQUE.fullmatch(value) is None:
        raise ValueError("opaque fixture material is invalid")


@dataclass(frozen=True, slots=True)
class StagingResearchIndexFixtureId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _validate_opaque(self.value)


@dataclass(frozen=True, slots=True)
class StagingResearchIndexFixtureRevision:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _validate_opaque(self.value)


@dataclass(frozen=True, slots=True)
class RevokedStagingResearchIndexFixture:
    fixture_id: StagingResearchIndexFixtureId = field(repr=False)
    active_revision: StagingResearchIndexFixtureRevision = field(repr=False)
    revoked_revision: StagingResearchIndexFixtureRevision = field(repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.fixture_id) is not StagingResearchIndexFixtureId
            or type(self.active_revision) is not StagingResearchIndexFixtureRevision
            or type(self.revoked_revision) is not StagingResearchIndexFixtureRevision
            or self.active_revision == self.revoked_revision
        ):
            raise ValueError("revoked fixture binding is invalid")


@dataclass(frozen=True, slots=True)
class RestoredStagingResearchIndexFixture:
    fixture_id: StagingResearchIndexFixtureId = field(repr=False)
    revoked_revision: StagingResearchIndexFixtureRevision = field(repr=False)
    restored_revision: StagingResearchIndexFixtureRevision = field(repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.fixture_id) is not StagingResearchIndexFixtureId
            or type(self.revoked_revision) is not StagingResearchIndexFixtureRevision
            or type(self.restored_revision) is not StagingResearchIndexFixtureRevision
            or self.revoked_revision == self.restored_revision
        ):
            raise ValueError("restored fixture binding is invalid")


class StagingResearchIndexFixtureRevoker(Protocol):
    def revoke(
        self,
        fixture_id: StagingResearchIndexFixtureId,
        expected_active_revision: StagingResearchIndexFixtureRevision,
    ) -> RevokedStagingResearchIndexFixture: ...


class StagingResearchIndexFixtureRestorer(Protocol):
    def restore(
        self,
        revoked: RevokedStagingResearchIndexFixture,
    ) -> RestoredStagingResearchIndexFixture: ...


def validate_staging_research_index_fixture_restoration(
    revoked: RevokedStagingResearchIndexFixture,
    restored: RestoredStagingResearchIndexFixture,
) -> None:
    """Require an exact fixture and revision chain across restore."""

    if (
        type(revoked) is not RevokedStagingResearchIndexFixture
        or type(restored) is not RestoredStagingResearchIndexFixture
        or restored.fixture_id != revoked.fixture_id
        or restored.revoked_revision != revoked.revoked_revision
        or restored.restored_revision in {
            revoked.active_revision,
            revoked.revoked_revision,
        }
    ):
        raise ValueError("fixture restoration binding is invalid")
