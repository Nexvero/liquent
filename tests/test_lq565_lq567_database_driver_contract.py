from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_contract_has_exact_sync_allowlist_and_closed_precedence() -> None:
    document = (ROOT / "docs/lq-565-supported-database-driver-contract.md").read_text()
    for value in (
        "genau `sqlite`, `sqlite+pysqlite` und\n`postgresql+psycopg`",
        "keinen automatischen Treiberwechsel", "vor\nAdapter-",
        "`unsupported_database_driver`", "Cause und Context bleiben leer",
        "`unsupported_database_backend`", "kein neuer Exceptiontyp",
    ):
        assert value in document


def test_implementation_order_precedes_adapter_and_engine_work() -> None:
    document = (ROOT / "docs/lq-566-fail-closed-database-driver-boundary.md").read_text()
    for value in (
        "1. URL", "2. Backend", "3. vollständiger Treibername",
        "4. Adapter-", "`create_engine` wird nicht aufgerufen",
        "erst\nnach erfolgreicher Treiberprüfung", "weder Cause noch Context",
    ):
        assert value in document


def test_regression_evidence_covers_rejected_allowed_and_precedence() -> None:
    document = (ROOT / "docs/lq-567-database-driver-boundary-regression.md").read_text()
    for value in (
        "SQLite/Aiosqlite", "SQLite/APSW", "PostgreSQL/Asyncpg",
        "PostgreSQL/Psycopg2", "bares PostgreSQL",
        "`sqlite+pysqlite:///:memory:`", "MySQL/Asyncmy-Beispiel",
        "48 Tests", "-W error::DeprecationWarning",
    ):
        assert value in document


def test_completion_audit_records_full_green_matrix() -> None:
    document = (ROOT / "docs/lq-568-database-driver-boundary-completion-audit.md").read_text()
    for value in (
        "5079 Tests", "einem erwarteten Skip",
        "105 `postgres_integration`-Tests", "5080", "51 Tests",
        "-W error::DeprecationWarning", "PostgreSQL/Asyncpg-URL",
        "`unsupported_database_driver`", "68 Console Entry Points",
        "69 Operator-Dateien", "42 Migrationen", "`20260826_0042`",
        "kein weiterer\nSlice",
    ):
        assert value in document


def test_roadmap_closes_database_driver_bundle() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text()
    section = roadmap.split(
        "- LQ-568 database driver boundary completion audit:", 1
    )[1].split("\n- LQ-192", 1)[0]
    for value in (
        "5079 normalen Tests", "105 PostgreSQL-Tests", "68/69/42",
        "20260826_0042", "kein weiterer Slice",
    ):
        assert value in section
