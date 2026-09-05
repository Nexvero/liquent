import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_acceptance_audit as audit_subject
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject

def _accepted(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root);monkeypatch.setattr(audit_subject,"_utc_now",lambda:NOW);return root

def test_registry_audit_uses_three_shared_validated_inspections(tmp_path,monkeypatch):
    root=_accepted(tmp_path,monkeypatch);calls=[];original=subject._inspect_validated_registry
    def inspected(*args,**kwargs): value=original(*args,**kwargs);calls.append(value);return value
    monkeypatch.setattr(subject,"_inspect_validated_registry",inspected);subject.audit(root,accepted_source=False)
    assert len(calls)==3 and calls[0]==calls[1]==calls[2]

@pytest.mark.parametrize("call",(1,2,3))
def test_registry_audit_rejects_malformed_value_read_at_every_stage(tmp_path,monkeypatch,call):
    root=_accepted(tmp_path,monkeypatch);calls=0;original=subject.inspect_registry
    def malformed(*args,**kwargs):
        nonlocal calls
        calls+=1
        return None if calls==call else original(*args,**kwargs)
    monkeypatch.setattr(subject,"inspect_registry",malformed)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.audit(root,accepted_source=False)

def test_validated_inspections_preserve_bound_registry_identity(tmp_path,monkeypatch):
    root=_accepted(tmp_path,monkeypatch);expected=subject.resolve_operation_root(root);seen=[];original=subject.inspect_registry
    def inspected(*args,**kwargs): seen.append((args,kwargs));return original(*args,**kwargs)
    monkeypatch.setattr(subject,"inspect_registry",inspected);subject.audit(root,accepted_source=False)
    assert len(seen)==3 and all(args==(root/"accepted-runs",) and kwargs=={"expected_acceptance_identity":expected.acceptance_identity} for args,kwargs in seen)

def test_accepted_audit_does_not_use_registry_value_projection(tmp_path,monkeypatch):
    root=_accepted(tmp_path,monkeypatch);monkeypatch.setattr(subject,"_inspect_validated_registry",lambda *args,**kwargs:pytest.fail("unexpected inspection"));subject.audit(root,accepted_source=True)
