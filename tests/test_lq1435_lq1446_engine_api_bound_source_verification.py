import shutil

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1123_lq1134_engine_api_run_bound_root import run_root
from tests.test_lq1135_lq1146_engine_api_run_acceptance import roots
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as operation_subject
from tools import engine_api_joint_staging_source_set as source_subject
from tools.engine_api_joint_staging_operation_root import resolve_operation_root


def test_run_source_loader_accepts_exact_expected_identity(tmp_path):
    root = run_root(tmp_path)
    identity = (root.stat().st_dev, root.stat().st_ino)
    assert source_subject.load_run_bound_source_set(root, expected_root_identity=identity) is not None


@pytest.mark.parametrize("expected", ((-1, 1), (True, 1), (1,), [1, 2], "1:2"))
def test_run_source_loader_rejects_malformed_expected_identity(tmp_path, expected):
    root = run_root(tmp_path)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        source_subject.load_run_bound_source_set(root, expected_root_identity=expected)


def test_run_source_loader_rejects_same_content_replacement_identity(tmp_path):
    root = run_root(tmp_path)
    identity = (root.stat().st_dev, root.stat().st_ino)
    moved = root.with_name("old-source-set")
    root.rename(moved)
    shutil.copytree(moved, root)
    root.chmod(0o700)
    for path in root.iterdir():
        path.chmod(0o600)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        source_subject.load_run_bound_source_set(root, expected_root_identity=identity)


def test_one_shot_passes_expected_identity_to_both_source_loads(tmp_path, monkeypatch):
    source, registry = roots(tmp_path)
    identity = (source.stat().st_dev, source.stat().st_ino)
    acceptance_identity = (registry.stat().st_dev, registry.stat().st_ino)
    observed = []
    original = accept_subject.observe_run_bound_source_set

    def recording(root, *, expected_root_identity=None):
        observed.append(expected_root_identity)
        return original(root, expected_root_identity=expected_root_identity)

    monkeypatch.setattr(accept_subject, "observe_run_bound_source_set", recording)
    monkeypatch.setattr(accept_subject, "_utc_now", lambda: NOW)
    accept_subject.verify_and_accept(source, registry, expected_source_identity=identity, expected_acceptance_identity=acceptance_identity)
    assert observed == [identity, identity]


def test_operation_accept_passes_both_resolved_child_identities(tmp_path, monkeypatch):
    root = operation_root(tmp_path)
    expected = resolve_operation_root(root)
    observed = []
    original = operation_subject.verify_and_accept

    def recording(source, acceptance, *, expected_source_identity=None, expected_acceptance_identity=None):
        observed.append((expected_source_identity, expected_acceptance_identity))
        return original(source, acceptance, expected_source_identity=expected_source_identity, expected_acceptance_identity=expected_acceptance_identity)

    monkeypatch.setattr(operation_subject, "verify_and_accept", recording)
    monkeypatch.setattr(accept_subject, "_utc_now", lambda: NOW)
    operation_subject.accept_once(root)
    assert observed == [(expected.source_identity, expected.acceptance_identity)]


def test_operation_accept_rejects_source_swap_before_inner_verification(tmp_path, monkeypatch):
    root = operation_root(tmp_path)
    source = root / "source-set"
    acceptance = root / "accepted-runs"
    moved = root / "old-source-set"
    original = operation_subject.verify_and_accept

    def swapping(source_root, acceptance_root, **kwargs):
        source_root.rename(moved)
        shutil.copytree(moved, source_root)
        source_root.chmod(0o700)
        for path in source_root.iterdir():
            path.chmod(0o600)
        return original(source_root, acceptance_root, **kwargs)

    monkeypatch.setattr(operation_subject, "verify_and_accept", swapping)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        operation_subject.accept_once(root)
    assert list(acceptance.iterdir()) == []


def test_unbound_standalone_source_loading_remains_supported(tmp_path):
    root = run_root(tmp_path)
    assert source_subject.load_run_bound_source_set(root) is not None
