from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]


def _source(name: str) -> str:
    package_local = {
        "private_manifest_handoff.py",
        "private_manifest_handoff_reconcile.py",
    }
    root = (
        ROOT / "src/liquent_platform/capabilities"
        if name in package_local else ROOT / "tools"
    )
    return (root / name).read_text(encoding="utf-8")


def _calls(name: str) -> list[tuple[str | None, str]]:
    tree = ast.parse(_source(name))
    calls: list[tuple[str | None, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute):
            owner = node.func.value.id if isinstance(node.func.value, ast.Name) else None
            calls.append((owner, node.func.attr))
        elif isinstance(node.func, ast.Name):
            calls.append((None, node.func.id))
    return calls


def test_chain_has_one_contract_and_test_per_slice() -> None:
    expected = {
        425: (
            "docs/lq-425-owner-controlled-private-pre-staging-manifest-handoff-contract.md",
            "tests/test_lq425_private_manifest_handoff_contract.py",
        ),
        426: (
            "docs/lq-426-owner-controlled-private-manifest-writer.md",
            "tests/test_lq426_private_manifest_handoff.py",
        ),
        427: (
            "docs/lq-427-read-only-private-manifest-handoff-reconciliation.md",
            "tests/test_lq427_private_manifest_handoff_reconcile.py",
        ),
        428: (
            "docs/lq-428-owner-controlled-private-manifest-handoff-cleanup.md",
            "tests/test_lq428_private_manifest_handoff_cleanup.py",
        ),
        429: (
            "docs/lq-429-private-manifest-handoff-completion-audit.md",
            "tests/test_lq429_private_manifest_handoff_completion_audit.py",
        ),
    }
    for number, paths in expected.items():
        assert all((ROOT / path).is_file() for path in paths), number


def test_mutation_budget_is_separated() -> None:
    writer_calls = _calls("private_manifest_handoff.py")
    reconcile_calls = _calls("private_manifest_handoff_reconcile.py")
    cleanup_calls = _calls("private_manifest_handoff_cleanup.py")
    mutators = {"link", "unlink", "rename", "replace", "remove", "chmod", "fchmod"}

    assert ("os", "link") in writer_calls
    assert ("os", "fchmod") in writer_calls
    assert not any(owner == "os" and call in mutators for owner, call in reconcile_calls)
    assert [(owner, call) for owner, call in cleanup_calls if owner == "os" and call in mutators] == [
        ("os", "unlink")
    ]


def test_outcomes_and_non_authorization_remain_explicit() -> None:
    writer = _source("private_manifest_handoff.py")
    reconciler = _source("private_manifest_handoff_reconcile.py")
    cleanup = _source("private_manifest_handoff_cleanup.py")
    for outcome in (
        "manifest_absent",
        "manifest_handed_off",
        "manifest_temporary_only",
        "manifest_handed_off_pending_cleanup",
        "manifest_handoff_conflict",
    ):
        assert outcome in reconciler
    assert "manifest_handoff_outcome_unknown" in writer
    assert "manifest_handoff_cleanup_outcome_unknown" in cleanup
    for source in (writer, reconciler, cleanup):
        assert '"commit_authorized": False' in source
        assert '"staging_authorized": False' in source


def test_attempt_and_retention_gaps_stay_open() -> None:
    audit = (ROOT / "docs/lq-429-private-manifest-handoff-completion-audit.md").read_text(
        encoding="utf-8"
    )
    assert "Abwesenheit keine Namenswiederverwendung autorisieren" in audit
    assert "LQ-429 entscheidet weder Speichertechnik noch Schema" in audit
    assert "Writerabschluss und Tempcleanup beenden ihre Retention nicht" in audit
    assert "keine Frist, Ablage, Archivierung oder Löschoberfläche" in audit


def test_roadmap_links_audit_without_entry_point() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "- LQ-429 private manifest handoff completion audit:" in roadmap
    assert "`docs/lq-429-private-manifest-handoff-completion-audit.md`" in roadmap
    assert "nächster Slice LQ-430" in roadmap
    assert "private-manifest-handoff-audit" not in project
