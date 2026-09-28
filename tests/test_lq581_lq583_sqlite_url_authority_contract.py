from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_contract_closes_all_sqlite_authority_fields_without_details() -> None:
    document = (ROOT / "docs/lq-581-sqlite-url-authority-contract.md").read_text()
    for value in (
        "keinen Benutzernamen", "kein Passwort", "keinen\nHost", "keinen Port",
        "`unsupported_database_url_authority`", "Cause\nund Context bleiben leer",
        "Authority-freie relative und absolute Dateipfade",
        "PostgreSQL benötigt Benutzer",
    ):
        assert value in document


def test_implementation_contract_preserves_structured_order_and_laziness() -> None:
    document = (ROOT / "docs/lq-582-fail-closed-sqlite-url-authority-boundary.md").read_text()
    for value in (
        "`username`, `password`, `host` und\n`port`", "1. URL", "2. Backend",
        "3. Treiber", "4. SQLite-Authority", "5. SQLite-Queryschlüssel",
        "6. Adapter-", "`create_engine` nicht aufgerufen", "kein globaler",
    ):
        assert value in document


def test_regression_record_covers_authority_order_and_preserved_paths() -> None:
    document = (ROOT / "docs/lq-583-sqlite-url-authority-boundary-regression.md").read_text()
    for value in (
        "leeren Benutzer mit Passwort", "Host allein", "Host mit Port",
        "`uri=true&mode=ro`", "Authority vor", "Beide In-Memory-Formen",
        "PostgreSQL/Psycopg-URL", "63 Tests", "-W error::DeprecationWarning",
    ):
        assert value in document


def test_completion_audit_records_full_green_matrix() -> None:
    document = (ROOT / "docs/lq-584-sqlite-url-authority-boundary-completion-audit.md").read_text()
    for value in (
        "5127 Tests", "einem erwarteten Skip",
        "105 `postgres_integration`-Tests", "5128", "66 Tests",
        "-W error::DeprecationWarning", "Authority-freie `sqlite://`-Engine",
        "`unsupported_database_url_authority`", "68 Console Entry Points",
        "69 Operator-Dateien", "42 Migrationen", "`20260826_0042`",
        "kein\nweiterer Slice",
    ):
        assert value in document


def test_roadmap_closes_sqlite_url_authority_bundle() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text()
    section = roadmap.split(
        "- LQ-584 SQLite URL authority boundary completion audit:", 1
    )[1].split("\n- LQ-192", 1)[0]
    for value in (
        "5127 normalen Tests", "105 PostgreSQL-Tests", "68/69/42",
        "20260826_0042", "kein weiterer Slice",
    ):
        assert value in section
