import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tools import engine_api_joint_staging_acceptance_audit as audit_subject
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tests.test_lq1135_lq1146_engine_api_run_acceptance import roots
from tests.test_lq1123_lq1134_engine_api_run_bound_root import RUN
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW

def test_acceptance_loads_marker_before_and_after_decision(tmp_path,monkeypatch):
    source,root=roots(tmp_path);calls=[];original=accept_subject.load_staging_run_acceptance
    def observed(path,run_id,**kwargs): calls.append((path,run_id));return original(path,run_id,**kwargs)
    monkeypatch.setattr(accept_subject,"load_staging_run_acceptance",observed);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);accept_subject.verify_and_accept(source,root);assert calls==[(root,RUN),(root,RUN)]

@pytest.mark.parametrize("mutation",("content","mode","link"))
def test_post_accept_marker_mutation_is_unknown_outcome(tmp_path,monkeypatch,mutation):
    source,root=roots(tmp_path);original=accept_subject.record_staging_run_acceptance
    def mutating(path,value,**kwargs):
        result=original(path,value,**kwargs);marker=path/(RUN+".accepted")
        if mutation=="content": marker.write_bytes(b"invalid\n")
        elif mutation=="mode": marker.chmod(0o640)
        else: (tmp_path/"linked").hardlink_to(marker)
        return result
    monkeypatch.setattr(accept_subject,"record_staging_run_acceptance",mutating);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): accept_subject.verify_and_accept(source,root)
    assert len(list(root.iterdir()))==1

def accepted(tmp_path,monkeypatch):
    source,root=roots(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);accept_subject.verify_and_accept(source,root);return source,root

def test_audit_loads_same_marker_before_and_after_crypto(tmp_path,monkeypatch):
    source,root=accepted(tmp_path,monkeypatch);calls=[];original=audit_subject.observe_staging_run_acceptance
    def observed(path,run_id,**kwargs): calls.append((path,run_id));return original(path,run_id,**kwargs)
    monkeypatch.setattr(audit_subject,"observe_staging_run_acceptance",observed);monkeypatch.setattr(audit_subject,"_utc_now",lambda:NOW);audit_subject.verify_accepted_current(source,root);assert calls==[(root,RUN),(root,RUN)]

@pytest.mark.parametrize("mutation",("content","mode","absent"))
def test_audit_rejects_marker_mutation_after_source_verification(tmp_path,monkeypatch,mutation):
    source,root=accepted(tmp_path,monkeypatch);original=audit_subject.verify_run_bound_snapshot
    def mutating(snapshot,**kwargs):
        original(snapshot,**kwargs);marker=root/(RUN+".accepted")
        if mutation=="content": marker.write_bytes(b"invalid\n")
        elif mutation=="mode": marker.chmod(0o640)
        else: marker.unlink()
    monkeypatch.setattr(audit_subject,"verify_run_bound_snapshot",mutating);monkeypatch.setattr(audit_subject,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): audit_subject.verify_accepted_current(source,root)

def test_stable_marker_and_source_allow_complete_lifecycle(tmp_path,monkeypatch):
    source,root=accepted(tmp_path,monkeypatch);monkeypatch.setattr(audit_subject,"_utc_now",lambda:NOW);audit_subject.verify_accepted_current(source,root)
