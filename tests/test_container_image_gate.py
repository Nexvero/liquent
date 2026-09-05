from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "Dockerfile"
DOCKERIGNORE = ROOT / ".dockerignore"
SMOKE = ROOT / "operations" / "container" / "smoke-test.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "quality.yml"


def test_base_image_is_versioned_and_digest_pinned() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    match = re.search(r"ARG PYTHON_IMAGE=(python:[^\s]+@sha256:[0-9a-f]{64})", dockerfile)
    assert match
    assert match.group(1) == (
        "python:3.13.15-slim-trixie@"
        "sha256:9d2e5553305c7c7b0097999bb17187c69b921ccd6bc9d40e4bb5ebe652c00285"
    )
    assert ":latest" not in dockerfile


def test_runtime_is_non_root_and_has_liveness_healthcheck() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    assert "USER 10001:10001" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "/health/live" in dockerfile
    assert 'CMD ["liquent-control-plane"]' in dockerfile
    assert "ENTRYPOINT" not in dockerfile


def test_image_build_uses_locked_nonisolated_wheel() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    assert "--constraint requirements/ci.lock" in dockerfile
    assert "python -m build --wheel --no-isolation" in dockerfile
    assert "COPY --from=builder /wheelhouse /wheelhouse" in dockerfile
    assert "/wheelhouse/liquent-*.whl" in dockerfile
    assert "/tmp/liquent.whl" not in dockerfile


def test_build_context_excludes_sensitive_and_nonruntime_content() -> None:
    ignored = set(DOCKERIGNORE.read_text(encoding="utf-8").splitlines())
    assert {".git", ".venv", "operations", "tests", "docs", "data/raw", "data/processed"} <= ignored
    assert {"*.env", "*.key", "*.pem"} <= ignored


def test_smoke_test_enforces_hardened_runtime_and_cleans_up() -> None:
    smoke = SMOKE.read_text(encoding="utf-8")
    for contract in ("--read-only", "--cap-drop ALL", "no-new-privileges:true", "trap cleanup", "docker rm --force"):
        assert contract in smoke
    assert "/health/live" in smoke


def test_container_gate_runs_only_after_verified_wheel() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "container:\n    needs: wheel" in workflow
    assert "operations/container/smoke-test.sh" in workflow
    assert "{{index .Config.Labels \\\"" not in workflow
    assert '{{index .Config.Labels "org.opencontainers.image.revision"}}' in workflow
    assert "Summarize blocking vulnerability findings" in workflow
    assert "failure() && hashFiles('dist/grype-results.json') != ''" in workflow
    for field in (".artifact.name", ".artifact.version", ".vulnerability.id", ".vulnerability.fix.versions"):
        assert field in workflow
    assert "if-no-files-found: warn" in workflow
    assert "docker push" not in workflow
    assert "packages: write" not in workflow
