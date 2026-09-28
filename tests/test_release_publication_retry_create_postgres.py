import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.release_authority import ReleasePromotionVerifierId
from liquent_platform.identity.release_publication import (
    ReleasePublicationArtifactBinding,
    ReleasePublicationAttemptId,
    ReleasePublicationCreateAcknowledgement,
    ReleasePublicationProviderReceiptId,
    ReleasePublicationReassessmentId,
    ReleasePublicationRecoveryId,
    ReleasePublicationReconciliationKind,
    ReleasePublicationTargetObservation,
)
from liquent_platform.persistence.release_publication_artifacts import (
    BoundLocalReleasePublicationArtifactSource,
    DatabaseReleasePublicationArtifactIntegrityCheck,
    ReleasePublicationArtifactFiles,
)
from liquent_platform.persistence.release_publication_reconciliation import (
    DatabaseReleasePublicationUnknownOutcomeReconciliation,
)
from liquent_platform.persistence.release_publication_finalize import (
    DatabaseReleasePublicationReconciliationFinalizer,
)
from liquent_platform.persistence.release_publication_recovery import (
    DatabaseReleasePublicationRecoveryFinalizer,
)
from liquent_platform.persistence.release_publication_retry import (
    DatabaseReleasePublicationRetryAttemptPreflight,
)
from liquent_platform.persistence.release_publication_retry_create import (
    DatabaseReleasePublicationRetryImmutableCreate,
)
from liquent_platform.persistence.release_registry_projection import (
    DatabaseCurrentReleaseAuthorityRegistryProjection,
)
from test_release_promotion_verifier import DECISION_TIME, KEY_ID, signed_candidate
from test_release_publication_artifacts import ATTEMPT, EXECUTION, HANDOFF, seed_prepared
from test_release_publication_target import Inspector
from tools.release_promotion_verifier import verify_release_promotion


pytestmark = pytest.mark.postgres_integration
ATTEMPT_TWO = ReleasePublicationAttemptId("attempt-postgres-262")


def test_postgresql_attempt_two_create_preserves_unknown(
    postgres_engine: Engine, signed_candidate, tmp_path: Path,
):
    evidence = verify_release_promotion(
        bundle_path=signed_candidate["bundle"],
        signature_path=signed_candidate["signature"],
        registry_path=signed_candidate["registry"], key_id=KEY_ID,
        clock=lambda: DECISION_TIME,
    )
    evidence_path = tmp_path / "promotion-retry-create-postgres.json"
    evidence_path.write_text(
        json.dumps(evidence, sort_keys=True, separators=(",", ":")) + "\n"
    )
    with postgres_engine.begin() as connection:
        values = seed_prepared(
            connection, signed_candidate, evidence_path, evidence
        )
        connection.execute(text(
            "UPDATE release_publication_executions SET status='outcome_unknown'"
        ))
        connection.execute(text(
            "UPDATE release_publication_execution_attempts"
            " SET status='outcome_unknown'"
        ))
    DatabaseReleasePublicationRecoveryFinalizer(
        postgres_engine,
        reconciliation=DatabaseReleasePublicationUnknownOutcomeReconciliation(
            postgres_engine, target_inspector=Inspector(),
        ),
        generate_recovery_id=lambda: ReleasePublicationRecoveryId(
            "recovery-postgres-262"
        ),
        generate_reassessment_id=lambda: ReleasePublicationReassessmentId(
            "unused-postgres-262"
        ),
        clock=lambda: datetime(2026, 8, 19, 3, tzinfo=timezone.utc),
    ).finalize_recovery(EXECUTION, ATTEMPT)
    binding = ReleasePublicationArtifactBinding(
        HANDOFF, values["bundle"], values["signature"], values["evidence"]
    )
    source = BoundLocalReleasePublicationArtifactSource({
        binding: ReleasePublicationArtifactFiles(
            signed_candidate["bundle"], signed_candidate["signature"], evidence_path
        )
    })
    integrity = DatabaseReleasePublicationArtifactIntegrityCheck(
        postgres_engine, artifact_source=source,
        registry_projection=DatabaseCurrentReleaseAuthorityRegistryProjection(
            postgres_engine,
            verification_identity=ReleasePromotionVerifierId(
                str(evidence["verification_identity"])
            ),
        ),
        clock=lambda: DECISION_TIME,
    )
    DatabaseReleasePublicationRetryAttemptPreflight(
        postgres_engine, artifact_integrity=integrity,
        target_inspector=Inspector(), generate_attempt_id=lambda: ATTEMPT_TWO,
        clock=lambda: datetime(2026, 8, 19, 4, tzinfo=timezone.utc),
    ).prepare_retry_attempt(EXECUTION, ATTEMPT)

    class Creator:
        def create_immutable(self, target, artifacts, idempotency_key):
            assert idempotency_key == ATTEMPT_TWO
            with postgres_engine.connect() as connection:
                assert connection.scalar(text(
                    "SELECT status FROM release_publication_execution_attempts"
                    " WHERE attempt_number=2"
                )) == "write_started"
            return ReleasePublicationCreateAcknowledgement("request-postgres-262")

    result = DatabaseReleasePublicationRetryImmutableCreate(
        postgres_engine, artifact_integrity=integrity,
        target_inspector=Inspector(), immutable_creator=Creator(),
    ).create_retry_publication(EXECUTION, ATTEMPT_TWO)
    assert result.acknowledgement.provider_request_id == "request-postgres-262"
    with postgres_engine.connect() as connection:
        assert connection.execute(text(
            "SELECT execution.status,attempt.status"
            " FROM release_publication_executions execution"
            " JOIN release_publication_execution_attempts attempt"
            " ON attempt.execution_id=execution.execution_id"
            " WHERE attempt.attempt_number=2"
        )).one() == ("outcome_unknown", "outcome_unknown")
    observation = ReleasePublicationTargetObservation(
        "artifact-postgres-263", "revision-postgres-263", "liquent", "1.2.3",
        values["wheel"], True,
    )
    reconciled = DatabaseReleasePublicationUnknownOutcomeReconciliation(
        postgres_engine, target_inspector=Inspector(observation),
    ).reconcile_unknown_outcome(EXECUTION, ATTEMPT_TWO)
    assert reconciled.kind is ReleasePublicationReconciliationKind.PUBLISHED_CONFIRMED
    assert reconciled.attempt_id == ATTEMPT_TWO
    with postgres_engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT status FROM release_publication_execution_attempts"
            " WHERE attempt_number=2"
        )) == "outcome_unknown"
    finalized = DatabaseReleasePublicationReconciliationFinalizer(
        postgres_engine,
        reconciliation=DatabaseReleasePublicationUnknownOutcomeReconciliation(
            postgres_engine, target_inspector=Inspector(observation),
        ),
        generate_receipt_id=lambda: ReleasePublicationProviderReceiptId(
            "receipt-postgres-264"
        ),
        generate_reassessment_id=lambda: ReleasePublicationReassessmentId(
            "reassessment-postgres-264"
        ),
        clock=lambda: datetime(2026, 8, 19, 5, tzinfo=timezone.utc),
    ).finalize_reconciliation(EXECUTION, ATTEMPT_TWO)
    assert finalized.attempt_id == ATTEMPT_TWO
    with postgres_engine.connect() as connection:
        assert connection.execute(text(
            "SELECT execution.status,attempt.status"
            " FROM release_publication_executions execution"
            " JOIN release_publication_execution_attempts attempt"
            " ON attempt.execution_id=execution.execution_id"
            " WHERE attempt.attempt_number=2"
        )).one() == ("published", "reconciled")
