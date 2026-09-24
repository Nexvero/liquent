from pathlib import Path


ROOT = Path(__file__).parents[1]
RUNBOOK = ROOT / "operations/runbooks/staging-promotion.md"
DOC = (
    ROOT
    / "docs/lq-2745-staging-promotion-reconciliation-settings-installation-runbook-handoff.md"
)


def _section() -> str:
    text = RUNBOOK.read_text(encoding="utf-8")
    start = text.index("### Install reconciliation settings")
    end = text.index("This is a separate, manual recovery action", start)
    return text[start:end]


def test_runbook_uses_exact_installed_command_and_argument_order() -> None:
    section = _section()
    assert (
        "liquent-staging-promotion-reconciliation-settings-install "
        "/ABSOLUTE/PROVIDER_SOURCE /ABSOLUTE/PROVIDER_TARGET "
        "/ABSOLUTE/PROCESS_SOURCE /ABSOLUTE/PROCESS_TARGET" in section
    )
    assert "four explicit absolute paths in this fixed order" in section


def test_runbook_preserves_private_no_replace_installation_boundary() -> None:
    section = _section()
    assert "mode `0600`, exactly\none hard link" in section
    assert "not writable\nby group or others" in section
    assert "process source must name the exact provider target" in section
    assert "no existing content was compared or replaced" in section
    assert "Do not remove or overwrite a retained provider target" in section


def test_runbook_presents_only_closed_results_and_requires_new_decision() -> None:
    section = _section()
    for token in ("`installed`", "`present`", "`unavailable`", "`invalid_invocation`"):
        assert token in section
    for code in ("`0`", "`1`", "`2`", "`3`"):
        assert code in section
    assert "do not retry automatically" in section
    assert "make a new explicit operator decision" in section


def test_slice_document_preserves_manual_non_authorizing_boundary() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "separate manual preparation action" in text
    assert "does\nnot grant promotion authority" in text
    assert "adds no settings value, credential, secret, default path" in text
    assert "Production triggering remains outside this\nslice" in text
