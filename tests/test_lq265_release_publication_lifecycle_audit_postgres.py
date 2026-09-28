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
    ReleasePublicationTargetObservation,
)
from liquent_platform.persistence.release_publication_artifacts import (
    BoundLocalReleasePublicationArtifactSource,
    DatabaseReleasePublicationArtifactIntegrityCheck,
    ReleasePublicationArtifactFiles,
)
from liquent_platform.persistence.release_publication_create import (
    DatabaseReleasePublicationImmutableCreate,
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
from liquent_platform.persistence.release_publication_retry import (
    DatabaseReleasePublicationRetryAttemptPreflight,
)
from liquent_platform.persistence.release_publication_retry_create import (
    DatabaseReleasePublicationRetryImmutableCreate,
)
from liquent_platform.persistence.release_publication_target import (
    DatabaseReleasePublicationTargetInspection,
)
from liquent_platform.persistence.release_registry_projection import (
    DatabaseCurrentReleaseAuthorityRegistryProjection,
)
from test_release_promotion_verifier import DECISION_TIME, KEY_ID, signed_candidate
from test_release_publication_artifacts import ATTEMPT, EXECUTION, HANDOFF, seed_prepared
from test_release_publication_target import Inspector
from tools.release_promotion_verifier import verify_release_promotion


pytestmark = pytest.mark.postgres_integration
ATTEMPT_TWO = ReleasePublicationAttemptId("attempt-postgres-lq265-two")
NOW = datetime(2026, 8, 19, 9, tzinfo=timezone.utc)


def test_postgresql_full_two_attempt_lifecycle_reaches_one_receipt(
    postgres_engine: Engine, signed_candidate, tmp_path: Path,
):
    evidence = verify_release_promotion(
        bundle_path=signed_candidate["bundle"],
        signature_path=signed_candidate["signature"],
        registry_path=signed_candidate["registry"], key_id=KEY_ID,
        clock=lambda: DECISION_TIME,
    )
    evidence_path = tmp_path / "promotion-lq265-postgres.json"
    evidence_path.write_text(
        json.dumps(evidence, sort_keys=True, separators=(",", ":")) + "\n"
    )
    with postgres_engine.begin() as connection:
        values = seed_prepared(
            connection, signed_candidate, evidence_path, evidence
        )
    binding = ReleasePublicationArtifactBinding(
        HANDOFF, values["bundle"], values["signature"], values["evidence"]
    )
    integrity = DatabaseReleasePublicationArtifactIntegrityCheck(
        postgres_engine,
        artifact_source=BoundLocalReleasePublicationArtifactSource({
            binding: ReleasePublicationArtifactFiles(
                signed_candidate["bundle"], signed_candidate["signature"],
                evidence_path,
            )
        }),
        registry_projection=DatabaseCurrentReleaseAuthorityRegistryProjection(
            postgres_engine,
            verification_identity=ReleasePromotionVerifierId(
                str(evidence["verification_identity"])
            ),
        ),
        clock=lambda: DECISION_TIME,
    )
    keys = []
    class Creator:
        def create_immutable(self, target, artifacts, idempotency_key):
            keys.append(idempotency_key)
            return ReleasePublicationCreateAcknowledgement(
                f"request-postgres-lq265-{len(keys)}"
            )
    creator = Creator()
    first_inspection = DatabaseReleasePublicationTargetInspection(
        postgres_engine, artifact_integrity=integrity,
        target_inspector=Inspector(),
    )
    DatabaseReleasePublicationImmutableCreate(
        postgres_engine, target_inspection=first_inspection,
        immutable_creator=creator,
    ).create_publication(EXECUTION, ATTEMPT)
    first_reconciliation = DatabaseReleasePublicationUnknownOutcomeReconciliation(
        postgres_engine, target_inspector=Inspector(),
    )
    DatabaseReleasePublicationRecoveryFinalizer(
        postgres_engine, reconciliation=first_reconciliation,
        generate_recovery_id=lambda: ReleasePublicationRecoveryId(
            "recovery-postgres-lq265-one"
        ),
        generate_reassessment_id=lambda: ReleasePublicationReassessmentId(
            "unused-postgres-lq265-one"
        ),
        clock=lambda: NOW,
    ).finalize_recovery(EXECUTION, ATTEMPT)
    DatabaseReleasePublicationRetryAttemptPreflight(
        postgres_engine, artifact_integrity=integrity,
        target_inspector=Inspector(), generate_attempt_id=lambda: ATTEMPT_TWO,
        clock=lambda: NOW,
    ).prepare_retry_attempt(EXECUTION, ATTEMPT)
    DatabaseReleasePublicationRetryImmutableCreate(
        postgres_engine, artifact_integrity=integrity,
        target_inspector=Inspector(), immutable_creator=creator,
    ).create_retry_publication(EXECUTION, ATTEMPT_TWO)
    observation = ReleasePublicationTargetObservation(
        "artifact-postgres-lq265", "revision-postgres-lq265", "liquent",
        "1.2.3", values["wheel"], True,
    )
    result = DatabaseReleasePublicationReconciliationFinalizer(
        postgres_engine,
        reconciliation=DatabaseReleasePublicationUnknownOutcomeReconciliation(
            postgres_engine, target_inspector=Inspector(observation),
        ),
        generate_receipt_id=lambda: ReleasePublicationProviderReceiptId(
            "receipt-postgres-lq265"
        ),
        generate_reassessment_id=lambda: ReleasePublicationReassessmentId(
            "unused-postgres-lq265-published"
        ),
        clock=lambda: NOW,
    ).finalize_reconciliation(EXECUTION, ATTEMPT_TWO)
    assert result.attempt_id == ATTEMPT_TWO
    assert keys == [EXECUTION, ATTEMPT_TWO]
    with postgres_engine.connect() as connection:
        assert connection.execute(text(
            "SELECT (SELECT status FROM release_publication_executions),"
            " (SELECT count(*) FROM release_publication_execution_attempts),"
            " (SELECT count(*) FROM release_publication_receipts)"
        )).one() == ("published", 2, 1)
