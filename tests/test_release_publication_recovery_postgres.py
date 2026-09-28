import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.release_publication import ReleasePublicationReassessmentId, ReleasePublicationRecoveryId
from liquent_platform.persistence.release_publication_reconciliation import DatabaseReleasePublicationUnknownOutcomeReconciliation
from liquent_platform.persistence.release_publication_recovery import DatabaseReleasePublicationRecoveryFinalizer
from test_release_promotion_verifier import KEY_ID, DECISION_TIME, signed_candidate
from test_release_publication_artifacts import ATTEMPT, EXECUTION, seed_prepared
from test_release_publication_target import Inspector
from tools.release_promotion_verifier import verify_release_promotion


pytestmark = pytest.mark.postgres_integration


def test_postgresql_atomically_closes_confirmed_absence_without_retry(
    postgres_engine: Engine, signed_candidate, tmp_path: Path,
):
    evidence = verify_release_promotion(
        bundle_path=signed_candidate["bundle"], signature_path=signed_candidate["signature"],
        registry_path=signed_candidate["registry"], key_id=KEY_ID, clock=lambda: DECISION_TIME,
    )
    evidence_path = tmp_path / "promotion-recovery-postgres.json"
    evidence_path.write_text(json.dumps(evidence, sort_keys=True, separators=(",", ":")) + "\n")
    with postgres_engine.begin() as connection:
        seed_prepared(connection, signed_candidate, evidence_path, evidence)
        connection.execute(text("UPDATE release_publication_executions SET status='outcome_unknown'"))
        connection.execute(text("UPDATE release_publication_execution_attempts SET status='outcome_unknown'"))
    reconcile = DatabaseReleasePublicationUnknownOutcomeReconciliation(
        postgres_engine, target_inspector=Inspector(),
    )
    result = DatabaseReleasePublicationRecoveryFinalizer(
        postgres_engine, reconciliation=reconcile,
        generate_recovery_id=lambda: ReleasePublicationRecoveryId("recovery-postgres-260"),
        generate_reassessment_id=lambda: ReleasePublicationReassessmentId("reassessment-postgres-260"),
        clock=lambda: datetime(2026, 8, 19, tzinfo=timezone.utc),
    ).finalize_recovery(EXECUTION, ATTEMPT)
    assert result.retry_eligible is True
    with postgres_engine.connect() as connection:
        assert connection.execute(text(
            "SELECT execution.status,attempt.status,"
            "(SELECT count(*) FROM release_publication_recovery_decisions)"
            " FROM release_publication_executions execution"
            " JOIN release_publication_execution_attempts attempt"
            " ON attempt.execution_id=execution.execution_id"
        )).one() == ("prepared", "reconciled", 1)
