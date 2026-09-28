from pathlib import Path


ROOT = Path(__file__).parents[1]
DOC = ROOT / "docs/lq-2739-staging-promotion-reconciliation-completion-audit.md"


def test_all_reconciliation_strand_documents_exist_and_are_ordered() -> None:
    text = DOC.read_text(encoding="utf-8")
    for number in range(2712, 2740):
        documents = list((ROOT / "docs").glob(f"lq-{number}-*.md"))
        assert len(documents) == 1
    groups = (
        "LQ-2712 through LQ-2738",
        "LQ-2718 through LQ-2723",
        "LQ-2724 through LQ-2727",
        "LQ-2728 through LQ-2730",
        "LQ-2731 through LQ-2734",
        "LQ-2735 and LQ-2736",
        "LQ-2737",
        "LQ-2738",
    )
    assert all(group in text for group in groups)


def test_audit_binds_cli_packaging_and_manual_runbook() -> None:
    text = DOC.read_text(encoding="utf-8")
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    runbook = (
        ROOT / "operations/runbooks/staging-promotion.md"
    ).read_text(encoding="utf-8")
    command = "liquent-staging-promotion-reconcile"
    assert command in text and command in project and command in runbook
    assert "explicit manual runbook procedure" in text
    assert "at most one candidate" in text


def test_audit_preserves_closed_observable_outcomes() -> None:
    text = DOC.read_text(encoding="utf-8")
    cli = (
        ROOT
        / "src/liquent_platform/transport"
        / "staging_research_index_promotion_reconciliation_cli.py"
    ).read_text(encoding="utf-8")
    for token in ("idle", "reconciled", "unavailable", "invalid_invocation"):
        assert token in text or token in cli
        assert f'"{token}\\n"' in cli
    assert "contains no internal retry loop" in text
    assert "grants no deployment or\npromotion authority" in text


def test_audit_closes_only_manual_strand_and_names_later_work() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "timer, service, worker, alert-driven\ntrigger" in text
    assert "automatic retry, bulk drain or deployment integration" in text
    assert "closes only the manual reconciliation\nimplementation strand" in text
    assert "changes no schema, migration, runtime behavior" in text
