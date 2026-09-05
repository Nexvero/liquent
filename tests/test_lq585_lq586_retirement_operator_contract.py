from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_contract_has_minimal_request_current_authority_and_no_follow_on() -> None:
    document = (ROOT / "docs/lq-585-owner-controlled-supervisor-control-directory-retirement-operator-contract.md").read_text()
    for value in (
        "`liquent-supervisor-control-directory-retire`", "exakt\n`directory_id`",
        "keinen Actor", "keinen Actor", "aus dem System of Record",
        "`terminal_observed`", "`rejected`", "`operator_unavailable`",
        "Retirement startet keine Retentionevaluation", "nicht zur Bereinigung gelöscht",
    ):
        assert value in document


def test_implementation_contract_records_private_handoff_and_inventory() -> None:
    document = (ROOT / "docs/lq-586-owner-controlled-supervisor-control-directory-retirement-operator.md").read_text()
    for value in (
        "`--database-url-file`", "`--backend-instance-id-file`", "`--request`",
        "`--result-file`", "Readinessprüfung", "derselben Engine",
        "`fsync`", "atomarem Replace", "im `finally` freigegeben",
        "69 Console Entry Points", "70\nOperator-Pythondateien", "42",
        "`20260826_0042`",
    ):
        assert value in document


def test_operator_source_has_closed_input_and_no_cleanup_or_retention_call() -> None:
    source = (
        ROOT / "src/liquent_platform/operators/manifest_handoff_supervisor_control_directory_retirement.py"
    ).read_text()
    assert 'set(value) != {"directory_id"}' in source
    assert "PersistentManifestHandoffSupervisorControlDirectoryRetirement" in source
    assert "DatabaseReadinessProbe(engine).check().ready" in source
    assert "_write_result(args.result_file, result)" in source
    assert "engine.dispose()" in source
    for forbidden in (
        "SessionPrincipal", "UserId", "WorkspaceId", "allow:",
        "cleanup_control_directory(", "retention_operation", "record_cleanup_decision",
    ):
        assert forbidden not in source


def test_postgresql_evidence_records_retry_and_effect_free_rejection() -> None:
    document = (ROOT / "docs/lq-587-postgresql-supervisor-control-directory-retirement-evidence.md").read_text()
    for value in (
        "PostgreSQL-16-Instanz", "`20260826_0042`", "`launch_committed`",
        "`terminal_observed`", "Active auf Retired", "zweiter identischer Aufruf",
        "ohne Terminaltransition bleibt Active", "keinen SQLite-Fallback",
        "zwei PostgreSQL-Tests", "-W error::DeprecationWarning",
    ):
        assert value in document


def test_completion_audit_records_full_green_matrix_and_inventory() -> None:
    document = (ROOT / "docs/lq-588-supervisor-control-directory-retirement-operator-completion-audit.md").read_text()
    for value in (
        "5137 Tests", "einem erwarteten Skip", "107 Tests", "5138",
        "82 Tests", "-W error::DeprecationWarning",
        "`liquent-supervisor-control-directory-retire`",
        "69 Console Entry Points", "70\nOperator-Pythondateien",
        "42 Migrationen", "`20260826_0042`", "kein weiterer Slice",
    ):
        assert value in document


def test_roadmap_closes_retirement_operator_bundle() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text()
    section = roadmap.split(
        "- LQ-588 supervisor control-directory retirement operator completion audit:", 1
    )[1].split("\n- LQ-192", 1)[0]
    for value in (
        "5137 normalen Tests", "107 PostgreSQL-Tests", "69/70/42",
        "20260826_0042", "kein weiterer Slice",
    ):
        assert value in section
