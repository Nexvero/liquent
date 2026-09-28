from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_contract_bounds_engine_local_memory_lifetime_and_thread_use() -> None:
    document = (ROOT / "docs/lq-553-sqlite-engine-url-and-pool-contract.md").read_text()
    for value in (
        "`sqlite://`", "`sqlite:///:memory:`", "pro erzeugter Engine",
        "zweite Engine", "Nach `dispose()`", "verschiedenen\nThreads",
        "kein\nErsatz",
    ):
        assert value in document


def test_implementation_contract_preserves_dialect_boundaries() -> None:
    document = (ROOT / "docs/lq-554-dialect-aware-database-engine-configuration.md").read_text()
    for value in (
        "`StaticPool`", "`check_same_thread=False`", "`QueuePool`",
        "Poolgröße 3", "Max-Overflow 2", "Pool-Timeout 5",
        "`connect_timeout=3`", "öffnet keine Verbindung",
    ):
        assert value in document


def test_regression_record_is_strict_and_bounded() -> None:
    document = (ROOT / "docs/lq-555-shared-in-memory-sqlite-engine-regression.md").read_text()
    for value in (
        "15 Tests", "-W error::DeprecationWarning", "UTC-Datetime-Wert",
        "keine gleichzeitige Mehrfachtransaktionsgarantie",
        "keine Persistenz über Engine-Disposal",
    ):
        assert value in document


def test_completion_audit_records_full_green_matrix() -> None:
    document = (ROOT / "docs/lq-556-dialect-aware-engine-completion-audit.md").read_text()
    for value in (
        "5041 Tests", "106 Tests", "105 `postgres_integration`-Tests",
        "5042", "18 Tests", "-W error::DeprecationWarning",
        "68 Console Entry Points", "69 Operator-Dateien", "42 Migrationen",
        "`20260826_0042`", "kein\nweiterer Slice",
    ):
        assert value in document


def test_roadmap_closes_engine_maintenance_bundle() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text()
    section = roadmap.split("- LQ-556 dialect-aware engine completion audit:", 1)[1]
    section = section.split("\n- LQ-192", 1)[0]
    for value in (
        "5041 normalen Tests", "105 PostgreSQL-Tests", "68/69/42",
        "20260826_0042", "kein weiterer Slice",
    ):
        assert value in section
