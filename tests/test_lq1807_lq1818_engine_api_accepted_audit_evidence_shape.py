import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_operation_verify as subject

@pytest.mark.parametrize("evidence",(None,(),(None,),[None,None],(None,None,None)))
def test_accepted_audit_rejects_noncanonical_evidence_shape(tmp_path,monkeypatch,evidence):
    root=operation_root(tmp_path);monkeypatch.setattr(subject,"verify_accepted_current",lambda *args,**kwargs:evidence)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.audit(root,accepted_source=True)

def test_accepted_audit_rejects_wrong_exact_evidence_types(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(subject,"verify_accepted_current",lambda *args,**kwargs:(None,None))
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.audit(root,accepted_source=True)

def test_accepted_audit_null_evidence_fails_before_success_check(tmp_path,monkeypatch):
    root=operation_root(tmp_path);checks=[];original=subject._within_operation_roots
    def within(path,operation,**kwargs):
        check=kwargs["success_check"]
        def observed(resolved,result): checks.append(result);return check(resolved,result)
        return original(path,operation,**{**kwargs,"success_check":observed})
    monkeypatch.setattr(subject,"_within_operation_roots",within);monkeypatch.setattr(subject,"verify_accepted_current",lambda *args,**kwargs:None)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.audit(root,accepted_source=True)
    assert checks==[]

def test_accepted_audit_evidence_shape_failure_is_detail_free(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(subject,"verify_accepted_current",lambda *args,**kwargs:object())
    with pytest.raises(ManifestHandoffRegistryUnavailable) as failure: subject.audit(root,accepted_source=True)
    assert str(failure.value)=="manifest_handoff_registry_unavailable"
