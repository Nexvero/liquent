from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_completion_audit_records_closed_chain_and_exact_inventory() -> None:
    document = (ROOT / "docs/lq-545-supervisor-cleanup-retention-chain-completion-audit.md").read_text()
    assert "LQ-537 bis LQ-545" in document
    assert "68 Console Entry Points" in document
    assert "68 fachliche\nOperatormodule plus Paketinitialisierer" in document
    assert "42 Migrationen bis Head\n`20260826_0042`" in document
    assert "kein weiterer Slice nötig" in document


def test_roadmap_records_completion_without_automatic_cleanup() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text()
    section = roadmap.split("- LQ-545 supervisor cleanup retention chain completion audit:", 1)[1]
    section = section.split("\n- LQ-192", 1)[0]
    assert "fachlich und technisch geschlossen" in section
    assert "keine automatische Cleanupwirkung" in section
