import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject

@pytest.mark.parametrize("values",(None,[],[None],(None,),object()))
def test_registry_audit_rejects_invalid_value_handoff_before_observation(tmp_path,monkeypatch,values):
    root=operation_root(tmp_path);observations=[];monkeypatch.setattr(subject,"inspect_registry",lambda *args,**kwargs:values);monkeypatch.setattr(subject,"observe_registry",lambda *args,**kwargs:observations.append(True))
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.audit(root,accepted_source=False)
    assert observations==[]

def test_registry_result_constructor_reuses_exact_value_gate():
    for values in (None,[],(None,)):
        with pytest.raises(ManifestHandoffRegistryUnavailable): subject.JointEngineApiRegistryAuditResult(values,())

def test_registry_audit_accepts_empty_exact_value_tuple(tmp_path):
    subject.audit(operation_root(tmp_path),accepted_source=False)

def test_registry_audit_accepts_exact_acceptance_value_tuple(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root);seen=[];original=subject.inspect_registry
    def inspected(*args,**kwargs): value=original(*args,**kwargs);seen.append(value);return value
    monkeypatch.setattr(subject,"inspect_registry",inspected);subject.audit(root,accepted_source=False)
    assert len(seen)==3 and all(type(value)is tuple and type(value[0]) is subject.ManifestHandoffSupervisorEngineApiStagingRunAcceptance for value in seen)

def test_registry_value_handoff_failure_is_detail_free(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(subject,"inspect_registry",lambda *args,**kwargs:object())
    with pytest.raises(ManifestHandoffRegistryUnavailable) as failure: subject.audit(root,accepted_source=False)
    assert str(failure.value)=="manifest_handoff_registry_unavailable"
