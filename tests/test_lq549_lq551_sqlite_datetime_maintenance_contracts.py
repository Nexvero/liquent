from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_three_slices_record_contract_implementation_and_regression() -> None:
    names = (
        "lq-549-python-312-sqlite-datetime-compatibility-contract.md",
        "lq-550-explicit-python-312-sqlite-datetime-adapters.md",
        "lq-551-sqlite-utc-persistence-warning-regression.md",
    )
    documents = [(ROOT / "docs" / name).read_text() for name in names]
    assert "keine neue fachliche\nZeitsemantik" in documents[0]
    assert "_configure_sqlite_adapters()" in documents[1]
    assert "48 fokussierten Tests" in documents[2]


def test_roadmap_orders_maintenance_slices_before_final_audit() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text()
    positions = [roadmap.index(f"- LQ-{number}") for number in range(549, 553)]
    assert positions == sorted(positions)
