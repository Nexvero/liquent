import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject

def test_acceptance_inventory_is_rechecked_after_state_capture(tmp_path,monkeypatch):
    root=operation_root(tmp_path);observations=[];original=subject.observe_registry
    def observed(*args,**kwargs): value=original(*args,**kwargs);observations.append(value);return value
    monkeypatch.setattr(subject,"observe_registry",observed);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root)
    assert len(observations)==4 and observations[1]==observations[2]==observations[3]

def test_replacement_between_inventory_and_state_capture_is_rejected(tmp_path,monkeypatch):
    root=operation_root(tmp_path);registry=root/"accepted-runs";calls=0;original=subject.resolve_operation_root
    def replacing(*args,**kwargs):
        nonlocal calls
        value=original(*args,**kwargs);calls+=1
        if calls==2:
            marker=next(registry.iterdir());content=marker.read_bytes();marker.unlink();marker.write_bytes(content);marker.chmod(0o600)
        return value
    monkeypatch.setattr(subject,"resolve_operation_root",replacing);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.accept_once(root)

def test_success_check_receives_captured_roots_and_inner_inventory(tmp_path,monkeypatch):
    root=operation_root(tmp_path);values=[]
    def operation(resolved): return (resolved.acceptance_identity,)
    def checked(resolved,result): values.append((resolved.acceptance_identity,result))
    result=subject._within_operation_roots(root,operation,allow_acceptance_state_change=True,success_check=checked)
    assert values==[(result[0],result)]

def test_stable_inventory_state_bridge_completes(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root)
    assert len(tuple((root/"accepted-runs").iterdir()))==1
