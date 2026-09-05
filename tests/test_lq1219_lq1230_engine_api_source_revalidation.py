import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tools import engine_api_joint_staging_acceptance_audit as audit_subject
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools.engine_api_joint_staging_acceptance_audit import verify_accepted_current
from tools.engine_api_joint_staging_one_shot_verify import verify_and_accept
from tests.test_lq1135_lq1146_engine_api_run_acceptance import roots
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW

def test_acceptance_reloads_identical_source_after_marker_write(tmp_path,monkeypatch):
    source,root=roots(tmp_path);calls=[];original=accept_subject.observe_run_bound_source_set
    def observed(path,**kwargs): calls.append(path);return original(path,**kwargs)
    monkeypatch.setattr(accept_subject,"observe_run_bound_source_set",observed);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);verify_and_accept(source,root);assert calls==[source,source]

@pytest.mark.parametrize("target",("run-envelope","evidence","render"))
def test_post_accept_source_mutation_is_unknown_outcome_with_marker(tmp_path,monkeypatch,target):
    source,root=roots(tmp_path);original=accept_subject.record_staging_run_acceptance
    def mutating(acceptance_root,value,**kwargs): result=original(acceptance_root,value,**kwargs);path=source/target;path.write_bytes(path.read_bytes()+b"x");return result
    monkeypatch.setattr(accept_subject,"record_staging_run_acceptance",mutating);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): verify_and_accept(source,root)
    assert len(list(root.iterdir()))==1

def test_accepted_audit_reloads_identical_source_after_verification(tmp_path,monkeypatch):
    source,root=roots(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);verify_and_accept(source,root);calls=[];original=audit_subject.observe_run_bound_source_set
    def observed(path,**kwargs): calls.append(path);return original(path,**kwargs)
    monkeypatch.setattr(audit_subject,"observe_run_bound_source_set",observed);monkeypatch.setattr(audit_subject,"_utc_now",lambda:NOW);verify_accepted_current(source,root);assert calls==[source,source]

@pytest.mark.parametrize("target",("run-authority","signature","staging-policy"))
def test_accepted_audit_rejects_source_mutation_after_crypto(tmp_path,monkeypatch,target):
    source,root=roots(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);verify_and_accept(source,root);original=audit_subject.verify_run_bound_snapshot
    def mutating(snapshot,**kwargs): original(snapshot,**kwargs);path=source/target;path.write_bytes(path.read_bytes()+b"x")
    monkeypatch.setattr(audit_subject,"verify_run_bound_snapshot",mutating);monkeypatch.setattr(audit_subject,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): verify_accepted_current(source,root)

def test_failed_post_accept_revalidation_blocks_retry(tmp_path,monkeypatch):
    source,root=roots(tmp_path);original=accept_subject.record_staging_run_acceptance
    def mutating(acceptance_root,value,**kwargs): result=original(acceptance_root,value,**kwargs);path=source/"render";path.write_bytes(path.read_bytes()+b"x");return result
    monkeypatch.setattr(accept_subject,"record_staging_run_acceptance",mutating);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): verify_and_accept(source,root)
    monkeypatch.setattr(accept_subject,"record_staging_run_acceptance",original)
    with pytest.raises(ManifestHandoffRegistryUnavailable): verify_and_accept(source,root)
