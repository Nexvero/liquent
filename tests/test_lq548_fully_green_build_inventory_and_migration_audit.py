from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_audit_records_exact_green_matrix_and_inventory() -> None:
    document = (ROOT / "docs/lq-548-fully-green-build-inventory-and-migration-audit.md").read_text()
    for value in (
        "5026 Tests", "105 Tests", "42 lineare Migrationsdateien",
        "`20260826_0042`", "68 Console Entry Points", "69 Python-Dateien",
    ):
        assert value in document
    assert "git diff --check" in document
    assert "kein weiterer Slice nötig" in document


def test_roadmap_records_green_audit_without_deployment_claim() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text()
    section = roadmap.split("- LQ-548 fully green build inventory and migration audit:", 1)[1]
    section = section.split("\n- LQ-192", 1)[0]
    assert "5026 normale" in section
    assert "PostgreSQL-Suite mit 105 Tests" in section
    assert "68/69/42" in section
    assert "keine Productionfreigabe" in section
