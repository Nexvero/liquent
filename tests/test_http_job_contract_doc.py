from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "lq-075-http-job-contract.md"


def test_contract_defines_minimal_research_resources() -> None:
    document = DOC.read_text(encoding="utf-8")

    for resource in (
        "POST /v1/research/jobs",
        "GET /v1/research/jobs/{job_id}",
        "GET /v1/research/jobs/{job_id}/evidence",
    ):
        assert resource in document
    assert "`202 Accepted` bestätigt nur die Annahme" in document


def test_contract_reuses_existing_domain_language() -> None:
    document = DOC.read_text(encoding="utf-8")

    for existing_type in (
        "ResearchJobStatus",
        "InMemoryResearchJob",
        "BacktestExperimentSummary",
        "execution_failed",
    ):
        assert existing_type in document
    assert "kein paralleles HTTP-Evidence-Modell" in document


def test_contract_is_fail_closed_and_does_not_leak_details() -> None:
    document = DOC.read_text(encoding="utf-8")

    assert "`422 Unprocessable Entity`" in document
    assert "unvollständige Eingaben scheitern fail-closed" in document
    for private_detail in ("Exception-Texte", "Stacktraces", "Dateipfade"):
        assert private_detail in document


def test_route_activation_has_a_small_explicit_gate() -> None:
    document = DOC.read_text(encoding="utf-8")

    assert "vollständiger, unveränderlicher Experiment-Snapshot" in document
    assert "minimale Job-Ablage" in document
    assert "noch keine aktivierten Routen" in document
    assert "kein spekulativer Produktcode" in document
