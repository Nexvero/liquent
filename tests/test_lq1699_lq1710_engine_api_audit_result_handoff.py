import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_acceptance_audit as audit_subject
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject

def _accepted(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root);monkeypatch.setattr(audit_subject,"_utc_now",lambda:NOW);return root

def test_accepted_audit_returns_bound_source_and_marker_observations(tmp_path,monkeypatch):
    root=_accepted(tmp_path,monkeypatch);source,marker=audit_subject.verify_accepted_current(root/"source-set",root/"accepted-runs")
    assert source.snapshot.run_authority and marker.acceptance.run_id

def test_registry_audit_rechecks_values_and_observation_inventory(tmp_path,monkeypatch):
    root=_accepted(tmp_path,monkeypatch);inspects=[];observes=[];original_inspect=subject.inspect_registry;original_observe=subject.observe_registry
    def inspected(*args,**kwargs): value=original_inspect(*args,**kwargs);inspects.append(value);return value
    def observed(*args,**kwargs): value=original_observe(*args,**kwargs);observes.append(value);return value
    monkeypatch.setattr(subject,"inspect_registry",inspected);monkeypatch.setattr(subject,"observe_registry",observed);subject.audit(root,accepted_source=False)
    assert len(inspects)==len(observes)==3 and inspects[0]==inspects[1]==inspects[2] and observes[0]==observes[1]==observes[2]

def test_accepted_audit_rejects_marker_replacement_after_inner_success(tmp_path,monkeypatch):
    root=_accepted(tmp_path,monkeypatch);registry=root/"accepted-runs";original=subject.verify_accepted_current
    def replacing(*args,**kwargs):
        result=original(*args,**kwargs);marker=next(registry.iterdir());content=marker.read_bytes();marker.unlink();marker.write_bytes(content);marker.chmod(0o600);return result
    monkeypatch.setattr(subject,"verify_accepted_current",replacing)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.audit(root,accepted_source=True)

def test_stable_operation_audits_complete(tmp_path,monkeypatch):
    root=_accepted(tmp_path,monkeypatch);subject.audit(root,accepted_source=False);subject.audit(root,accepted_source=True)
