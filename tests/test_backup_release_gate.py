from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "backup-release.yml"


def test_backup_release_is_manual_main_gated_and_non_deploying() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    for guard in ("workflow_dispatch:", "revision:", "version:", "confirmation:"):
        assert guard in workflow
    assert "if: github.ref == 'refs/heads/main'" in workflow
    assert "environment: registry-release" in workflow
    assert "validate_release_candidate.py" in workflow
    assert "git merge-base --is-ancestor" in workflow
    assert "ssh " not in workflow
    assert "docker compose" not in workflow


def test_backup_release_rebuilds_and_smokes_before_registry_authentication() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    build = workflow.index("Build backup image from verified commit")
    smoke = workflow.index("Run hardened backup smoke test")
    scan = workflow.index("Fail on high or critical backup image vulnerabilities")
    login = workflow.index("Authenticate to GHCR only after all gates")
    push = workflow.index('docker push "${IMAGE_REF}"')
    assert build < smoke < scan < login < push
    assert "--file Dockerfile.backup" in workflow
    assert "backup-smoke-test.sh" in workflow
    assert "only-fixed: true" in workflow
    assert "severity-cutoff: high" in workflow


def test_backup_release_uses_immutable_identity_and_evidence() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "ghcr.io/nexvero/liquent-backup" in workflow
    assert "${RELEASE_VERSION}-${REVISION}" in workflow
    assert re.search(r"\^sha256:\[0-9a-f\]\{64\}\$", workflow)
    assert "subject-digest: ${{ env.IMAGE_DIGEST }}" in workflow
    assert "push-to-registry: true" in workflow
    assert "backup-release-manifest.json" in workflow
    assert "retention-days: 30" in workflow


def test_backup_release_actions_are_commit_sha_pinned() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    actions = re.findall(r"uses:\s+([^\s#]+)", workflow)
    assert actions
    assert all(re.fullmatch(r"[0-9a-f]{40}", action.rsplit("@", 1)[1]) for action in actions)
