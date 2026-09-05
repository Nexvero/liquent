import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject

def _clock(values):
    iterator=iter(values);calls=[]
    def read(): value=next(iterator);calls.append(value);return value
    return read,calls

def test_source_is_observed_after_completion_freshness_verification(tmp_path,monkeypatch):
    root=operation_root(tmp_path);values=[];original=subject.observe_run_bound_source_set
    def observed(*args,**kwargs): value=original(*args,**kwargs);values.append(value);return value
    monkeypatch.setattr(subject,"observe_run_bound_source_set",observed);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root)
    assert len(values)==4 and values[0]==values[1]==values[2]==values[3]

def test_source_change_during_completion_verification_is_rejected(tmp_path,monkeypatch):
    root=operation_root(tmp_path);target=root/"source-set"/"render";original=subject.verify_run_bound_snapshot;calls=0
    def changing(*args,**kwargs):
        nonlocal calls
        result=original(*args,**kwargs);calls+=1
        if calls==2:
            content=target.read_bytes();target.write_bytes(bytes((value+1)%256 for value in content));target.chmod(0o600)
        return result
    monkeypatch.setattr(subject,"verify_run_bound_snapshot",changing);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.accept_once(root)

def test_terminal_convergence_is_included_in_duration(tmp_path,monkeypatch):
    root=operation_root(tmp_path);clock,calls=_clock((100.0,129.0,130.000001));monkeypatch.setattr(subject,"_monotonic_now",clock);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.accept_once(root)
    assert calls==[100.0,129.0,130.000001]

def test_stable_terminal_source_convergence_completes(tmp_path,monkeypatch):
    root=operation_root(tmp_path);clock,_=_clock((100.0,101.0,102.0));monkeypatch.setattr(subject,"_monotonic_now",clock);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root)
    assert len(tuple((root/"accepted-runs").iterdir()))==1
