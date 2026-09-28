import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject

def test_source_is_observed_again_after_final_verification(tmp_path,monkeypatch):
    root=operation_root(tmp_path);values=[];original=subject.observe_run_bound_source_set
    def observed(*args,**kwargs): value=original(*args,**kwargs);values.append(value);return value
    monkeypatch.setattr(subject,"observe_run_bound_source_set",observed);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root)
    assert len(values)==4 and values[0]==values[1]==values[2]==values[3]

def test_source_change_during_final_verification_is_rejected(tmp_path,monkeypatch):
    root=operation_root(tmp_path);target=root/"source-set"/"render";original=subject.verify_run_bound_snapshot;calls=0
    def changing(*args,**kwargs):
        nonlocal calls
        result=original(*args,**kwargs);calls+=1
        if calls==1:
            content=target.read_bytes();target.write_bytes(bytes((value+1)%256 for value in content));target.chmod(0o600)
        return result
    monkeypatch.setattr(subject,"verify_run_bound_snapshot",changing);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.accept_once(root)

def test_retained_snapshot_is_verified_at_verification_and_completion_times(tmp_path,monkeypatch):
    root=operation_root(tmp_path);seen=[];original=subject.verify_run_bound_snapshot
    def verified(snapshot,*,now): seen.append((snapshot,now));return original(snapshot,now=now)
    monkeypatch.setattr(subject,"verify_run_bound_snapshot",verified);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root)
    assert len(seen)==2 and seen[0][0] is seen[1][0] and seen[0][1]==seen[1][1]==NOW

def test_stable_post_verification_source_convergence_completes(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root)
    assert len(tuple((root/"accepted-runs").iterdir()))==1
