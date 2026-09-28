from datetime import datetime, timezone
import json
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.release_publication import (
    InspectedReleasePublicationTarget,
    ReleasePublicationArtifactBytes,
    ReleasePublicationCreateAcknowledgement,
    ReleasePublicationTarget,
    ReleasePublicationTargetDecisionKind,
    VerifiedReleasePublicationArtifacts,
    ReleasePublicationChannelId,
    ReleasePublicationChannelPolicyRevisionId,
)
from liquent_platform.persistence.release_publication_create import DatabaseReleasePublicationImmutableCreate
from test_release_promotion_verifier import KEY_ID, DECISION_TIME, signed_candidate
from test_release_publication_artifacts import ATTEMPT, EXECUTION, HANDOFF, seed_prepared
from tools.release_promotion_verifier import verify_release_promotion


pytestmark = pytest.mark.postgres_integration


def test_postgresql_commits_write_start_before_create_and_unknown_after(
    postgres_engine: Engine, signed_candidate, tmp_path: Path,
):
    evidence = verify_release_promotion(
        bundle_path=signed_candidate["bundle"], signature_path=signed_candidate["signature"],
        registry_path=signed_candidate["registry"], key_id=KEY_ID, clock=lambda: DECISION_TIME,
    )
    evidence_path = tmp_path / "promotion-create-postgres.json"
    evidence_path.write_text(json.dumps(evidence, sort_keys=True, separators=(",", ":")) + "\n")
    with postgres_engine.begin() as connection:
        values = seed_prepared(connection, signed_candidate, evidence_path, evidence)
    artifacts = ReleasePublicationArtifactBytes(
        signed_candidate["bundle"].name, signed_candidate["bundle"].read_bytes(),
        signed_candidate["signature"].read_bytes(), evidence_path.read_bytes(),
    )
    verified = VerifiedReleasePublicationArtifacts(
        EXECUTION, ATTEMPT, HANDOFF, "1.2.3", values["bundle"], values["wheel"],
        values["checksums"], values["signature"], values["evidence"], artifacts,
    )
    inspected = InspectedReleasePublicationTarget(
        ReleasePublicationTargetDecisionKind.CREATE_ALLOWED,
        ReleasePublicationTarget(
            ReleasePublicationChannelId("channel-255"),
            ReleasePublicationChannelPolicyRevisionId("channel-revision-255"),
            "package-index", "stable", "liquent", "1.2.3",
        ), verified,
    )
    class Inspection:
        def inspect_publication_target(self, execution_id, attempt_id): return inspected
    class Creator:
        def create_immutable(self, target, artifacts, idempotency_key):
            with postgres_engine.connect() as connection:
                assert connection.scalar(text(
                    "SELECT status FROM release_publication_execution_attempts"
                )) == "write_started"
            return ReleasePublicationCreateAcknowledgement("request-postgres-257")
    result = DatabaseReleasePublicationImmutableCreate(
        postgres_engine, target_inspection=Inspection(), immutable_creator=Creator(),
    ).create_publication(EXECUTION, ATTEMPT)
    assert result is not None
    with postgres_engine.connect() as connection:
        assert connection.execute(text(
            "SELECT execution.status,attempt.status FROM release_publication_executions execution"
            " JOIN release_publication_execution_attempts attempt"
            " ON attempt.execution_id=execution.execution_id"
        )).one() == ("outcome_unknown", "outcome_unknown")
