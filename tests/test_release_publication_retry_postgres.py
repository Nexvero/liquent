import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.release_authority import ReleasePromotionVerifierId
from liquent_platform.identity.release_publication import (
    ReleasePublicationArtifactBinding,
    ReleasePublicationAttemptId,
    ReleasePublicationReassessmentId,
    ReleasePublicationRecoveryId,
)
from liquent_platform.persistence.release_publication_artifacts import BoundLocalReleasePublicationArtifactSource, DatabaseReleasePublicationArtifactIntegrityCheck, ReleasePublicationArtifactFiles
from liquent_platform.persistence.release_publication_reconciliation import DatabaseReleasePublicationUnknownOutcomeReconciliation
from liquent_platform.persistence.release_publication_recovery import DatabaseReleasePublicationRecoveryFinalizer
from liquent_platform.persistence.release_publication_retry import DatabaseReleasePublicationRetryAttemptPreflight
from liquent_platform.persistence.release_registry_projection import DatabaseCurrentReleaseAuthorityRegistryProjection
from test_release_promotion_verifier import KEY_ID, DECISION_TIME, signed_candidate
from test_release_publication_artifacts import ATTEMPT, EXECUTION, HANDOFF, seed_prepared
from test_release_publication_target import Inspector
from tools.release_promotion_verifier import verify_release_promotion


pytestmark = pytest.mark.postgres_integration


def test_postgresql_prepares_attempt_two_after_fresh_absence_preflight(
    postgres_engine: Engine, signed_candidate, tmp_path: Path,
):
    evidence = verify_release_promotion(
        bundle_path=signed_candidate["bundle"], signature_path=signed_candidate["signature"],
        registry_path=signed_candidate["registry"], key_id=KEY_ID, clock=lambda: DECISION_TIME,
    )
    evidence_path = tmp_path / "promotion-retry-postgres.json"
    evidence_path.write_text(json.dumps(evidence, sort_keys=True, separators=(",", ":")) + "\n")
    with postgres_engine.begin() as connection:
        values = seed_prepared(connection, signed_candidate, evidence_path, evidence)
        connection.execute(text("UPDATE release_publication_executions SET status='outcome_unknown'"))
        connection.execute(text("UPDATE release_publication_execution_attempts SET status='outcome_unknown'"))
    DatabaseReleasePublicationRecoveryFinalizer(
        postgres_engine, reconciliation=DatabaseReleasePublicationUnknownOutcomeReconciliation(
            postgres_engine, target_inspector=Inspector(),
        ), generate_recovery_id=lambda: ReleasePublicationRecoveryId("recovery-postgres-261"),
        generate_reassessment_id=lambda: ReleasePublicationReassessmentId("unused-postgres-261"),
        clock=lambda: datetime(2026, 8, 19, 1, tzinfo=timezone.utc),
    ).finalize_recovery(EXECUTION, ATTEMPT)
    binding = ReleasePublicationArtifactBinding(
        HANDOFF, values["bundle"], values["signature"], values["evidence"]
    )
    source = BoundLocalReleasePublicationArtifactSource({binding: ReleasePublicationArtifactFiles(
        signed_candidate["bundle"], signed_candidate["signature"], evidence_path
    )})
    integrity = DatabaseReleasePublicationArtifactIntegrityCheck(
        postgres_engine, artifact_source=source,
        registry_projection=DatabaseCurrentReleaseAuthorityRegistryProjection(
            postgres_engine, verification_identity=ReleasePromotionVerifierId(str(evidence["verification_identity"]))
        ), clock=lambda: DECISION_TIME,
    )
    result = DatabaseReleasePublicationRetryAttemptPreflight(
        postgres_engine, artifact_integrity=integrity, target_inspector=Inspector(),
        generate_attempt_id=lambda: ReleasePublicationAttemptId("attempt-postgres-261"),
        clock=lambda: datetime(2026, 8, 19, 2, tzinfo=timezone.utc),
    ).prepare_retry_attempt(EXECUTION, ATTEMPT)
    assert result.attempt_number == 2
    with postgres_engine.connect() as connection:
        assert connection.execute(text(
            "SELECT attempt_number,status FROM release_publication_execution_attempts "
            "ORDER BY attempt_number"
        )).all() == [(1, "reconciled"), (2, "prepared")]
