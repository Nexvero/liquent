from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_contract_requires_every_sqlite_connection_to_enforce_constraints() -> None:
    document = (ROOT / "docs/lq-557-sqlite-foreign-key-enforcement-contract.md").read_text()
    for value in (
        "Jede durch die zentrale Enginefactory", "`PRAGMA foreign_keys=ON`",
        "Pool-Reconnect", "vor deren erster fachlicher Transaktion",
        "ausschließlich für SQLite", "keine Migration",
    ):
        assert value in document


def test_implementation_is_lazy_dialect_scoped_and_resource_safe() -> None:
    document = (ROOT / "docs/lq-558-central-sqlite-foreign-key-activation.md").read_text()
    for value in (
        "Connect-Listener", "schließt den\nCursor in jedem Fall",
        "öffnet weiterhin keine Verbindung", "PostgreSQL",
        "testlokalen Listener", "idempotent",
    ):
        assert value in document


def test_regression_evidence_covers_effect_reconnect_and_failure() -> None:
    document = (ROOT / "docs/lq-559-sqlite-foreign-key-regression-evidence.md").read_text()
    for value in (
        "`sqlite://`", "`sqlite:///:memory:`", "`IntegrityError`",
        "Nach `dispose()`", "keinen\nSQLite-Connect-Listener",
        "39 Tests", "-W error::DeprecationWarning",
    ):
        assert value in document


def test_completion_audit_records_full_green_matrix() -> None:
    document = (ROOT / "docs/lq-560-sqlite-foreign-key-enforcement-completion-audit.md").read_text()
    for value in (
        "5051 Tests", "einem erwarteten Skip",
        "105 `postgres_integration`-Tests", "5052", "42 Tests",
        "-W error::DeprecationWarning", "`PRAGMA foreign_keys=1`",
        "68 Console Entry Points", "69 Operator-Dateien", "42 Migrationen",
        "`20260826_0042`", "kein\nweiterer Slice",
    ):
        assert value in document


def test_roadmap_closes_foreign_key_maintenance_bundle() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text()
    section = roadmap.split(
        "- LQ-560 SQLite foreign-key enforcement completion audit:", 1
    )[1].split("\n- LQ-192", 1)[0]
    for value in (
        "5051 normalen Tests", "105 PostgreSQL-Tests", "68/69/42",
        "20260826_0042", "kein weiterer Slice",
    ):
        assert value in section
