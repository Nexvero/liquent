from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pytest
from sqlalchemy import Engine

from liquent_platform.identity.release_authority import ReleasePromotionVerifierId
from liquent_platform.identity.release_publication import ReleasePublicationArtifactBinding
from liquent_platform.persistence.release_publication_artifacts import (
    BoundLocalReleasePublicationArtifactSource,
    DatabaseReleasePublicationArtifactIntegrityCheck,
    ReleasePublicationArtifactFiles,
)
from liquent_platform.persistence.release_registry_projection import DatabaseCurrentReleaseAuthorityRegistryProjection
from test_release_promotion_verifier import KEY_ID, DECISION_TIME, signed_candidate
from test_release_publication_artifacts import ATTEMPT, EXECUTION, HANDOFF, seed_prepared
from tools.release_promotion_verifier import verify_release_promotion


pytestmark = pytest.mark.postgres_integration


def test_postgresql_resolves_prepared_attempt_for_byte_verification(
    postgres_engine: Engine, signed_candidate, tmp_path: Path,
):
    evidence = verify_release_promotion(
        bundle_path=signed_candidate["bundle"], signature_path=signed_candidate["signature"],
        registry_path=signed_candidate["registry"], key_id=KEY_ID, clock=lambda: DECISION_TIME,
    )
    evidence_path = tmp_path / "promotion-postgres.json"
    evidence_path.write_text(json.dumps(evidence, sort_keys=True, separators=(",", ":")) + "\n")
    with postgres_engine.begin() as connection:
        values = seed_prepared(connection, signed_candidate, evidence_path, evidence)
    binding = ReleasePublicationArtifactBinding(HANDOFF, values["bundle"], values["signature"], values["evidence"])
    source = BoundLocalReleasePublicationArtifactSource({binding: ReleasePublicationArtifactFiles(
        signed_candidate["bundle"], signed_candidate["signature"], evidence_path
    )})
    projection = DatabaseCurrentReleaseAuthorityRegistryProjection(
        postgres_engine, verification_identity=ReleasePromotionVerifierId(str(evidence["verification_identity"]))
    )
    result = DatabaseReleasePublicationArtifactIntegrityCheck(
        postgres_engine, artifact_source=source, registry_projection=projection,
        clock=lambda: datetime(2026, 8, 18, 20, tzinfo=timezone.utc),
    ).verify_artifacts(EXECUTION, ATTEMPT)
    assert result is not None
    assert result.bundle_sha256 == hashlib.sha256(signed_candidate["bundle"].read_bytes()).hexdigest()
