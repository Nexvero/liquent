import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.release_publication import (
    ReleasePublicationChannelId,
    ReleasePublicationChannelPolicyRevisionId,
    ReleasePublicationHandoffId,
    ReleasePublicationProviderReceiptId,
    ReleasePublicationReassessmentId,
    ReleasePublicationRecoveryId,
    ReleasePublicationTargetObservation,
    ReleasePublicationWorkRequest,
    ReleasePublicationWorkResultKind,
    ReleasePublicationWorkStateKind,
    ReleasePublisherAuthorityId,
)
from liquent_platform.persistence.release_publication_finalize import (
    DatabaseReleasePublicationReconciliationFinalizer,
)
from liquent_platform.persistence.release_publication_reconciliation import (
    DatabaseReleasePublicationUnknownOutcomeReconciliation,
)
from liquent_platform.persistence.release_publication_recovery import (
    DatabaseReleasePublicationRecoveryFinalizer,
)
from liquent_platform.persistence.release_publication_work import (
    DatabaseReleasePublicationCurrentOutcomeFinalizer,
    DatabaseReleasePublicationWorkStateLookup,
)
from test_release_promotion_verifier import (
    DECISION_TIME,
    KEY_ID,
    signed_candidate,
)
from test_release_publication_artifacts import ATTEMPT, EXECUTION, seed_prepared
from test_release_publication_target import Inspector
from tools.release_promotion_verifier import verify_release_promotion


pytestmark = pytest.mark.postgres_integration


def test_postgresql_resolves_and_finalizes_one_current_outcome(
    postgres_engine: Engine, signed_candidate, tmp_path: Path,
) -> None:
    evidence = verify_release_promotion(
        bundle_path=signed_candidate["bundle"],
        signature_path=signed_candidate["signature"],
        registry_path=signed_candidate["registry"],
        key_id=KEY_ID,
        clock=lambda: DECISION_TIME,
    )
    evidence_path = tmp_path / "promotion-work-lq272.json"
    evidence_path.write_text(
        json.dumps(evidence, sort_keys=True, separators=(",", ":")) + "\n"
    )
    with postgres_engine.begin() as connection:
        values = seed_prepared(
            connection, signed_candidate, evidence_path, evidence
        )
        row = connection.execute(text(
            "SELECT handoff_id,publisher_authority_id,channel_id,"
            " channel_revision_id FROM release_publication_executions"
        )).one()
        connection.execute(text(
            "UPDATE release_publication_executions SET status='outcome_unknown'"
        ))
        connection.execute(text(
            "UPDATE release_publication_execution_attempts"
            " SET status='outcome_unknown'"
        ))
    request = ReleasePublicationWorkRequest(
        EXECUTION,
        ReleasePublicationHandoffId(bytes(row.handoff_id).decode()),
        ReleasePublisherAuthorityId(bytes(row.publisher_authority_id).decode()),
        ReleasePublicationChannelId(bytes(row.channel_id).decode()),
        ReleasePublicationChannelPolicyRevisionId(
            bytes(row.channel_revision_id).decode()
        ),
    )
    lookup = DatabaseReleasePublicationWorkStateLookup(postgres_engine)
    assert lookup.get_work_state(request).kind is (
        ReleasePublicationWorkStateKind.ATTEMPT_ONE_UNKNOWN
    )
    observation = ReleasePublicationTargetObservation(
        "artifact-postgres-lq272",
        "revision-postgres-lq272",
        "liquent",
        "1.2.3",
        values["wheel"],
        True,
    )
    inspector = Inspector(observation)
    reconciliation = DatabaseReleasePublicationUnknownOutcomeReconciliation(
        postgres_engine, target_inspector=inspector
    )
    receipt = DatabaseReleasePublicationReconciliationFinalizer(
        postgres_engine,
        reconciliation=reconciliation,
        generate_receipt_id=lambda: ReleasePublicationProviderReceiptId(
            "receipt-postgres-lq272"
        ),
        generate_reassessment_id=lambda: ReleasePublicationReassessmentId(
            "reassessment-postgres-lq272-receipt"
        ),
        clock=lambda: datetime(2026, 8, 19, 13, tzinfo=timezone.utc),
    )
    recovery = DatabaseReleasePublicationRecoveryFinalizer(
        postgres_engine,
        reconciliation=reconciliation,
        generate_recovery_id=lambda: ReleasePublicationRecoveryId(
            "recovery-postgres-lq272"
        ),
        generate_reassessment_id=lambda: ReleasePublicationReassessmentId(
            "reassessment-postgres-lq272-recovery"
        ),
        clock=lambda: datetime(2026, 8, 19, 13, tzinfo=timezone.utc),
    )
    result = DatabaseReleasePublicationCurrentOutcomeFinalizer(
        reconciliation=reconciliation,
        receipt_finalizer=receipt,
        recovery_finalizer=recovery,
    ).finalize_current_outcome(EXECUTION, ATTEMPT)
    assert result.status.value == "published"
    assert len(inspector.calls) == 1
    terminal = lookup.get_work_state(request)
    assert terminal.kind is ReleasePublicationWorkStateKind.TERMINAL
    assert terminal.terminal_result is ReleasePublicationWorkResultKind.PUBLISHED
