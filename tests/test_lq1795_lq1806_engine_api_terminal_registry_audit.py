import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_operation_verify as subject

def test_registry_audit_terminally_rechecks_values_and_observations(tmp_path,monkeypatch):
    root=operation_root(tmp_path);inspects=[];observes=[];original_inspect=subject.inspect_registry;original_observe=subject.observe_registry
    def inspected(*args,**kwargs): value=original_inspect(*args,**kwargs);inspects.append(value);return value
    def observed(*args,**kwargs): value=original_observe(*args,**kwargs);observes.append(value);return value
    monkeypatch.setattr(subject,"inspect_registry",inspected);monkeypatch.setattr(subject,"observe_registry",observed);subject.audit(root,accepted_source=False)
    assert len(inspects)==len(observes)==3 and len(set(inspects))==len(set(observes))==1

@pytest.mark.parametrize("target",("values","observations"))
def test_registry_audit_rejects_terminal_divergence(tmp_path,monkeypatch,target):
    root=operation_root(tmp_path);name="inspect_registry" if target=="values" else "observe_registry";original=getattr(subject,name);calls=0
    def changed(*args,**kwargs):
        nonlocal calls
        value=original(*args,**kwargs);calls+=1
        return (None,) if calls==3 else value
    monkeypatch.setattr(subject,name,changed)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.audit(root,accepted_source=False)

def test_registry_audit_terminal_rechecks_are_duration_bound(tmp_path,monkeypatch):
    root=operation_root(tmp_path);clock=iter((100.0,129.0,130.000001));monkeypatch.setattr(subject,"_monotonic_now",lambda:next(clock))
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.audit(root,accepted_source=False)

def test_stable_terminal_registry_audit_completes(tmp_path):
    subject.audit(operation_root(tmp_path),accepted_source=False)
