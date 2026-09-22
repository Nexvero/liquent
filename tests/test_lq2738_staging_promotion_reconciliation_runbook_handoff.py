from pathlib import Path


ROOT = Path(__file__).parents[1]
RUNBOOK = ROOT / "operations/runbooks/staging-promotion.md"
DOC = ROOT / "docs/lq-2738-staging-promotion-reconciliation-runbook-handoff.md"


def test_runbook_keeps_reconciliation_separate_and_manual() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    section = text[text.index("## Research-index unknown-effect reconciliation") :]
    assert "separate, manual recovery action" in section
    assert "Do not run it during the normal" in section
    assert "unknown-effect attempt" in section
    assert "new explicit\noperator decision" in section


def test_runbook_names_exact_private_settings_projection() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    assert "LIQUENT_STAGING_PROMOTION_PROVIDER_ENDPOINT=" in text
    assert (
        "LIQUENT_STAGING_PROMOTION_RECONCILIATION_PROVIDER_SETTINGS_FILE=" in text
    )
    assert "LIQUENT_STAGING_PROMOTION_RECONCILIATION_DATABASE_URL=" in text
    assert "mode `0600`" in text
    assert "one hard link" in text


def test_runbook_uses_exact_command_and_closed_outcomes() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    assert (
        "liquent-staging-promotion-reconcile /ABSOLUTE/PROCESS_SETTINGS" in text
    )
    for token in ("`idle`", "`reconciled`", "`unavailable`", "`invalid_invocation`"):
        assert token in text
    assert "do not retry automatically" in text


def test_slice_document_preserves_non_automating_boundary() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "operator-facing handoff" in text
    assert "does not\ngrant promotion authority" in text
    assert "no settings file, credential, secret, default path" in text
    assert "Production triggering remains\noutside this slice" in text
