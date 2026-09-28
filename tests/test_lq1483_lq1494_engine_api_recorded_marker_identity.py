import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport import manifest_handoff_supervisor_engine_api_staging_acceptance as registry_subject
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_acceptance import build_staging_run_acceptance
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_run import decode_staging_run_authority
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1123_lq1134_engine_api_run_bound_root import RUN
from tests.test_lq1135_lq1146_engine_api_run_acceptance import roots
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools.engine_api_joint_staging_source_set import load_run_bound_source_set


def _material(tmp_path):
    source, registry = roots(tmp_path)
    snapshot = load_run_bound_source_set(source)
    acceptance = build_staging_run_acceptance(decode_staging_run_authority(snapshot.run_authority), snapshot.run_envelope)
    return source, registry, acceptance


def test_record_returns_descriptor_bound_marker_observation(tmp_path):
    _, registry, acceptance = _material(tmp_path)
    observed = registry_subject.record_staging_run_acceptance(registry, acceptance)
    marker = registry / (RUN + ".accepted")
    assert observed.acceptance == acceptance
    assert observed.marker_identity == (marker.stat().st_dev, marker.stat().st_ino)


def test_bound_record_observation_preserves_registry_identity_check(tmp_path):
    _, registry, acceptance = _material(tmp_path)
    identity = (registry.stat().st_dev, registry.stat().st_ino)
    observed = registry_subject.record_staging_run_acceptance(registry, acceptance, expected_root_identity=identity)
    assert observed.acceptance == acceptance


def test_one_shot_compares_final_observation_with_record_result(tmp_path, monkeypatch):
    source, registry, _ = _material(tmp_path)
    recorded = []
    final = []
    original_record = accept_subject.record_staging_run_acceptance
    original_observe = accept_subject.observe_staging_run_acceptance

    def record(root, value, **kwargs):
        result = original_record(root, value, **kwargs)
        recorded.append(result)
        return result

    def observe(root, run_id, **kwargs):
        result = original_observe(root, run_id, **kwargs)
        final.append(result)
        return result

    monkeypatch.setattr(accept_subject, "record_staging_run_acceptance", record)
    monkeypatch.setattr(accept_subject, "observe_staging_run_acceptance", observe)
    monkeypatch.setattr(accept_subject, "_utc_now", lambda: NOW)
    accept_subject.verify_and_accept(source, registry)
    assert final == recorded


def test_one_shot_rejects_same_content_marker_replacement_after_record(tmp_path, monkeypatch):
    source, registry, _ = _material(tmp_path)
    marker = registry / (RUN + ".accepted")
    original = accept_subject.record_staging_run_acceptance

    def replacing(root, value, **kwargs):
        observed = original(root, value, **kwargs)
        content = marker.read_bytes()
        marker.unlink()
        marker.write_bytes(content)
        marker.chmod(0o600)
        return observed

    monkeypatch.setattr(accept_subject, "record_staging_run_acceptance", replacing)
    monkeypatch.setattr(accept_subject, "_utc_now", lambda: NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        accept_subject.verify_and_accept(source, registry)


def test_final_observation_is_bound_to_expected_registry_identity(tmp_path, monkeypatch):
    source, registry, _ = _material(tmp_path)
    identity = (registry.stat().st_dev, registry.stat().st_ino)
    seen = []
    original = accept_subject.observe_staging_run_acceptance

    def observe(root, run_id, *, expected_root_identity=None):
        seen.append(expected_root_identity)
        return original(root, run_id, expected_root_identity=expected_root_identity)

    monkeypatch.setattr(accept_subject, "observe_staging_run_acceptance", observe)
    monkeypatch.setattr(accept_subject, "_utc_now", lambda: NOW)
    accept_subject.verify_and_accept(source, registry, expected_acceptance_identity=identity)
    assert seen == [identity]
