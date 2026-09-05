import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject

@pytest.mark.parametrize("inventory",(None,[],[None],(None,),object()))
def test_accept_rejects_invalid_before_inventory_without_mutation(tmp_path,monkeypatch,inventory):
    root=operation_root(tmp_path);mutations=[];monkeypatch.setattr(subject,"observe_registry",lambda *args,**kwargs:inventory);monkeypatch.setattr(subject,"verify_and_accept",lambda *args,**kwargs:mutations.append(True))
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.accept_once(root)
    assert mutations==[] and tuple((root/"accepted-runs").iterdir())==()

@pytest.mark.parametrize("inventory",(None,[],(None,),object()))
def test_accept_rejects_invalid_after_inventory_before_delta(tmp_path,monkeypatch,inventory):
    root=operation_root(tmp_path);calls=0;original_observe=subject.observe_registry;original_accept=subject.verify_and_accept
    def observed(*args,**kwargs):
        nonlocal calls
        calls+=1
        return original_observe(*args,**kwargs) if calls==1 else inventory
    monkeypatch.setattr(subject,"observe_registry",observed);monkeypatch.setattr(subject,"verify_and_accept",original_accept);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.accept_once(root)
    assert len(tuple((root/"accepted-runs").iterdir()))==1

def test_accept_inventory_handoff_uses_shared_result_validator(tmp_path,monkeypatch):
    root=operation_root(tmp_path);validated=[];original=subject._validate_result_observations
    def validate(value): validated.append(value);return original(value)
    monkeypatch.setattr(subject,"_validate_result_observations",validate);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root)
    assert len(validated)==5 and validated[0]==() and all(len(value)==1 for value in validated[1:])

def test_exact_before_and_after_inventory_handoffs_complete(tmp_path,monkeypatch):
    root=operation_root(tmp_path);seen=[];original=subject.observe_registry
    def observed(*args,**kwargs): value=original(*args,**kwargs);seen.append(value);return value
    monkeypatch.setattr(subject,"observe_registry",observed);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root)
    assert seen[0]==() and all(type(value)is tuple for value in seen)
