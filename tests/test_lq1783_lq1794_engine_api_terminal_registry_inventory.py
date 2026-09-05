import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject

def test_accept_terminally_reobserves_complete_registry(tmp_path,monkeypatch):
    root=operation_root(tmp_path);values=[];original=subject.observe_registry
    def observed(*args,**kwargs): value=original(*args,**kwargs);values.append(value);return value
    monkeypatch.setattr(subject,"observe_registry",observed);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root)
    assert len(values)==4 and values[1]==values[2]==values[3]

def test_accept_rejects_terminal_registry_divergence(tmp_path,monkeypatch):
    root=operation_root(tmp_path);calls=0;original=subject.observe_registry
    def observed(*args,**kwargs):
        nonlocal calls
        value=original(*args,**kwargs);calls+=1
        return () if calls==4 else value
    monkeypatch.setattr(subject,"observe_registry",observed);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.accept_once(root)

def test_terminal_registry_read_uses_bound_identity(tmp_path,monkeypatch):
    root=operation_root(tmp_path);arguments=[];original=subject.observe_registry
    def observed(*args,**kwargs): arguments.append((args,kwargs));return original(*args,**kwargs)
    monkeypatch.setattr(subject,"observe_registry",observed);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root)
    assert arguments[-1][0]==(root/"accepted-runs",) and arguments[-1][1]["expected_acceptance_identity"]==arguments[0][1]["expected_acceptance_identity"]

def test_stable_terminal_registry_inventory_completes(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root)
    assert len(subject.observe_registry(root/"accepted-runs"))==1
