from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_contract_closes_semantic_query_surface_and_details() -> None:
    document = (ROOT / "docs/lq-577-sqlite-url-query-policy-contract.md").read_text()
    for value in (
        "nur die Kompatibilitätsschlüssel `timeout`", "`check_same_thread`",
        "`uri`", "`mode`", "`cache`", "`immutable`", "`nolock`",
        "`unsupported_database_url_option`", "Cause und\nContext bleiben leer",
        "PostgreSQL-Queryparameter bleiben außerhalb",
    ):
        assert value in document


def test_implementation_contract_preserves_order_and_no_side_effects() -> None:
    document = (ROOT / "docs/lq-578-fail-closed-sqlite-url-query-boundary.md").read_text()
    for value in (
        "1. URL", "2. Backend", "3. Treiber", "4. SQLite-Queryschlüssel",
        "5. Adapter-", "MySQL mit `uri=true`", "SQLite/Aiosqlite",
        "öffnet keine Verbindung", "keine globalen SQLite-Adapter",
    ):
        assert value in document


def test_regression_record_covers_rejection_compatibility_and_postgresql() -> None:
    document = (ROOT / "docs/lq-579-sqlite-url-query-boundary-regression.md").read_text()
    for value in (
        "`mode=memory`", "`mode=ro`", "`cache=shared`",
        "`unsupported_database_backend`", "`unsupported_database_driver`",
        "`sslmode`", "`application_name`", "53 Tests",
        "-W error::DeprecationWarning",
    ):
        assert value in document


def test_completion_audit_records_full_green_matrix() -> None:
    document = (ROOT / "docs/lq-580-sqlite-url-query-boundary-completion-audit.md").read_text()
    for value in (
        "5112 Tests", "einem erwarteten Skip",
        "105 `postgres_integration`-Tests", "5113", "56 Tests",
        "-W error::DeprecationWarning", "`timeout=0.001`",
        "`PRAGMA busy_timeout=5000`", "`uri=true&mode=memory`",
        "`unsupported_database_url_option`", "68 Console Entry Points",
        "69 Operator-Dateien", "42 Migrationen", "`20260826_0042`",
        "kein weiterer\nSlice",
    ):
        assert value in document


def test_roadmap_closes_sqlite_url_query_bundle() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text()
    section = roadmap.split(
        "- LQ-580 SQLite URL query boundary completion audit:", 1
    )[1].split("\n- LQ-192", 1)[0]
    for value in (
        "5112 normalen Tests", "105 PostgreSQL-Tests", "68/69/42",
        "20260826_0042", "kein weiterer Slice",
    ):
        assert value in section
