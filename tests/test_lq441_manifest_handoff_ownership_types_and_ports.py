from datetime import datetime, timedelta, timezone
import inspect
from pathlib import Path

import pytest

from liquent_platform.identity.access import UserId
from liquent_platform.identity.manifest_handoff import (
    AppendedManifestHandoffObservation,
    AppendedManifestHandoffRecoveryObservation,
    ClaimedManifestHandoffExecution,
    ClaimedManifestHandoffRecovery,
    ManifestHandoffAttemptId,
    ManifestHandoffExecutionClaimId,
    ManifestHandoffExecutionEndId,
    ManifestHandoffExecutionEndKind,
    ManifestHandoffExecutionOwnerId,
    ManifestHandoffLeaseRenewalId,
    ManifestHandoffName,
    ManifestHandoffObservationId,
    ManifestHandoffObservationKind,
    ManifestHandoffOwnershipConflict,
    ManifestHandoffRecoveryClaimId,
    ManifestHandoffRecoveryOwnerId,
    ManifestHandoffRecoveryRequest,
    ManifestHandoffRegistryScopeId,
    RecordedManifestHandoffExecutionEnd,
    RenewedManifestHandoffExecutionLease,
    StartedManifestHandoffExecution,
)
from liquent_platform.identity.ports import (
    AuthorizedManifestHandoffExecutionClaim,
    AuthorizedManifestHandoffRecoveryClaim,
    ControlledManifestHandoffClaimedWriterStart,
    ControlledManifestHandoffExecutionEnd,
    ControlledManifestHandoffRecoveryObservationAppend,
    ManifestHandoffExecutionLeaseRenewal,
)


NOW = datetime(2026, 8, 24, 20, tzinfo=timezone.utc)
ATTEMPT = ManifestHandoffAttemptId("attempt-441")
EXECUTION = ManifestHandoffExecutionClaimId("execution-441")
EXECUTION_OWNER = ManifestHandoffExecutionOwnerId("execution-owner-441")
RECOVERY = ManifestHandoffRecoveryClaimId("recovery-441")
RECOVERY_OWNER = ManifestHandoffRecoveryOwnerId("recovery-owner-441")


def test_execution_claim_and_lease_are_repr_safe_non_authorizations() -> None:
    claimed = ClaimedManifestHandoffExecution(
        EXECUTION, ATTEMPT, EXECUTION_OWNER, NOW, NOW + timedelta(minutes=2)
    )
    renewed = RenewedManifestHandoffExecutionLease(
        ManifestHandoffLeaseRenewalId("renewal-441"),
        EXECUTION, EXECUTION_OWNER, NOW, NOW + timedelta(minutes=2)
    )
    assert claimed.writer_authorized is False
    assert renewed.recovery_authorized is False
    assert "execution-441" not in repr(claimed)
    assert "execution-owner-441" not in repr(renewed)
    with pytest.raises(TypeError):
        ClaimedManifestHandoffExecution(
            EXECUTION,
            ATTEMPT,
            EXECUTION_OWNER,
            NOW,
            NOW + timedelta(minutes=2),
            writer_authorized=True,
        )
    with pytest.raises(ValueError):
        RenewedManifestHandoffExecutionLease(
            ManifestHandoffLeaseRenewalId("invalid-renewal-441"),
            EXECUTION, EXECUTION_OWNER, NOW, NOW
        )


def test_claimed_start_and_source_specific_end_are_closed() -> None:
    started = StartedManifestHandoffExecution(
        EXECUTION,
        ATTEMPT,
        ManifestHandoffObservationId("started-441"),
        EXECUTION_OWNER,
        NOW,
    )
    ended = RecordedManifestHandoffExecutionEnd(
        ManifestHandoffExecutionEndId("ended-441"),
        EXECUTION,
        ATTEMPT,
        ManifestHandoffExecutionEndKind.OUTCOME_UNKNOWN,
        NOW,
    )
    assert "execution-441" not in repr(started)
    assert "ended-441" not in repr(ended)
    assert set(ManifestHandoffExecutionEndKind) == {
        ManifestHandoffExecutionEndKind.OUTCOME_SECURED,
        ManifestHandoffExecutionEndKind.OUTCOME_UNKNOWN,
        ManifestHandoffExecutionEndKind.START_NOT_CONFIRMED,
    }


