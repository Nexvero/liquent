from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_completion_audit_records_strict_green_matrix() -> None:
    document = (ROOT / "docs/lq-552-warning-free-python-312-persistence-completion-audit.md").read_text()
    for value in (
        "5032 Tests", "105 Tests", "-W error::DeprecationWarning",
        "68 Entry Points", "69 Operator-Dateien", "42\nMigrationen",
        "`20260826_0042`", "kein weiterer Slice",
    ):
        assert value in document


def test_roadmap_marks_bundled_maintenance_complete() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text()
    section = roadmap.split("- LQ-552 warning-free Python 3.12 persistence completion audit:", 1)[1]
    section = section.split("\n- LQ-192", 1)[0]
    assert "5032 normalen Tests" in section
    assert "105 PostgreSQL-Tests" in section
    assert "789" in section and "beseitigt" in section
    assert "kein weiterer Slice" in section
