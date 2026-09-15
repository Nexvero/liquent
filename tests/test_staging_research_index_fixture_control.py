from dataclasses import replace

import pytest

from liquent_platform.application.staging_research_index_fixture_control import (
    RestoredStagingResearchIndexFixture,
    RevokedStagingResearchIndexFixture,
    StagingResearchIndexFixtureId,
    StagingResearchIndexFixtureRevision,
    validate_staging_research_index_fixture_restoration,
)


FIXTURE = StagingResearchIndexFixtureId("opaque-fixture-0001")
ACTIVE = StagingResearchIndexFixtureRevision("active-revision-001")
REVOKED = StagingResearchIndexFixtureRevision("revoked-revision-01")
RESTORED = StagingResearchIndexFixtureRevision("restored-revision-1")


def test_exact_revocation_and_restoration_chain_is_valid() -> None:
    revoked = RevokedStagingResearchIndexFixture(FIXTURE, ACTIVE, REVOKED)
    restored = RestoredStagingResearchIndexFixture(FIXTURE, REVOKED, RESTORED)
    validate_staging_research_index_fixture_restoration(revoked, restored)
    assert "opaque-fixture" not in repr(revoked)
    assert "revision" not in repr(restored)


@pytest.mark.parametrize("value", ("", "short", "contains space", "ä" * 16))
def test_opaque_fixture_material_is_closed(value) -> None:
    with pytest.raises(ValueError):
        StagingResearchIndexFixtureId(value)
    with pytest.raises(ValueError):
        StagingResearchIndexFixtureRevision(value)


def test_revocation_requires_a_new_revision() -> None:
    with pytest.raises(ValueError):
        RevokedStagingResearchIndexFixture(FIXTURE, ACTIVE, ACTIVE)


def test_restore_requires_a_new_revision() -> None:
    with pytest.raises(ValueError):
        RestoredStagingResearchIndexFixture(FIXTURE, REVOKED, REVOKED)


@pytest.mark.parametrize("mutation", ("fixture", "source", "reuse_active"))
def test_restore_must_continue_the_exact_revocation(mutation) -> None:
    revoked = RevokedStagingResearchIndexFixture(FIXTURE, ACTIVE, REVOKED)
    restored = RestoredStagingResearchIndexFixture(FIXTURE, REVOKED, RESTORED)
    if mutation == "fixture":
        restored = replace(
            restored,
            fixture_id=StagingResearchIndexFixtureId("opaque-fixture-0002"),
        )
    elif mutation == "source":
        restored = replace(
            restored,
            revoked_revision=StagingResearchIndexFixtureRevision(
                "revoked-revision-02"
            ),
        )
    else:
        restored = replace(restored, restored_revision=ACTIVE)
    with pytest.raises(ValueError):
        validate_staging_research_index_fixture_restoration(revoked, restored)


def test_boolean_role_or_identity_material_is_not_part_of_contract() -> None:
    fields = RevokedStagingResearchIndexFixture.__dataclass_fields__
    assert set(fields) == {"fixture_id", "active_revision", "revoked_revision"}
    assert not {"allow", "role", "user_id", "workspace_id", "session"} & set(fields)
