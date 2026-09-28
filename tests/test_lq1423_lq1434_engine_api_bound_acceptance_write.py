import shutil

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport import manifest_handoff_supervisor_engine_api_staging_acceptance as registry_subject
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_acceptance import build_staging_run_acceptance
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_run import decode_staging_run_authority
from tests.test_lq1135_lq1146_engine_api_run_acceptance import roots
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as operation_subject
from tools.engine_api_joint_staging_operation_root import resolve_operation_root
from tools.engine_api_joint_staging_source_set import load_run_bound_source_set


def _material(tmp_path):
    source, registry = roots(tmp_path)
    snapshot = load_run_bound_source_set(source)
    value = build_staging_run_acceptance(decode_staging_run_authority(snapshot.run_authority), snapshot.run_envelope)
    identity = (registry.stat().st_dev, registry.stat().st_ino)
    return source, registry, value, identity


def test_record_accepts_exact_expected_registry_identity(tmp_path):
    _, registry, value, identity = _material(tmp_path)
    registry_subject.record_staging_run_acceptance(registry, value, expected_root_identity=identity)
    assert registry_subject.load_staging_run_acceptance(registry, value.run_id) == value


@pytest.mark.parametrize("expected", ((-1, 1), (True, 1), (1,), [1, 2], "1:2"))
def test_record_rejects_malformed_expected_registry_identity(tmp_path, expected):
    _, registry, value, _ = _material(tmp_path)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        registry_subject.record_staging_run_acceptance(registry, value, expected_root_identity=expected)
    assert list(registry.iterdir()) == []


def test_record_rejects_replaced_registry_before_marker_creation(tmp_path):
    _, registry, value, identity = _material(tmp_path)
    moved = registry.with_name("old-accepted-runs")
    registry.rename(moved)
    registry.mkdir(mode=0o700)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        registry_subject.record_staging_run_acceptance(registry, value, expected_root_identity=identity)
    assert list(registry.iterdir()) == []
    assert list(moved.iterdir()) == []


def test_one_shot_passes_expected_identity_to_record(tmp_path, monkeypatch):
    source, registry, _, identity = _material(tmp_path)
    observed = []
    original = accept_subject.record_staging_run_acceptance

    def recording(root, value, *, expected_root_identity=None):
        observed.append(expected_root_identity)
        return original(root, value, expected_root_identity=expected_root_identity)

    monkeypatch.setattr(accept_subject, "record_staging_run_acceptance", recording)
    monkeypatch.setattr(accept_subject, "_utc_now", lambda: NOW)
    accept_subject.verify_and_accept(source, registry, expected_acceptance_identity=identity)
    assert observed == [identity]


def test_operation_accept_passes_resolved_acceptance_identity(tmp_path, monkeypatch):
    root = operation_root(tmp_path)
    expected = resolve_operation_root(root).acceptance_identity
    observed = []
    original = operation_subject.verify_and_accept

    def recording(source, acceptance, *, expected_source_identity=None, expected_acceptance_identity=None):
        observed.append(expected_acceptance_identity)
        return original(source, acceptance, expected_source_identity=expected_source_identity, expected_acceptance_identity=expected_acceptance_identity)

    monkeypatch.setattr(operation_subject, "verify_and_accept", recording)
    monkeypatch.setattr(accept_subject, "_utc_now", lambda: NOW)
    operation_subject.accept_once(root)
    assert observed == [expected]


def test_operation_accept_rejects_registry_swap_before_inner_write(tmp_path, monkeypatch):
    root = operation_root(tmp_path)
    acceptance = root / "accepted-runs"
    moved = root / "old-accepted-runs"
    original = operation_subject.verify_and_accept

    def swapping(source, registry, *, expected_source_identity=None, expected_acceptance_identity=None):
        registry.rename(moved)
        registry.mkdir(mode=0o700)
        return original(source, registry, expected_source_identity=expected_source_identity, expected_acceptance_identity=expected_acceptance_identity)

    monkeypatch.setattr(operation_subject, "verify_and_accept", swapping)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        operation_subject.accept_once(root)
    assert list(acceptance.iterdir()) == []
    assert list(moved.iterdir()) == []


def test_same_content_registry_replacement_cannot_inherit_expected_identity(tmp_path):
    _, registry, value, identity = _material(tmp_path)
    moved = registry.with_name("old-accepted-runs")
    registry.rename(moved)
    shutil.copytree(moved, registry)
    registry.chmod(0o700)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        registry_subject.record_staging_run_acceptance(registry, value, expected_root_identity=identity)
