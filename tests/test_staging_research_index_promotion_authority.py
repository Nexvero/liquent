from dataclasses import replace

import pytest

from liquent_platform.application.staging_research_index_current_promotion_evidence import (
    CurrentStagingResearchIndexPromotionEvidence,
)
from liquent_platform.application.staging_research_index_promotion_authority import (
    CurrentStagingResearchIndexPromotionAuthority,
    StagingResearchIndexPromotionAuthorityUnavailable,
    resolve_staging_research_index_promotion_authority,
)
from liquent_platform.identity.access import UserId
from liquent_platform.identity.session import SessionPrincipal
from tests.test_staging_research_index_promotion_evidence_store import _binding


ACTOR = SessionPrincipal(UserId("user-2704"))


class Authorities:
    def __init__(self, authority):
        self.authority = authority
        self.calls = []

    def resolve_current(self, actor, evidence):
        self.calls.append((actor, evidence))
        return self.authority


def _current():
    return CurrentStagingResearchIndexPromotionEvidence(_binding())


def _authority(current):
    run = current.binding.run
    return CurrentStagingResearchIndexPromotionAuthority(
        ACTOR.user_id, run.candidate_digest, run.staging_origin, "production"
    )


def test_current_authority_binds_actor_candidate_origin_and_target() -> None:
    current = _current()
    source = Authorities(_authority(current))
    authority = resolve_staging_research_index_promotion_authority(
        ACTOR, current, source
    )
    assert authority is source.authority
    assert authority.target_environment == "production"
    assert source.calls == [(ACTOR, current)]


def test_absent_or_revoked_authority_is_neutral_on_each_decision() -> None:
    current = _current()
    source = Authorities(_authority(current))
    assert resolve_staging_research_index_promotion_authority(
        ACTOR, current, source
    ) is not None
    source.authority = None
    assert resolve_staging_research_index_promotion_authority(
        ACTOR, current, source
    ) is None
    assert len(source.calls) == 2


@pytest.mark.parametrize(
    "change",
    [
        {"actor_user_id": UserId("other-user")},
        {"candidate_digest": "sha256:" + "f" * 64},
        {"staging_origin": "https://other.example"},
    ],
)
def test_substituted_authority_binding_fails_closed(change) -> None:
    current = _current()
    substituted = replace(_authority(current), **change)
    with pytest.raises(StagingResearchIndexPromotionAuthorityUnavailable):
        resolve_staging_research_index_promotion_authority(
            ACTOR, current, Authorities(substituted)
        )


def test_session_and_evidence_do_not_grant_authority() -> None:
    current = _current()
    assert resolve_staging_research_index_promotion_authority(
        ACTOR, current, Authorities(None)
    ) is None


def test_invalid_input_and_reader_failure_are_detail_free() -> None:
    current = _current()
    with pytest.raises(StagingResearchIndexPromotionAuthorityUnavailable):
        resolve_staging_research_index_promotion_authority(
            object(), current, Authorities(None)  # type: ignore[arg-type]
        )

    class Broken:
        def resolve_current(self, _actor, _evidence):
            raise RuntimeError("authority backend detail")

    with pytest.raises(StagingResearchIndexPromotionAuthorityUnavailable) as raised:
        resolve_staging_research_index_promotion_authority(ACTOR, current, Broken())
    assert raised.value.__cause__ is None and raised.value.__context__ is None
    assert "backend detail" not in str(raised.value)


def test_representation_hides_authority_binding_and_cannot_promote() -> None:
    authority = _authority(_current())
    assert repr(authority) == "CurrentStagingResearchIndexPromotionAuthority()"
    assert authority.candidate_digest not in repr(authority)
    assert authority.target_environment not in repr(authority)
    assert not hasattr(authority, "promote")
