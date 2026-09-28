import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_acceptance_audit as audit_subject
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject

def _accepted(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root);monkeypatch.setattr(audit_subject,"_utc_now",lambda:NOW);return root

@pytest.mark.parametrize("mode",("accept","registry","accepted"))
def test_all_registry_reads_use_shared_validated_boundary(tmp_path,monkeypatch,mode):
    root=_accepted(tmp_path,monkeypatch) if mode!="accept" else operation_root(tmp_path);calls=[];original=subject._observe_validated_registry
    def observed(*args,**kwargs): value=original(*args,**kwargs);calls.append(value);return value
    monkeypatch.setattr(subject,"_observe_validated_registry",observed)
    if mode=="accept": monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root)
    else: subject.audit(root,accepted_source=mode=="accepted")
    assert len(calls)==4 if mode=="accept" else len(calls)==3

@pytest.mark.parametrize("mode",("accept","registry","accepted"))
def test_malformed_registry_read_fails_at_shared_boundary(tmp_path,monkeypatch,mode):
    root=_accepted(tmp_path,monkeypatch) if mode!="accept" else operation_root(tmp_path);original=subject.observe_registry;calls=0
    def malformed(*args,**kwargs):
        nonlocal calls
        calls+=1
        return None if calls==(4 if mode=="accept" else 3) else original(*args,**kwargs)
    monkeypatch.setattr(subject,"observe_registry",malformed)
    if mode=="accept": monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        subject.accept_once(root) if mode=="accept" else subject.audit(root,accepted_source=mode=="accepted")

def test_validated_registry_boundary_preserves_bound_identity(tmp_path,monkeypatch):
    root=operation_root(tmp_path);expected=subject.resolve_operation_root(root);seen=[];original=subject.observe_registry
    def observed(*args,**kwargs): seen.append((args,kwargs));return original(*args,**kwargs)
    monkeypatch.setattr(subject,"observe_registry",observed);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root)
    assert all(args==(root/"accepted-runs",) and kwargs=={"expected_acceptance_identity":expected.acceptance_identity} for args,kwargs in seen)
