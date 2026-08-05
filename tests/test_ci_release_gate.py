from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "quality.yml"
LOCK = ROOT / "requirements" / "ci.lock"
PYPROJECT = ROOT / "pyproject.toml"
VERIFIER = ROOT / "tools" / "verify_release_wheel.py"


def _requirements(section: str) -> list[str]:
    """Return the requirement strings of one pyproject list, e.g. dependencies.

    The block ends at a ``]`` in the first column, because a requirement may
    itself contain brackets, as ``psycopg[binary]`` does.
    """

    text = PYPROJECT.read_text(encoding="utf-8")
    block = re.search(rf"^{section} = \[$(.*?)^\]$", text, re.MULTILINE | re.DOTALL)
    assert block is not None, section
    return re.findall(r'"([^"]+)"', block.group(1))


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


def test_oidc_verification_libraries_are_bounded_runtime_dependencies() -> None:
    """LQ-161: PyJWT needs the crypto extra, and httpx2 moved out of dev."""

    runtime = _requirements("dependencies")
    dev = _requirements("dev")

    pyjwt = [r for r in runtime if r.lower().startswith("pyjwt")]
    assert pyjwt, "PyJWT must be a runtime dependency"
    # The extra is what pulls the maintained cryptography implementation;
    # bare PyJWT cannot verify asymmetric signatures.
    assert "[crypto]" in pyjwt[0]

    assert any(r.lower().startswith("httpx2") for r in runtime)
    # Runtime only — never declared twice.
    assert not any(r.lower().startswith("httpx2") for r in dev)


def test_runtime_dependencies_are_registry_versions_with_an_upper_bound() -> None:
    for requirement in _requirements("dependencies"):
        # A PEP 508 direct reference is "name @ url"; a package may legitimately
        # be named httpx2, so the scheme is what identifies a URL, not a prefix.
        assert "@" not in requirement, requirement
        assert "://" not in requirement, requirement
        assert ">=" in requirement and "<" in requirement, requirement
        assert not re.search(r"(rc|a|b|dev)\d", requirement), requirement


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
