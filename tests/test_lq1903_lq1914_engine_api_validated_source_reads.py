import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_acceptance_audit as audit_subject
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject

def _accepted(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root);monkeypatch.setattr(audit_subject,"_utc_now",lambda:NOW);return root

def test_accept_uses_four_shared_validated_source_reads(tmp_path,monkeypatch):
    root=operation_root(tmp_path);calls=[];original=subject._observe_validated_source
    def observed(*args,**kwargs): value=original(*args,**kwargs);calls.append(value);return value
    monkeypatch.setattr(subject,"_observe_validated_source",observed);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root)
    assert len(calls)==4 and calls[0]==calls[1]==calls[2]==calls[3]

@pytest.mark.parametrize("call",(1,2,3,4))
def test_accept_rejects_malformed_source_at_every_operation_read(tmp_path,monkeypatch,call):
    root=operation_root(tmp_path);calls=0;original=subject.observe_run_bound_source_set
    def malformed(*args,**kwargs):
        nonlocal calls
        calls+=1
        return None if calls==call else original(*args,**kwargs)
    monkeypatch.setattr(subject,"observe_run_bound_source_set",malformed);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.accept_once(root)

def test_accepted_audit_uses_two_shared_validated_outer_source_reads(tmp_path,monkeypatch):
    root=_accepted(tmp_path,monkeypatch);calls=[];original=subject._observe_validated_source
    def observed(*args,**kwargs): value=original(*args,**kwargs);calls.append(value);return value
    monkeypatch.setattr(subject,"_observe_validated_source",observed);subject.audit(root,accepted_source=True)
    assert len(calls)==2 and calls[0]==calls[1]

def test_validated_source_reads_preserve_bound_identity(tmp_path,monkeypatch):
    root=operation_root(tmp_path);expected=subject.resolve_operation_root(root);seen=[];original=subject.observe_run_bound_source_set
    def observed(*args,**kwargs): seen.append((args,kwargs));return original(*args,**kwargs)
    monkeypatch.setattr(subject,"observe_run_bound_source_set",observed);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root)
    assert len(seen)==4 and all(args==(root/"source-set",) and kwargs=={"expected_root_identity":expected.source_identity} for args,kwargs in seen)

def test_registry_audit_does_not_read_source_context(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(subject,"_observe_validated_source",lambda *args,**kwargs:pytest.fail("unexpected source read"));subject.audit(root,accepted_source=False)
