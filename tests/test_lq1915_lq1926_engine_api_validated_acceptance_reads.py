import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_acceptance_audit as audit_subject
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject

def _accepted(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root);monkeypatch.setattr(audit_subject,"_utc_now",lambda:NOW);return root

def test_accept_uses_one_shared_validated_acceptance_read(tmp_path,monkeypatch):
    root=operation_root(tmp_path);calls=[];original=subject._observe_validated_acceptance
    def observed(*args,**kwargs): value=original(*args,**kwargs);calls.append(value);return value
    monkeypatch.setattr(subject,"_observe_validated_acceptance",observed);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root)
    assert len(calls)==1 and type(calls[0]) is subject.ManifestHandoffSupervisorEngineApiStagingRunAcceptanceObservation

def test_accept_rejects_malformed_terminal_acceptance_read(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(subject,"observe_staging_run_acceptance",lambda *args,**kwargs:None);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.accept_once(root)

def test_accepted_audit_uses_two_shared_validated_acceptance_reads(tmp_path,monkeypatch):
    root=_accepted(tmp_path,monkeypatch);calls=[];original=subject._observe_validated_acceptance
    def observed(*args,**kwargs): value=original(*args,**kwargs);calls.append(value);return value
    monkeypatch.setattr(subject,"_observe_validated_acceptance",observed);subject.audit(root,accepted_source=True)
    assert len(calls)==2 and calls[0]==calls[1]

@pytest.mark.parametrize("call",(1,2))
def test_accepted_audit_rejects_malformed_acceptance_at_each_outer_read(tmp_path,monkeypatch,call):
    root=_accepted(tmp_path,monkeypatch);calls=0;original=subject.observe_staging_run_acceptance
    def malformed(*args,**kwargs):
        nonlocal calls
        calls+=1
        return None if calls==call else original(*args,**kwargs)
    monkeypatch.setattr(subject,"observe_staging_run_acceptance",malformed)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.audit(root,accepted_source=True)

def test_validated_acceptance_reads_preserve_run_and_root_identity(tmp_path,monkeypatch):
    root=_accepted(tmp_path,monkeypatch);expected=subject.resolve_operation_root(root);seen=[];original=subject.observe_staging_run_acceptance
    def observed(*args,**kwargs): seen.append((args,kwargs));return original(*args,**kwargs)
    monkeypatch.setattr(subject,"observe_staging_run_acceptance",observed);subject.audit(root,accepted_source=True)
    assert len(seen)==2 and all(args[0]==root/"accepted-runs" and args[1]==seen[0][0][1] and kwargs=={"expected_root_identity":expected.acceptance_identity} for args,kwargs in seen)

def test_registry_audit_does_not_read_target_acceptance(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(subject,"_observe_validated_acceptance",lambda *args,**kwargs:pytest.fail("unexpected marker read"));subject.audit(root,accepted_source=False)
