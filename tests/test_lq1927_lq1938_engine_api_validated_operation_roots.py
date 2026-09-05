import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject

@pytest.mark.parametrize("value",(None,(),object()))
def test_operation_rejects_malformed_initial_root_before_work(tmp_path,monkeypatch,value):
    root=operation_root(tmp_path);work=[];monkeypatch.setattr(subject,"resolve_operation_root",lambda *args,**kwargs:value)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject._within_operation_roots(root,lambda resolved:work.append(resolved))
    assert work==[]

def test_accept_uses_two_shared_validated_root_resolutions(tmp_path,monkeypatch):
    root=operation_root(tmp_path);seen=[];original=subject._resolve_validated_operation_root
    def resolved(*args,**kwargs): value=original(*args,**kwargs);seen.append(value);return value
    monkeypatch.setattr(subject,"_resolve_validated_operation_root",resolved);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root)
    assert len(seen)==2 and type(seen[0]) is subject.JointEngineApiStagingOperationRoots and seen[0].root_identity==seen[1].root_identity

def test_read_only_audit_uses_two_shared_validated_root_resolutions(tmp_path,monkeypatch):
    root=operation_root(tmp_path);seen=[];original=subject._resolve_validated_operation_root
    def resolved(*args,**kwargs): value=original(*args,**kwargs);seen.append(value);return value
    monkeypatch.setattr(subject,"_resolve_validated_operation_root",resolved);subject.audit(root,accepted_source=False)
    assert len(seen)==2 and seen[0]==seen[1]

def test_accept_rejects_malformed_post_operation_root(tmp_path,monkeypatch):
    root=operation_root(tmp_path);original=subject.resolve_operation_root;calls=0
    def resolved(*args,**kwargs):
        nonlocal calls
        calls+=1
        return object() if calls==2 else original(*args,**kwargs)
    monkeypatch.setattr(subject,"resolve_operation_root",resolved);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.accept_once(root)
    assert len(tuple((root/"accepted-runs").iterdir()))==1

def test_read_only_audit_rejects_malformed_post_operation_root(tmp_path,monkeypatch):
    root=operation_root(tmp_path);original=subject.resolve_operation_root;calls=0
    def resolved(*args,**kwargs):
        nonlocal calls
        calls+=1
        return None if calls==2 else original(*args,**kwargs)
    monkeypatch.setattr(subject,"resolve_operation_root",resolved)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.audit(root,accepted_source=False)

def test_operation_root_type_failure_is_detail_free(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(subject,"resolve_operation_root",lambda *args,**kwargs:object())
    with pytest.raises(ManifestHandoffRegistryUnavailable) as failure: subject.audit(root,accepted_source=False)
    assert str(failure.value)=="manifest_handoff_registry_unavailable"
