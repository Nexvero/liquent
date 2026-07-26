from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "lq-069-release-environment-governance.md"
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"


def test_release_environment_governance_is_explicit() -> None:
    document = DOC.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "registry-release" in document
    assert "Branch pattern | `main`" in document
    assert "Environment secrets | 0" in document
    assert "Required Reviewers sind derzeit nicht aktiviert" in document
    assert "kein Release oder Deployment wurde ausgelöst" in document
    assert "environment: registry-release" in workflow


def test_environment_governance_preserves_manual_release_boundary() -> None:
    document = DOC.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")

    for guard in ("workflow_dispatch:", "revision:", "version:", "confirmation:"):
        assert guard in workflow
    assert "PUBLISH" in workflow
    assert "erster GHCR-Release benötigt weiterhin ausdrückliche Freigabe" in document
    assert "VPS-Deployment" in document