def test_recovery_request_and_claim_carry_no_paths_or_authority_flags() -> None:
    request = ManifestHandoffRecoveryRequest(
        RECOVERY,
        UserId("actor-441"),
        ManifestHandoffRegistryScopeId("scope-441"),
        ManifestHandoffName("handoff-441"),
        RECOVERY_OWNER,
    )
    claimed = ClaimedManifestHandoffRecovery(
        RECOVERY, ATTEMPT, EXECUTION, RECOVERY_OWNER, NOW
    )
    assert set(request.__dataclass_fields__) == {
        "claim_id", "actor_user_id", "scope_id", "handoff_name", "owner_id"
    }
    assert "actor-441" not in repr(request) and "scope-441" not in repr(request)
    assert claimed.writer_authorized is False
    assert claimed.cleanup_authorized is False
    assert not set(request.__dataclass_fields__) & {
        "source_root", "target_root", "allow", "role", "process_ended"
    }


def test_recovery_observation_accepts_only_reconciliation_kinds() -> None:
    absent = AppendedManifestHandoffObservation(
        ManifestHandoffObservationId("observation-441"),
        ATTEMPT,
        4,
        ManifestHandoffObservationKind.MANIFEST_ABSENT,
        NOW,
    )
    value = AppendedManifestHandoffRecoveryObservation(RECOVERY, absent)
    assert value.observation is absent

    started = AppendedManifestHandoffObservation(
        ManifestHandoffObservationId("other-441"),
        ATTEMPT,
        2,
        ManifestHandoffObservationKind.WRITER_STARTED,
        NOW,
    )
    with pytest.raises(ValueError):
        AppendedManifestHandoffRecoveryObservation(RECOVERY, started)


def test_ownership_conflict_and_port_signatures_are_closed() -> None:
    assert repr(ManifestHandoffOwnershipConflict()) == "ManifestHandoffOwnershipConflict()"
    signatures = {
        AuthorizedManifestHandoffExecutionClaim.claim_execution: (
            "self", "claim_id", "attempt_id", "actor_user_id", "owner_id"
        ),
        ManifestHandoffExecutionLeaseRenewal.renew_execution_lease: (
            "self", "renewal_id", "claim_id", "owner_id"
        ),
        ControlledManifestHandoffClaimedWriterStart.start_claimed_execution: (
            "self", "observation_id", "claim_id", "owner_id"
        ),
        AuthorizedManifestHandoffRecoveryClaim.claim_recovery: ("self", "request"),
    }
    for method, expected in signatures.items():
        assert tuple(inspect.signature(method).parameters) == expected

    end_methods = {
        name for name, value in ControlledManifestHandoffExecutionEnd.__dict__.items()
        if callable(value) and not name.startswith("_")
    }
    assert end_methods == {
        "record_outcome_secured", "record_outcome_unknown", "record_start_not_confirmed"
    }
    recovery_methods = {
        name
        for name, value in ControlledManifestHandoffRecoveryObservationAppend.__dict__.items()
        if callable(value) and not name.startswith("_")
    }
    assert recovery_methods == {
        "record_manifest_absent",
        "record_manifest_temporary_only",
        "record_manifest_handed_off",
        "record_manifest_handed_off_pending_cleanup",
        "record_manifest_handoff_conflict",
    }


def test_roadmap_records_types_ports_and_next_slice() -> None:
    roadmap = (Path(__file__).parents[1] / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-441 manifest handoff ownership and recovery types and ports:" in roadmap
    assert "`docs/lq-441-manifest-handoff-ownership-and-recovery-types-and-ports.md`" in roadmap
    assert "nächster Slice LQ-442" in roadmap
