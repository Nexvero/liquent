import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject

def test_root_validation_completion_requires_none(tmp_path,monkeypatch):
    root=operation_root(tmp_path);resolved=subject.resolve_operation_root(root);monkeypatch.setattr(subject,"validate_operation_roots",lambda *args,**kwargs:object())
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject._validate_operation_root_completion(root,resolved)

def test_read_only_success_rejects_foreign_root_validation_result(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(subject,"validate_operation_roots",lambda *args,**kwargs:True)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.audit(root,accepted_source=False)

def test_accept_success_rejects_foreign_root_validation_result(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(subject,"validate_operation_roots",lambda *args,**kwargs:());monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.accept_once(root)
    assert len(tuple((root/"accepted-runs").iterdir()))==1

def test_failure_revalidation_rejects_foreign_completion_result(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(subject,"validate_operation_roots",lambda *args,**kwargs:object())
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject._within_operation_roots(root,lambda resolved:(_ for _ in ()).throw(RuntimeError("hidden")))

def test_root_validation_completion_forwards_mutation_allowance(tmp_path,monkeypatch):
    root=operation_root(tmp_path);resolved=subject.resolve_operation_root(root);seen=[]
    def validated(*args,**kwargs): seen.append((args,kwargs))
    monkeypatch.setattr(subject,"validate_operation_roots",validated);subject._validate_operation_root_completion(root,resolved,allow_acceptance_state_change=True)
    assert seen==[((root,resolved),{"allow_acceptance_state_change":True})]

def test_normal_root_validation_completion_remains_none(tmp_path):
    root=operation_root(tmp_path);resolved=subject.resolve_operation_root(root)
    assert subject._validate_operation_root_completion(root,resolved) is None
