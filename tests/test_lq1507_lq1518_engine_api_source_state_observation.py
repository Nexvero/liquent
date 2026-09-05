import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1123_lq1134_engine_api_run_bound_root import run_root
from tests.test_lq1135_lq1146_engine_api_run_acceptance import roots
from tests.test_lq1159_lq1170_engine_api_acceptance_audit import accept
from tools import engine_api_joint_staging_acceptance_audit as audit_subject
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools.engine_api_joint_staging_source_set import load_run_bound_source_set, observe_run_bound_source_set


def test_source_observation_contains_root_and_all_child_states(tmp_path):
    root = run_root(tmp_path)
    observed = observe_run_bound_source_set(root)
    assert observed.snapshot == load_run_bound_source_set(root)
    assert observed.root_state[:2] == (root.stat().st_dev, root.stat().st_ino)
    assert len(observed.child_states) == 14
    assert repr(observed) == "JointEngineApiRunBoundSourceObservation()"


def test_one_shot_rejects_same_inode_source_rewrite_with_restored_bytes(tmp_path, monkeypatch):
    source, registry = roots(tmp_path)
    target = source / "render"
    original = accept_subject.record_staging_run_acceptance

    def rewriting(root, value, **kwargs):
        result = original(root, value, **kwargs)
        content = target.read_bytes();target.write_bytes(b"temporary");target.write_bytes(content);target.chmod(0o600)
        return result

    monkeypatch.setattr(accept_subject, "record_staging_run_acceptance", rewriting)
    monkeypatch.setattr(accept_subject, "_utc_now", lambda: NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): accept_subject.verify_and_accept(source, registry)


def test_audit_rejects_same_inode_source_rewrite_with_restored_bytes(tmp_path, monkeypatch):
    source, registry = roots(tmp_path);accept(source, registry);target = source / "render";original = audit_subject.verify_run_bound_snapshot
    def rewriting(snapshot, **kwargs):
        original(snapshot, **kwargs);content=target.read_bytes();target.write_bytes(b"temporary");target.write_bytes(content);target.chmod(0o600)
    monkeypatch.setattr(audit_subject, "verify_run_bound_snapshot", rewriting);monkeypatch.setattr(audit_subject, "_utc_now", lambda: NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): audit_subject.verify_accepted_current(source, registry)


def test_stable_source_observation_allows_acceptance_and_audit(tmp_path, monkeypatch):
    source, registry = roots(tmp_path);monkeypatch.setattr(accept_subject, "_utc_now", lambda: NOW);accept_subject.verify_and_accept(source, registry);monkeypatch.setattr(audit_subject, "_utc_now", lambda: NOW);audit_subject.verify_accepted_current(source, registry)
