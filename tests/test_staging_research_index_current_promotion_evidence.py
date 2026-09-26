import pytest

from liquent_platform.application.staging_research_index_current_promotion_evidence import (
    CurrentStagingResearchIndexPromotionEvidence,
    CurrentStagingResearchIndexPromotionEvidenceUnavailable,
    resolve_current_staging_research_index_promotion_evidence,
)
from tests.test_staging_research_index_promotion_evidence_store import _binding


class Evidence:
    def __init__(self, binding):
        self.binding = binding
        self.calls = []

    def resolve(self, digest):
        self.calls.append(digest)
        return self.binding


class Candidates:
    def __init__(self, digest):
        self.digest = digest
        self.calls = []

    def resolve_current(self, origin):
        self.calls.append(origin)
        return self.digest


def test_exact_persisted_evidence_for_current_candidate_resolves() -> None:
    binding = _binding()
    evidence = Evidence(binding)
    candidates = Candidates(binding.run.candidate_digest)

    current = resolve_current_staging_research_index_promotion_evidence(
        binding.evidence_digest, evidence, candidates
    )

    assert type(current) is CurrentStagingResearchIndexPromotionEvidence
    assert current.binding is binding
    assert evidence.calls == [binding.evidence_digest]
    assert candidates.calls == [binding.run.staging_origin]


@pytest.mark.parametrize("current", [None, "sha256:" + "f" * 64])
def test_absent_or_changed_current_candidate_is_neutral(current) -> None:
    binding = _binding()
    assert resolve_current_staging_research_index_promotion_evidence(
        binding.evidence_digest, Evidence(binding), Candidates(current)
    ) is None


def test_absent_evidence_never_resolves_candidate() -> None:
    candidates = Candidates("sha256:" + "a" * 64)
    assert resolve_current_staging_research_index_promotion_evidence(
        "sha256:" + "b" * 64, Evidence(None), candidates
    ) is None
    assert candidates.calls == []


def test_substituted_binding_and_failures_are_detail_free() -> None:
    binding = _binding()
    with pytest.raises(CurrentStagingResearchIndexPromotionEvidenceUnavailable):
        resolve_current_staging_research_index_promotion_evidence(
            binding.evidence_digest, Evidence(object()), Candidates(None)
        )
    with pytest.raises(CurrentStagingResearchIndexPromotionEvidenceUnavailable):
        resolve_current_staging_research_index_promotion_evidence(
            "sha256:" + "c" * 64, Evidence(binding), Candidates(None)
        )
    with pytest.raises(CurrentStagingResearchIndexPromotionEvidenceUnavailable):
        resolve_current_staging_research_index_promotion_evidence(
            binding.evidence_digest, Evidence(binding), Candidates("not-a-digest")
        )

    class Broken:
        def resolve(self, _digest):
            raise RuntimeError("database detail")

    with pytest.raises(CurrentStagingResearchIndexPromotionEvidenceUnavailable) as raised:
        resolve_current_staging_research_index_promotion_evidence(
            binding.evidence_digest, Broken(), Candidates(None)
        )
    assert raised.value.__cause__ is None and raised.value.__context__ is None
    assert "database detail" not in str(raised.value)


def test_result_is_non_authorizing_and_hides_binding() -> None:
    binding = _binding()
    current = CurrentStagingResearchIndexPromotionEvidence(binding)
    assert repr(current) == "CurrentStagingResearchIndexPromotionEvidence()"
    assert binding.evidence_digest not in repr(current)
    assert not hasattr(current, "promote")
    assert not hasattr(current, "authority")
