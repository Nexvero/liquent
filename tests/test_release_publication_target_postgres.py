from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pytest
from sqlalchemy import Engine

from liquent_platform.identity.release_publication import (
    ReleasePublicationArtifactBytes,
    VerifiedReleasePublicationArtifacts,
    ReleasePublicationTargetDecisionKind,
)
from liquent_platform.persistence.release_publication_target import DatabaseReleasePublicationTargetInspection
from test_release_promotion_verifier import KEY_ID, DECISION_TIME, signed_candidate
from test_release_publication_artifacts import ATTEMPT, EXECUTION, HANDOFF, seed_prepared
from test_release_publication_target import Inspector
from tools.release_promotion_verifier import verify_release_promotion


pytestmark = pytest.mark.postgres_integration


def test_postgresql_resolves_controlled_target_before_read_only_inspection(
    postgres_engine: Engine, signed_candidate, tmp_path: Path,
):
    evidence = verify_release_promotion(
        bundle_path=signed_candidate["bundle"], signature_path=signed_candidate["signature"],
        registry_path=signed_candidate["registry"], key_id=KEY_ID, clock=lambda: DECISION_TIME,
    )
    evidence_path = tmp_path / "promotion-target-postgres.json"
    evidence_path.write_text(json.dumps(evidence, sort_keys=True, separators=(",", ":")) + "\n")
    with postgres_engine.begin() as connection:
        values = seed_prepared(connection, signed_candidate, evidence_path, evidence)
    artifacts = ReleasePublicationArtifactBytes(
        signed_candidate["bundle"].name, signed_candidate["bundle"].read_bytes(),
        signed_candidate["signature"].read_bytes(), evidence_path.read_bytes(),
    )
    verified = VerifiedReleasePublicationArtifacts(
        EXECUTION, ATTEMPT, HANDOFF, str(evidence["package_version"]),
        values["bundle"], values["wheel"], values["checksums"],
        values["signature"], values["evidence"], artifacts,
    )
    class Integrity:
        def verify_artifacts(self, execution_id, attempt_id): return verified
    inspector = Inspector()
    result = DatabaseReleasePublicationTargetInspection(
        postgres_engine, artifact_integrity=Integrity(), target_inspector=inspector,
    ).inspect_publication_target(EXECUTION, ATTEMPT)
    assert result.kind is ReleasePublicationTargetDecisionKind.CREATE_ALLOWED
    assert result.target.package_version == "1.2.3"
    assert len(inspector.calls) == 1
