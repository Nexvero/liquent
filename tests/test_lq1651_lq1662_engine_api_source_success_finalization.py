import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject

def test_source_is_reobserved_after_acceptance_state_capture(tmp_path,monkeypatch):
    root=operation_root(tmp_path);observations=[];original=subject.observe_run_bound_source_set
    def observed(*args,**kwargs): value=original(*args,**kwargs);observations.append(value);return value
    monkeypatch.setattr(subject,"observe_run_bound_source_set",observed);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root)
    assert len(observations)==4 and observations[0]==observations[1]==observations[2]==observations[3]

def test_source_change_between_inner_inventory_and_state_capture_is_rejected(tmp_path,monkeypatch):
    root=operation_root(tmp_path);target=root/"source-set"/"render";calls=0;original=subject.resolve_operation_root
    def changing(*args,**kwargs):
        nonlocal calls
        value=original(*args,**kwargs);calls+=1
        if calls==2:
            content=target.read_bytes();target.write_bytes(bytes((value+1)%256 for value in content));target.chmod(0o600)
        return value
    monkeypatch.setattr(subject,"resolve_operation_root",changing);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.accept_once(root)

def test_source_success_check_uses_resolved_source_identity(tmp_path,monkeypatch):
    root=operation_root(tmp_path);identities=[];original=subject.observe_run_bound_source_set
    def observed(path,*,expected_root_identity=None): identities.append(expected_root_identity);return original(path,expected_root_identity=expected_root_identity)
    monkeypatch.setattr(subject,"observe_run_bound_source_set",observed);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root)
    assert len(identities)==4 and identities[0]==identities[1]==identities[2]==identities[3] and identities[0] is not None

def test_stable_source_success_finalization_completes(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root)
    assert len(tuple((root/"accepted-runs").iterdir()))==1
