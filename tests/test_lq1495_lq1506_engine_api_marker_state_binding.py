import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport import manifest_handoff_supervisor_engine_api_staging_acceptance as registry_subject
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_acceptance import ManifestHandoffSupervisorEngineApiStagingRunAcceptanceObservation, build_staging_run_acceptance
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_run import decode_staging_run_authority
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1123_lq1134_engine_api_run_bound_root import RUN
from tests.test_lq1135_lq1146_engine_api_run_acceptance import roots
from tests.test_lq1159_lq1170_engine_api_acceptance_audit import accept
from tools import engine_api_joint_staging_acceptance_audit as audit_subject
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools.engine_api_joint_staging_source_set import load_run_bound_source_set


def _acceptance(source):
    snapshot = load_run_bound_source_set(source)
    return build_staging_run_acceptance(decode_staging_run_authority(snapshot.run_authority), snapshot.run_envelope)


def test_marker_observation_contains_complete_stable_descriptor_state(tmp_path):
    source, registry = roots(tmp_path)
    accept(source, registry)
    marker = registry / (RUN + ".accepted")
    facts = marker.stat()
    observed = registry_subject.observe_staging_run_acceptance(registry, RUN)
    expected = tuple(getattr(facts, name) for name in ("st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns"))
    assert observed.marker_state == expected
    assert observed.marker_state[:2] == observed.marker_identity


@pytest.mark.parametrize("state", ((1,), (1,) * 9, (1, 2, 3, 4, 5, 6, 7, 8, True), [1] * 9, "state"))
def test_marker_observation_rejects_malformed_or_unbound_state(tmp_path, state):
    source, _ = roots(tmp_path)
    value = _acceptance(source)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        ManifestHandoffSupervisorEngineApiStagingRunAcceptanceObservation(value, (1, 2), state)


def test_recorded_observation_contains_post_sync_marker_state(tmp_path):
    source, registry = roots(tmp_path)
    observed = registry_subject.record_staging_run_acceptance(registry, _acceptance(source))
    marker = registry / (RUN + ".accepted")
    assert observed.marker_state[7:] == (marker.stat().st_mtime_ns, marker.stat().st_ctime_ns)


def test_audit_rejects_same_inode_rewrite_restored_to_same_bytes(tmp_path, monkeypatch):
    source, registry = roots(tmp_path)
    accept(source, registry)
    marker = registry / (RUN + ".accepted")
    original = audit_subject.verify_run_bound_snapshot

    def rewriting(snapshot, **kwargs):
        original(snapshot, **kwargs)
        content = marker.read_bytes()
        marker.write_bytes(b"temporary\n")
        marker.write_bytes(content)
        marker.chmod(0o600)

    monkeypatch.setattr(audit_subject, "verify_run_bound_snapshot", rewriting)
    monkeypatch.setattr(audit_subject, "_utc_now", lambda: NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        audit_subject.verify_accepted_current(source, registry)


def test_one_shot_rejects_same_inode_rewrite_after_record(tmp_path, monkeypatch):
    source, registry = roots(tmp_path)
    marker = registry / (RUN + ".accepted")
    original = accept_subject.record_staging_run_acceptance

    def rewriting(root, value, **kwargs):
        observed = original(root, value, **kwargs)
        content = marker.read_bytes()
        marker.write_bytes(b"temporary\n")
        marker.write_bytes(content)
        marker.chmod(0o600)
        return observed

    monkeypatch.setattr(accept_subject, "record_staging_run_acceptance", rewriting)
    monkeypatch.setattr(accept_subject, "_utc_now", lambda: NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        accept_subject.verify_and_accept(source, registry)


def test_stable_marker_state_allows_audit_and_one_shot(tmp_path, monkeypatch):
    source, registry = roots(tmp_path)
    monkeypatch.setattr(accept_subject, "_utc_now", lambda: NOW)
    accept_subject.verify_and_accept(source, registry)
    monkeypatch.setattr(audit_subject, "_utc_now", lambda: NOW)
    audit_subject.verify_accepted_current(source, registry)
