from pathlib import Path


ROOT = Path(__file__).parents[1]
DOC = (
    ROOT
    / "docs/lq-2746-staging-promotion-reconciliation-settings-installation-completion-audit.md"
)


def test_all_installation_strand_documents_exist_and_are_ordered() -> None:
    text = DOC.read_text(encoding="utf-8")
    for number in range(2740, 2746):
        assert len(list((ROOT / "docs").glob(f"lq-{number}-*.md"))) == 1
        assert f"LQ-{number}" in text
    assert "LQ-2740 through LQ-2745" in text


def test_audit_binds_cli_packaging_and_manual_runbook() -> None:
    text = DOC.read_text(encoding="utf-8")
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    runbook = (ROOT / "operations/runbooks/staging-promotion.md").read_text(
        encoding="utf-8"
    )
    command = "liquent-staging-promotion-reconciliation-settings-install"
    assert command in text and command in project and command in runbook
    assert "exactly one console entry point" in text
    assert "explicit manual runbook procedure" in text


def test_audit_preserves_ordered_no_replace_activation() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "never overwritten, truncated, removed or compared" in text
    assert "Both sources validate before target publication begins" in text
    assert "Provider publication precedes process publication" in text
    assert "process is the activation\n  record" in text
    assert "provider without a process target is inert" in text


def test_audit_closes_only_manual_installation_and_names_external_work() -> None:
    text = DOC.read_text(encoding="utf-8")
    for token in ("`installed`", "`present`", "`unavailable`", "`invalid_invocation`"):
        assert token in text
    assert "configuration readiness only" in text
    assert "cleanup, replacement, rotation, secret-manager integration" in text
    assert "closes only the manual reconciliation\nsettings-installation implementation strand" in text
    assert "changes no schema, migration, runtime behavior" in text
