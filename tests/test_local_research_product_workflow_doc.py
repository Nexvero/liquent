from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "lq-071-local-research-product-workflow.md"


def test_slice_one_workflow_contains_complete_user_path() -> None:
    document = DOC.read_text(encoding="utf-8")

    for stage in ("Workspace", "Data", "Strategy", "Run", "Evidence"):
        assert f"**{stage}**" in document
    for product_object in (
        "Workspace",
        "Dataset Selection",
        "Strategy Draft",
        "Experiment Input",
        "Research Job",
        "Evidence Summary",
    ):
        assert product_object in document


def test_slice_one_job_lifecycle_is_explicit_and_retry_is_immutable() -> None:
    document = DOC.read_text(encoding="utf-8")

    for state in (
        "Draft",
        "Ready",
        "Queued",
        "Running",
        "Succeeded",
        "Failed",
        "Cancelled",
        "Invalidated",
        "Discarded",
    ):
        assert f"**{state}:**" in document
    assert "Ein erneuter Versuch erzeugt\nein neues Experiment" in document
    assert "überschreibt keinen bestehenden Lauf" in document


def test_slice_one_preserves_research_and_compliance_boundaries() -> None:
    document = DOC.read_text(encoding="utf-8")

    for boundary in (
        "keine Empfehlung",
        "keine Live-Ausführung",
        "Broker-, Exchange- oder Echtzeitdatenanbindung",
        "Paper- oder Live-Automation",
        "keine Technologieauswahl",
        "kein Release, Deployment oder externer Datenzugriff",
    ):
        assert boundary in document


def test_slice_one_has_fail_closed_and_empty_result_semantics() -> None:
    document = DOC.read_text(encoding="utf-8")

    assert "Ungültige Daten oder Parameter verhindern den Start fail-closed" in document
    assert "Ein Lauf ohne Signale gilt als gültige technische Evidenz" in document
    assert "keine Teil-Evidence als Erfolg" in document
    assert "kein stilles Defaulting" in document


def test_follow_up_sequence_stays_inside_slice_one() -> None:
    document = DOC.read_text(encoding="utf-8")

    for ticket in ("LQ-072", "LQ-073", "LQ-074", "LQ-075", "LQ-076"):
        assert f"**{ticket}:**" in document
    assert "erster ausführbarer In-Memory-Workflow" in document
