from __future__ import annotations

from pathlib import Path
import re
import tomllib

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "quality.yml"
LOCK = ROOT / "requirements" / "ci.lock"
PYPROJECT = ROOT / "pyproject.toml"
VERIFIER = ROOT / "tools" / "verify_release_wheel.py"


def _pyproject() -> dict:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def _find(requirements: list[str], name: str) -> Requirement | None:
    """Return one parsed requirement by canonical distribution name."""

    for raw in requirements:
        parsed = Requirement(raw)
        if canonicalize_name(parsed.name) == canonicalize_name(name):
            return parsed
    return None


def _runtime(name: str) -> Requirement | None:
    return _find(_pyproject()["project"]["dependencies"], name)


def _dev(name: str) -> Requirement | None:
    return _find(_pyproject()["project"]["optional-dependencies"]["dev"], name)


def _locked_names() -> set[str]:
    return {
        line.split("==", 1)[0].lower()
        for line in LOCK.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }


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


def test_pyjwt_is_a_bounded_runtime_dependency_with_the_crypto_extra() -> None:
    """LQ-161. Scoped to PyJWT: this is not a policy for every dependency."""

    pyjwt = _runtime("PyJWT")

    assert pyjwt is not None, "PyJWT must be a runtime dependency"
    # The extra is what pulls the maintained cryptography implementation;
    # bare PyJWT cannot verify asymmetric signatures.
    assert pyjwt.extras == {"crypto"}
    assert pyjwt.url is None
    assert {specifier.operator for specifier in pyjwt.specifier} >= {">=", "<"}
    assert not any(Version(s.version).is_prerelease for s in pyjwt.specifier)


def test_httpx2_is_a_bounded_runtime_dependency() -> None:
    """LQ-161. Scoped to httpx2, which moved out of the dev extra."""

    httpx2 = _runtime("httpx2")

    assert httpx2 is not None, "httpx2 must be a runtime dependency"
    assert httpx2.url is None
    assert {specifier.operator for specifier in httpx2.specifier} >= {">=", "<"}
    assert not any(Version(s.version).is_prerelease for s in httpx2.specifier)


def test_the_verification_libraries_are_not_also_declared_for_dev() -> None:
    """httpx2 moved rather than being duplicated, and PyJWT is runtime only."""

    assert _dev("httpx2") is None
    assert _dev("PyJWT") is None


def test_verification_libraries_and_their_crypto_chain_are_locked() -> None:
    """Exact pins and stability are enforced centrally; only coverage here."""

    assert {"pyjwt", "httpx2", "cryptography", "cffi", "pycparser"} <= _locked_names()


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
