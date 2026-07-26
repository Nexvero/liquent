from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "quality.yml"
LOCK = ROOT / "requirements" / "ci.lock"
VERIFIER = ROOT / "tools" / "verify_release_wheel.py"


def test_workflow_is_read_only_bounded_and_uses_explicit_python() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "permissions:\n  contents: read" in workflow
    assert 'python-version: "3.12"' in workflow
    assert "timeout-minutes:" in workflow
    assert "persist-credentials: false" in workflow
    assert "secrets." not in workflow


def test_all_external_actions_are_pinned_to_full_commit_sha() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    actions = re.findall(r"uses:\s+([^\s#]+)", workflow)
    assert actions
    for action in actions:
        reference = action.rsplit("@", 1)[1]
        assert re.fullmatch(r"[0-9a-f]{40}", reference), action


def test_ci_uses_lock_for_install_and_nonisolated_build() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert workflow.count("--constraint requirements/ci.lock") == 4
    assert workflow.count("--no-build-isolation") == 2
    assert "python -m build --wheel --no-isolation" in workflow
    assert "SOURCE_DATE_EPOCH=" in workflow


def test_lock_contains_only_exact_stable_registry_versions() -> None:
    lines = [
        line.strip()
        for line in LOCK.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    assert len(lines) >= 25
    assert all(re.fullmatch(r"[A-Za-z0-9_.-]+==[A-Za-z0-9_.+-]+", line) for line in lines)
    assert not any("dev" in line.lower() or "rc" in line.lower() for line in lines)
    assert len({line.split("==", 1)[0].lower() for line in lines}) == len(lines)


def test_wheel_verifier_requires_runtime_entrypoints_and_migrations() -> None:
    verifier = VERIFIER.read_text(encoding="utf-8")
    for term in (
        "liquent-control-plane",
        "liquent-health-check",
        "liquent-migrate",
        "20260726_0001_platform_baseline.py",
        "FORBIDDEN_NAME_PARTS",
        "sha256",
    ):
        assert term in verifier


def test_verified_wheel_is_uploaded_only_after_tests() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "wheel:\n    needs: test" in workflow
    assert "if-no-files-found: error" in workflow
    assert "retention-days: 14" in workflow
