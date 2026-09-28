import shutil

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_operation_verify as subject


def test_successful_inner_operation_is_revalidated(tmp_path, monkeypatch):
    root = operation_root(tmp_path)
    calls = []
    original = subject.validate_operation_roots

    def recording(path, expected):
        calls.append((path, expected))
        return original(path, expected)

    monkeypatch.setattr(subject, "validate_operation_roots", recording)
    value = subject._within_operation_roots(root, lambda resolved: resolved.root_identity)
    assert value == calls[0][1].root_identity
    assert calls[0][0] == root


def test_failed_inner_operation_is_still_revalidated(tmp_path, monkeypatch):
    root = operation_root(tmp_path)
    calls = []
    original = subject.validate_operation_roots

    def recording(path, expected):
        calls.append((path, expected))
        return original(path, expected)

    monkeypatch.setattr(subject, "validate_operation_roots", recording)
    with pytest.raises(RuntimeError, match="inner failure"):
        subject._within_operation_roots(root, lambda resolved: (_ for _ in ()).throw(RuntimeError("inner failure")))
    assert len(calls) == 1


@pytest.mark.parametrize("target", ("root", "source", "acceptance"))
def test_failure_path_rejects_operation_boundary_replacement(tmp_path, target):
    root = operation_root(tmp_path)

    def failing(resolved):
        if target == "root":
            moved = tmp_path / "old-operation"
            root.rename(moved)
            root.mkdir(mode=0o700)
            shutil.copytree(moved / "source-set", root / "source-set")
            (root / "accepted-runs").mkdir(mode=0o700)
        else:
            name = "source-set" if target == "source" else "accepted-runs"
            path = root / name
            moved = root / (name + "-old")
            path.rename(moved)
            if target == "source":
                shutil.copytree(moved, path)
            else:
                path.mkdir(mode=0o700)
        raise RuntimeError("inner failure")

    with pytest.raises(ManifestHandoffRegistryUnavailable):
        subject._within_operation_roots(root, failing)


def test_accept_once_revalidates_when_verification_fails(tmp_path, monkeypatch):
    root = operation_root(tmp_path)
    validated = []
    original = subject.validate_operation_roots

    def fail(source, acceptance, **kwargs):
        raise ManifestHandoffRegistryUnavailable

    def recording(path, expected, **kwargs):
        validated.append(expected)
        return original(path, expected, **kwargs)

    monkeypatch.setattr(subject, "verify_and_accept", fail)
    monkeypatch.setattr(subject, "validate_operation_roots", recording)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        subject.accept_once(root)
    assert len(validated) == 1


@pytest.mark.parametrize("accepted_source", (False, True))
def test_each_audit_mode_revalidates_when_audit_fails(tmp_path, monkeypatch, accepted_source):
    root = operation_root(tmp_path)
    validated = []
    original = subject.validate_operation_roots

    def fail(*args, **kwargs):
        raise ManifestHandoffRegistryUnavailable

    def recording(path, expected):
        validated.append(expected)
        return original(path, expected)

    monkeypatch.setattr(subject, "inspect_registry", fail)
    monkeypatch.setattr(subject, "verify_accepted_current", fail)
    monkeypatch.setattr(subject, "validate_operation_roots", recording)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        subject.audit(root, accepted_source=accepted_source)
    assert len(validated) == 1


def test_cli_keeps_failure_detail_closed_after_final_revalidation(tmp_path, monkeypatch):
    root = operation_root(tmp_path)
    monkeypatch.setattr(subject, "verify_and_accept", lambda *args: (_ for _ in ()).throw(RuntimeError("secret detail")))
    assert subject.main(["--operation-root", str(root), "--mode", "accept-once"]) == 2
