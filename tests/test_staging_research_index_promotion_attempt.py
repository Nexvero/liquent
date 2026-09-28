from dataclasses import fields

import pytest

from liquent_platform.application.staging_research_index_atomic_promotion import (
    StagingResearchIndexPromotionCommand,
)
from liquent_platform.application.staging_research_index_promotion_attempt import (
    PreparedStagingResearchIndexPromotionAttempt,
    StagingResearchIndexPromotionAttemptStore,
    UnknownStagingResearchIndexPromotionEffect,
    WriteStartedStagingResearchIndexPromotionAttempt,
)
from liquent_platform.application.staging_research_index_promotion_authority import (
    CurrentStagingResearchIndexPromotionAuthority,
)
from liquent_platform.identity.access import UserId
from liquent_platform.identity.session import SessionPrincipal


ACTOR = SessionPrincipal(UserId("user-2706"))
COMMAND = StagingResearchIndexPromotionCommand(ACTOR, "sha256:" + "a" * 64)
AUTHORITY = CurrentStagingResearchIndexPromotionAuthority(
    ACTOR.user_id,
    "sha256:" + "b" * 64,
    "https://staging.liquent.ai",
    "production",
)


def test_prepared_attempt_binds_command_authority_and_operation() -> None:
    attempt = PreparedStagingResearchIndexPromotionAttempt(
        "promotion-2706", COMMAND, AUTHORITY
    )
    assert [item.name for item in fields(attempt)] == [
        "operation_id", "command", "authority"
    ]
    assert repr(attempt) == "PreparedStagingResearchIndexPromotionAttempt()"
    assert COMMAND.evidence_digest not in repr(attempt)


def test_prepared_attempt_rejects_actor_substitution() -> None:
    foreign = CurrentStagingResearchIndexPromotionAuthority(
        UserId("other-user"),
        AUTHORITY.candidate_digest,
        AUTHORITY.staging_origin,
        AUTHORITY.target_environment,
    )
    with pytest.raises(ValueError, match="prepared staging promotion"):
        PreparedStagingResearchIndexPromotionAttempt("promotion-2706", COMMAND, foreign)


def test_write_started_and_unknown_states_are_exactly_nested() -> None:
    prepared = PreparedStagingResearchIndexPromotionAttempt(
        "promotion-2706", COMMAND, AUTHORITY
    )
    started = WriteStartedStagingResearchIndexPromotionAttempt(prepared)
    unknown = UnknownStagingResearchIndexPromotionEffect(started)
    assert unknown.attempt.prepared is prepared
    assert repr(started) == "WriteStartedStagingResearchIndexPromotionAttempt()"
    assert repr(unknown) == "UnknownStagingResearchIndexPromotionEffect()"
    assert not hasattr(unknown, "retry")


def test_store_requires_write_start_before_any_outcome() -> None:
    operations = {
        name
        for name, value in StagingResearchIndexPromotionAttemptStore.__dict__.items()
        if not name.startswith("_") and callable(value)
    }
    assert operations == {
        "prepare_current",
        "mark_write_started",
        "record_unknown",
        "record_committed",
    }
    assert "retry" not in operations
