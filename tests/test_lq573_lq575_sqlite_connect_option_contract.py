from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_contract_distinguishes_pool_busy_and_caller_options() -> None:
    document = (ROOT / "docs/lq-573-sqlite-connect-option-precedence-contract.md").read_text()
    for value in (
        "`PRAGMA busy_timeout=5000`", "Pool-Timeout", "DBAPI-/Busy-Timeout",
        "`check_same_thread=False`", "dürfen die zentralen Werte nicht überschreiben",
        "`connect_timeout=3`", "keine Retrylogik",
    ):
        assert value in document


def test_implementation_contract_preserves_dialect_and_laziness() -> None:
    document = (ROOT / "docs/lq-574-central-sqlite-connect-options.md").read_text()
    for value in (
        '`connect_args={"timeout": 5}`', "`StaticPool`", "Max-Overflow 2",
        "`check_same_thread=False` und `timeout=5`",
        '`connect_args={"connect_timeout": 3}`', "öffnet weiterhin keine Verbindung",
    ):
        assert value in document


def test_regression_record_covers_actual_and_factory_boundaries() -> None:
    document = (ROOT / "docs/lq-575-sqlite-connect-option-precedence-regression.md").read_text()
    for value in (
        "`timeout=0.001`", "`PRAGMA busy_timeout=5000`", "`timeout=99`",
        "`check_same_thread=true`", "anderer Thread", "`connect_timeout=99`",
        "32 Tests", "-W error::DeprecationWarning",
    ):
        assert value in document


def test_completion_audit_records_full_green_matrix() -> None:
    document = (ROOT / "docs/lq-576-sqlite-connect-option-precedence-completion-audit.md").read_text()
    for value in (
        "5095 Tests", "einem erwarteten Skip",
        "105 `postgres_integration`-Tests", "5096", "35 Tests",
        "-W error::DeprecationWarning", "`timeout=0.001`",
        "`check_same_thread=true`", "`PRAGMA busy_timeout=5000`",
        "68 Console Entry Points", "69 Operator-Dateien", "42 Migrationen",
        "`20260826_0042`", "kein\nweiterer Slice",
    ):
        assert value in document


def test_roadmap_closes_sqlite_connect_option_bundle() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text()
    section = roadmap.split(
        "- LQ-576 SQLite connect-option precedence completion audit:", 1
    )[1].split("\n- LQ-192", 1)[0]
    for value in (
        "5095 normalen Tests", "105 PostgreSQL-Tests", "68/69/42",
        "20260826_0042", "kein weiterer Slice",
    ):
        assert value in section
