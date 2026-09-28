import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.release_publication import (
    ReleasePublicationFinalStatus,
    ReleasePublicationProviderReceiptId,
    ReleasePublicationReassessmentId,
    ReleasePublicationTargetObservation,
)
from liquent_platform.persistence.release_publication_finalize import DatabaseReleasePublicationReconciliationFinalizer
from liquent_platform.persistence.release_publication_reconciliation import DatabaseReleasePublicationUnknownOutcomeReconciliation
from test_release_promotion_verifier import KEY_ID, DECISION_TIME, signed_candidate
from test_release_publication_artifacts import ATTEMPT, EXECUTION, seed_prepared
from test_release_publication_target import Inspector
from tools.release_promotion_verifier import verify_release_promotion


pytestmark = pytest.mark.postgres_integration


def test_postgresql_atomically_finalizes_confirmed_publication(
    postgres_engine: Engine, signed_candidate, tmp_path: Path,
):
    evidence = verify_release_promotion(
        bundle_path=signed_candidate["bundle"], signature_path=signed_candidate["signature"],
        registry_path=signed_candidate["registry"], key_id=KEY_ID, clock=lambda: DECISION_TIME,
    )
    evidence_path = tmp_path / "promotion-finalize-postgres.json"
    evidence_path.write_text(json.dumps(evidence, sort_keys=True, separators=(",", ":")) + "\n")
    with postgres_engine.begin() as connection:
        values = seed_prepared(connection, signed_candidate, evidence_path, evidence)
        connection.execute(text("UPDATE release_publication_executions SET status='outcome_unknown'"))
        connection.execute(text("UPDATE release_publication_execution_attempts SET status='outcome_unknown'"))
    observation = ReleasePublicationTargetObservation(
        "artifact-postgres-259", "revision-postgres-259", "liquent", "1.2.3",
        values["wheel"], True,
    )
    reconcile = DatabaseReleasePublicationUnknownOutcomeReconciliation(
        postgres_engine, target_inspector=Inspector(observation),
    )
    result = DatabaseReleasePublicationReconciliationFinalizer(
        postgres_engine, reconciliation=reconcile,
        generate_receipt_id=lambda: ReleasePublicationProviderReceiptId("receipt-postgres-259"),
        generate_reassessment_id=lambda: ReleasePublicationReassessmentId("reassessment-postgres-259"),
        clock=lambda: datetime(2026, 8, 18, 22, tzinfo=timezone.utc),
    ).finalize_reconciliation(EXECUTION, ATTEMPT)
    assert result.status is ReleasePublicationFinalStatus.PUBLISHED
    with postgres_engine.connect() as connection:
        assert connection.execute(text(
            "SELECT execution.status,attempt.status,"
            "(SELECT count(*) FROM release_publication_receipts)"
            " FROM release_publication_executions execution"
            " JOIN release_publication_execution_attempts attempt"
            " ON attempt.execution_id=execution.execution_id"
        )).one() == ("published", "reconciled", 1)
