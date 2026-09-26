from dataclasses import fields

import pytest

from liquent_platform.application.staging_research_index_atomic_promotion import (
    AtomicStagingResearchIndexPromotionGateway,
    StagingResearchIndexPromotionCommand,
    StagingResearchIndexPromotionReceipt,
)
from liquent_platform.identity.access import UserId
from liquent_platform.identity.session import SessionPrincipal


ACTOR = SessionPrincipal(UserId("user-2705"))
DIGEST = "sha256:" + "a" * 64
CANDIDATE = "sha256:" + "b" * 64


def test_command_contains_only_actor_and_evidence_lookup_key() -> None:
    command = StagingResearchIndexPromotionCommand(ACTOR, DIGEST)
    assert [item.name for item in fields(command)] == ["actor", "evidence_digest"]
    assert repr(command) == "StagingResearchIndexPromotionCommand()"
    assert DIGEST not in repr(command)
    assert not hasattr(command, "allow")
    assert not hasattr(command, "role")
    assert not hasattr(command, "target_environment")


@pytest.mark.parametrize(
    "actor,digest",
    [(object(), DIGEST), (ACTOR, "not-a-digest"), (ACTOR, "sha256:" + "A" * 64)],
)
def test_command_rejects_substituted_or_noncanonical_input(actor, digest) -> None:
    with pytest.raises(ValueError, match="promotion command"):
        StagingResearchIndexPromotionCommand(actor, digest)


def test_receipt_binds_observed_atomic_effect_without_granting_authority() -> None:
    receipt = StagingResearchIndexPromotionReceipt(
        "promotion-2705",
        ACTOR.user_id,
        DIGEST,
        CANDIDATE,
        "https://staging.liquent.ai",
        "production",
    )
    assert repr(receipt) == "StagingResearchIndexPromotionReceipt()"
    assert DIGEST not in repr(receipt)
    assert CANDIDATE not in repr(receipt)
    assert not hasattr(receipt, "promote")
    assert not hasattr(receipt, "authority")


def test_gateway_exposes_one_atomic_promotion_operation() -> None:
    public_operations = {
        name
        for name, value in AtomicStagingResearchIndexPromotionGateway.__dict__.items()
        if not name.startswith("_") and callable(value)
    }
    assert public_operations == {"promote_current"}
