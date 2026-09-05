import shutil

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1135_lq1146_engine_api_run_acceptance import roots
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as operation_subject


def _identities(source, registry):
    return (source.stat().st_dev, source.stat().st_ino), (registry.stat().st_dev, registry.stat().st_ino)


def test_one_shot_passes_acceptance_identity_to_both_marker_reads(tmp_path, monkeypatch):
    source, registry = roots(tmp_path)
    source_identity, acceptance_identity = _identities(source, registry)
    observed = []
    original = accept_subject.load_staging_run_acceptance

    def recording(root, run_id, *, expected_root_identity=None):
        observed.append(expected_root_identity)
        return original(root, run_id, expected_root_identity=expected_root_identity)

    monkeypatch.setattr(accept_subject, "load_staging_run_acceptance", recording)
    monkeypatch.setattr(accept_subject, "_utc_now", lambda: NOW)
    accept_subject.verify_and_accept(source, registry, expected_source_identity=source_identity, expected_acceptance_identity=acceptance_identity)
    assert observed == [acceptance_identity, acceptance_identity]


def test_bound_duplicate_precheck_rejects_registry_replacement(tmp_path):
    source, registry = roots(tmp_path)
    source_identity, acceptance_identity = _identities(source, registry)
    moved = registry.with_name("old-accepted-runs")
    registry.rename(moved)
    shutil.copytree(moved, registry)
    registry.chmod(0o700)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        accept_subject.verify_and_accept(source, registry, expected_source_identity=source_identity, expected_acceptance_identity=acceptance_identity)
    assert list(registry.iterdir()) == []


def test_bound_readback_rejects_registry_replacement_after_record(tmp_path, monkeypatch):
    source, registry = roots(tmp_path)
    source_identity, acceptance_identity = _identities(source, registry)
    moved = registry.with_name("old-accepted-runs")
    original = accept_subject.record_staging_run_acceptance

    def record_then_replace(root, value, **kwargs):
        result = original(root, value, **kwargs)
        root.rename(moved)
        shutil.copytree(moved, root)
        root.chmod(0o700)
        for marker in root.iterdir():
            marker.chmod(0o600)
        return result

    monkeypatch.setattr(accept_subject, "record_staging_run_acceptance", record_then_replace)
    monkeypatch.setattr(accept_subject, "_utc_now", lambda: NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        accept_subject.verify_and_accept(source, registry, expected_source_identity=source_identity, expected_acceptance_identity=acceptance_identity)


def test_operation_accept_rejects_replacement_before_duplicate_precheck(tmp_path, monkeypatch):
    root = operation_root(tmp_path)
    registry = root / "accepted-runs"
    moved = root / "old-accepted-runs"
    original = operation_subject.verify_and_accept

    def replacing(source, acceptance, **kwargs):
        acceptance.rename(moved)
        shutil.copytree(moved, acceptance)
        acceptance.chmod(0o700)
        return original(source, acceptance, **kwargs)

    monkeypatch.setattr(operation_subject, "verify_and_accept", replacing)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        operation_subject.accept_once(root)
    assert list(registry.iterdir()) == []


def test_unbound_one_shot_marker_reads_remain_supported(tmp_path, monkeypatch):
    source, registry = roots(tmp_path)
    monkeypatch.setattr(accept_subject, "_utc_now", lambda: NOW)
    accept_subject.verify_and_accept(source, registry)
    assert len(list(registry.iterdir())) == 1
