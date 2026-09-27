from pathlib import Path

import pytest
from sqlalchemy import text

from liquent_platform.application.staging_research_index_evidence_codec import (
    encode_staging_research_index_evidence,
)
from liquent_platform.application.staging_research_index_promotion_eligibility import (
    StagingResearchIndexPromotionEligibility,
)
from liquent_platform.application.staging_research_index_promotion_evidence import (
    bind_staging_research_index_promotion_evidence,
)
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.staging_research_index_promotion_evidence import (
    DatabaseStagingResearchIndexPromotionEvidence,
    StagingResearchIndexPromotionEvidenceStoreUnavailable,
)
from tests.test_staging_research_index_evidence_codec import RUN, _handoffs


def _binding():
    return bind_staging_research_index_promotion_evidence(
        StagingResearchIndexPromotionEligibility(RUN),
        encode_staging_research_index_evidence(_handoffs()),
    )


def test_record_and_resolve_exact_binding(tmp_path: Path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'evidence.db'}")
    upgrade_to_head(str(engine.url))
    store = DatabaseStagingResearchIndexPromotionEvidence(engine)
    try:
        binding = _binding()
        assert store.resolve(binding.evidence_digest) is None
        assert store.record(binding) == binding
        assert store.resolve(binding.evidence_digest) == binding
        assert store.record(binding) == binding
        with engine.connect() as connection:
            assert connection.scalar(text(
                "SELECT count(*) FROM staging_research_index_promotion_evidence"
            )) == 1
    finally:
        engine.dispose()


def test_conflicting_existing_record_fails_closed(tmp_path: Path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'conflict.db'}")
    upgrade_to_head(str(engine.url))
    store = DatabaseStagingResearchIndexPromotionEvidence(engine)
    binding = _binding()
    try:
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO staging_research_index_promotion_evidence VALUES"
                " (:evidence,:candidate,:origin,:observed)"
            ), {
                "evidence": binding.evidence_digest,
                "candidate": "sha256:" + "f" * 64,
                "origin": RUN.staging_origin,
                "observed": RUN.observed_at.isoformat().replace("+00:00", "Z"),
            })
        with pytest.raises(StagingResearchIndexPromotionEvidenceStoreUnavailable):
            store.record(binding)
    finally:
        engine.dispose()


def test_invalid_input_and_technical_failure_are_detail_free(tmp_path: Path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'absent.db'}")
    store = DatabaseStagingResearchIndexPromotionEvidence(engine)
    try:
        with pytest.raises(StagingResearchIndexPromotionEvidenceStoreUnavailable):
            store.record(object())  # type: ignore[arg-type]
        with pytest.raises(StagingResearchIndexPromotionEvidenceStoreUnavailable) as raised:
            store.resolve(_binding().evidence_digest)
        assert raised.value.__cause__ is None and raised.value.__context__ is None
        assert "absent" not in str(raised.value)
    finally:
        engine.dispose()


def test_representation_hides_engine_and_evidence(tmp_path: Path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'hidden.db'}")
    try:
        store = DatabaseStagingResearchIndexPromotionEvidence(engine)
        assert repr(store) == "DatabaseStagingResearchIndexPromotionEvidence()"
        assert str(engine.url) not in repr(store)
        assert not hasattr(store, "promote")
        assert not hasattr(store, "delete")
    finally:
        engine.dispose()
