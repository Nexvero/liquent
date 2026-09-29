from pathlib import Path


ROOT = Path(__file__).parents[1]
DOC = (
    ROOT
    / "docs/lq-2760-staging-promotion-reconciliation-acceptance-completion-audit.md"
)


def test_acceptance_strand_documents_are_complete_and_ordered() -> None:
    text = DOC.read_text(encoding="utf-8")
    for number in range(2750, 2760):
        documents = list((ROOT / "docs").glob(f"lq-{number}-*.md"))
        assert len(documents) == 1
        assert f"LQ-{number}" in text
    assert "LQ-2750 through LQ-2759" in text


def test_audit_binds_all_installed_manual_commands_to_the_runbook() -> None:
    text = DOC.read_text(encoding="utf-8")
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    runbook = (
        ROOT / "operations/runbooks/staging-promotion.md"
    ).read_text(encoding="utf-8")
    commands = (
        "liquent-staging-promotion-reconciliation-settings-install",
        "liquent-staging-promotion-reconciliation-readiness-audit",
        "liquent-staging-promotion-reconciliation-candidate-audit",
        "liquent-staging-promotion-reconcile",
    )
    for command in commands:
        assert command in text
        assert command in project
        assert command in runbook
    assert "exactly one entry point for each manual boundary" in text


def test_audit_closes_positive_and_failure_acceptance_matrix() -> None:
    text = DOC.read_text(encoding="utf-8")
    for phrase in (
        "`installed` -> `ready` -> `pending` -> `reconciled` -> `idle`",
        "provider HTTP and decoder failures",
        "owner-private settings tamper",
        "database unavailability",
        "schema-revision mismatch",
        "dedicated real\n    PostgreSQL database",
        "independent database engine",
        "exactly one provider request",
    ):
        assert phrase in text


def test_audit_preserves_closed_authority_and_names_external_work() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "does not authorize that exercise, another reconciliation, promotion or\ndeployment" in text
    assert "monitoring, scheduling, automatic retry, bulk draining" in text
    assert "adds tests and documentation only" in text
    assert "changes no production code,\nschema, migration, command, route, trigger" in text
    assert "closes only the manual reconciliation acceptance strand" in text
