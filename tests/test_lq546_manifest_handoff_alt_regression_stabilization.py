from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_stabilization_document_records_all_repaired_boundaries() -> None:
    document = (ROOT / "docs/lq-546-manifest-handoff-alt-regression-stabilization.md").read_text()
    for boundary in ("LQ-432", "LQ-438", "LQ-443", "Architekturguard"):
        assert boundary in document
    assert "5021 Tests" in document
    assert "LQ-302" in document


def test_roadmap_records_stabilization_and_separate_next_slice() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text()
    section = roadmap.split("- LQ-546 manifest handoff alt-regression stabilization:", 1)[1]
    section = section.split("\n- LQ-192", 1)[0]
    assert "sieben normalen Altregressionen" in section
    assert "5021" in section
    assert "nächster Slice LQ-547" in section
