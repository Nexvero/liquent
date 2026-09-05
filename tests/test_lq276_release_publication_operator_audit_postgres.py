import json
from pathlib import Path

import pytest
from sqlalchemy import Engine

from test_lq276_release_publication_operator_audit import (
    audit_operator_publishes_once,
)
from test_release_promotion_verifier import DECISION_TIME, KEY_ID, signed_candidate
from test_release_publication_artifacts import seed_prepared
from tools.release_promotion_verifier import verify_release_promotion


pytestmark = pytest.mark.postgres_integration


def test_manual_operator_boundary_on_postgresql(
    postgres_engine: Engine,
    postgres_url: str,
    signed_candidate,
    tmp_path: Path,
    monkeypatch,
    capsys,
):
    evidence = verify_release_promotion(
        bundle_path=signed_candidate["bundle"],
        signature_path=signed_candidate["signature"],
        registry_path=signed_candidate["registry"],
        key_id=KEY_ID,
        clock=lambda: DECISION_TIME,
    )
    evidence_path = tmp_path / "promotion-lq276.json"
    evidence_path.write_text(
        json.dumps(evidence, sort_keys=True, separators=(",", ":")) + "\n"
    )
    with postgres_engine.begin() as connection:
        seed_prepared(connection, signed_candidate, evidence_path, evidence)
    audit_operator_publishes_once(
        engine=postgres_engine,
        database_url=postgres_url,
        candidate=signed_candidate,
        evidence_path=evidence_path,
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        capsys=capsys,
    )
