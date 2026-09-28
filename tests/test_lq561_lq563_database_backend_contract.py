from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_contract_is_closed_structured_and_detail_free() -> None:
    document = (ROOT / "docs/lq-561-supported-database-backend-contract.md").read_text()
    for value in (
        "ausschließlich", "`sqlite`", "`postgresql`",
        "vor Engineaufbau", "`unsupported_database_backend`",
        "`invalid_database_url`", "keine\nEingabe- oder Parserdetails",
        "keinen neuen Exceptiontyp",
    ):
        assert value in document


def test_implementation_order_precedes_engine_and_driver_work() -> None:
    document = (ROOT / "docs/lq-562-fail-closed-database-backend-boundary.md").read_text()
    for value in (
        "weder Cause noch Context", "Nur `sqlite` und\n`postgresql`",
        "bevor `create_engine`", "kein optionaler Fremdtreiber",
        "eingebauten `ValueError`", "öffnet auf keinem Zweig",
    ):
        assert value in document


def test_regression_evidence_covers_rejection_and_preservation() -> None:
    document = (ROOT / "docs/lq-563-database-backend-boundary-regression.md").read_text()
    for value in (
        "MySQL-, Oracle-", "Microsoft-SQL-Server-URLs",
        "Cause und\nContext bleiben leer", "`sqlite+pysqlite:///:memory:`",
        "`postgresql+psycopg`", "27\nTests",
        "-W error::DeprecationWarning",
    ):
        assert value in document


def test_completion_audit_records_full_green_matrix() -> None:
    document = (ROOT / "docs/lq-564-database-backend-boundary-completion-audit.md").read_text()
    for value in (
        "5065 Tests", "einem erwarteten Skip",
        "105 `postgres_integration`-Tests", "5066", "30 Tests",
        "-W error::DeprecationWarning", "MySQL/PyMySQL-URL",
        "`unsupported_database_backend`", "68 Console Entry Points",
        "69 Operator-Dateien", "42 Migrationen", "`20260826_0042`",
        "kein weiterer\nSlice",
    ):
        assert value in document


def test_roadmap_closes_database_backend_bundle() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text()
    section = roadmap.split(
        "- LQ-564 database backend boundary completion audit:", 1
    )[1].split("\n- LQ-192", 1)[0]
    for value in (
        "5065 normalen Tests", "105 PostgreSQL-Tests", "68/69/42",
        "20260826_0042", "kein weiterer Slice",
    ):
        assert value in section
