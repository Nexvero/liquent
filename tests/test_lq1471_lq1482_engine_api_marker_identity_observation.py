import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport import manifest_handoff_supervisor_engine_api_staging_acceptance as registry_subject
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1123_lq1134_engine_api_run_bound_root import RUN
from tests.test_lq1135_lq1146_engine_api_run_acceptance import roots
from tests.test_lq1159_lq1170_engine_api_acceptance_audit import accept
from tools import engine_api_joint_staging_acceptance_audit as audit_subject


def test_marker_observation_exposes_value_and_descriptor_identity(tmp_path):
    source, registry = roots(tmp_path)
    accept(source, registry)
    observed = registry_subject.observe_staging_run_acceptance(registry, RUN)
    marker = registry / (RUN + ".accepted")
    assert observed.acceptance.run_id == RUN
    assert observed.marker_identity == (marker.stat().st_dev, marker.stat().st_ino)
    assert repr(observed) == "ManifestHandoffSupervisorEngineApiStagingRunAcceptanceObservation()"


def test_marker_observation_preserves_neutral_absence(tmp_path):
    _, registry = roots(tmp_path)
    assert registry_subject.observe_staging_run_acceptance(registry, RUN) is None


def test_marker_observation_binds_expected_registry_identity(tmp_path):
    source, registry = roots(tmp_path)
    accept(source, registry)
    identity = (registry.stat().st_dev, registry.stat().st_ino)
    assert registry_subject.observe_staging_run_acceptance(registry, RUN, expected_root_identity=identity) is not None


@pytest.mark.parametrize("expected", ((-1, 1), (True, 1), (1,), [1, 2], "1:2"))
def test_marker_observation_rejects_malformed_registry_identity(tmp_path, expected):
    _, registry = roots(tmp_path)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        registry_subject.observe_staging_run_acceptance(registry, RUN, expected_root_identity=expected)


def test_audit_passes_registry_identity_to_both_marker_observations(tmp_path, monkeypatch):
    source, registry = roots(tmp_path)
    accept(source, registry)
    source_identity = (source.stat().st_dev, source.stat().st_ino)
    acceptance_identity = (registry.stat().st_dev, registry.stat().st_ino)
    seen = []
    original = audit_subject.observe_staging_run_acceptance

    def recording(root, run_id, *, expected_root_identity=None):
        seen.append(expected_root_identity)
        return original(root, run_id, expected_root_identity=expected_root_identity)

    monkeypatch.setattr(audit_subject, "observe_staging_run_acceptance", recording)
    monkeypatch.setattr(audit_subject, "_utc_now", lambda: NOW)
    audit_subject.verify_accepted_current(source, registry, expected_source_identity=source_identity, expected_acceptance_identity=acceptance_identity)
    assert seen == [acceptance_identity, acceptance_identity]


def test_audit_rejects_same_content_marker_replacement(tmp_path, monkeypatch):
    source, registry = roots(tmp_path)
    accept(source, registry)
    marker = registry / (RUN + ".accepted")
    original = audit_subject.verify_run_bound_snapshot

    def replacing(snapshot, **kwargs):
        original(snapshot, **kwargs)
        content = marker.read_bytes()
        marker.unlink()
        marker.write_bytes(content)
        marker.chmod(0o600)

    monkeypatch.setattr(audit_subject, "verify_run_bound_snapshot", replacing)
    monkeypatch.setattr(audit_subject, "_utc_now", lambda: NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        audit_subject.verify_accepted_current(source, registry)


def test_ordinary_load_remains_value_only_compatible(tmp_path):
    source, registry = roots(tmp_path)
    accept(source, registry)
    value = registry_subject.load_staging_run_acceptance(registry, RUN)
    assert value.run_id == RUN
    assert not hasattr(value, "marker_identity")
