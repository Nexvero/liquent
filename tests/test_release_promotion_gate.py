from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import pytest

from tools.validate_release_candidate import validate


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
MANIFEST_TOOL = ROOT / "tools" / "write_release_manifest.py"
REVISION = "a" * 40


def _quality_run(**updates: object) -> dict[str, object]:
    run: dict[str, object] = {
        "head_sha": REVISION,
        "head_branch": "main",
        "path": ".github/workflows/quality.yml",
        "event": "push",
        "status": "completed",
        "conclusion": "success",
    }
    run.update(updates)
    return {"workflow_runs": [run]}


def test_release_candidate_requires_successful_main_push_quality_run() -> None:
    validate(REVISION, "1.2.3", "PUBLISH", _quality_run())


@pytest.mark.parametrize(
    ("revision", "version", "confirmation", "updates"),
    [
        ("main", "1.2.3", "PUBLISH", {}),
        (REVISION, "v1.2.3", "PUBLISH", {}),
        (REVISION, "1.2.3", "yes", {}),
        (REVISION, "1.2.3", "PUBLISH", {"head_branch": "feature"}),
        (REVISION, "1.2.3", "PUBLISH", {"event": "pull_request"}),
        (REVISION, "1.2.3", "PUBLISH", {"conclusion": "failure"}),
    ],
)
def test_invalid_or_unverified_release_candidate_is_rejected(
    revision: str, version: str, confirmation: str, updates: dict[str, object]
) -> None:
    with pytest.raises(ValueError):
        validate(revision, version, confirmation, _quality_run(**updates))


def test_release_workflow_is_manual_gated_and_does_not_deploy() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in workflow
    assert "if: github.ref == 'refs/heads/main'" in workflow
    assert "environment: registry-release" in workflow
    assert "confirmation" in workflow
    assert "git merge-base --is-ancestor" in workflow
    assert "validate_release_candidate.py" in workflow
    assert "packages: write" in workflow
    assert "attestations: write" in workflow
    assert "push-to-registry: true" in workflow
    assert "ssh " not in workflow
    assert "57.131.130.107" not in workflow


def test_release_scans_before_registry_authentication_and_push() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    scan = workflow.index("Fail on high or critical release vulnerabilities")
    login = workflow.index("Authenticate to GHCR only after all gates")
    push = workflow.index('docker push "${IMAGE_REF}"')
    assert scan < login < push
    assert "only-fixed: true" in workflow
    assert "severity-cutoff: high" in workflow


def test_release_uses_commit_qualified_tag_and_digest_attestation() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert '${RELEASE_VERSION}-${REVISION}' in workflow
    assert "subject-digest: ${{ env.IMAGE_DIGEST }}" in workflow
    assert "subject-name: ${{ env.IMAGE_NAME }}" in workflow
    assert re.search(r"\^sha256:\[0-9a-f\]\{64\}\$", workflow)


def test_all_release_actions_are_commit_sha_pinned() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    actions = re.findall(r"uses:\s+([^\s#]+)", workflow)
    assert actions
    assert all(re.fullmatch(r"[0-9a-f]{40}", action.rsplit("@", 1)[1]) for action in actions)


def test_release_manifest_binds_revision_image_digest_and_sbom(tmp_path: Path) -> None:
    sbom = tmp_path / "sbom.json"
    sbom.write_text('{"spdxVersion":"SPDX-2.3"}\n', encoding="utf-8")
    output = tmp_path / "manifest.json"
    digest = "sha256:" + "b" * 64
    subprocess.run(
        [
            sys.executable,
            str(MANIFEST_TOOL),
            "--revision", REVISION,
            "--version", "1.2.3",
            "--image", "ghcr.io/nexvero/liquent",
            "--digest", digest,
            "--sbom", str(sbom),
            "--output", str(output),
        ],
        check=True,
    )
    manifest = json.loads(output.read_text(encoding="utf-8"))
    assert manifest["revision"] == REVISION
    assert manifest["image_digest"] == digest
    assert manifest["sbom_sha256"] == hashlib.sha256(sbom.read_bytes()).hexdigest()
