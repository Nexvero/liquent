import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_acceptance_audit as audit_subject
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject

def _accepted(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root);monkeypatch.setattr(audit_subject,"_utc_now",lambda:NOW);return root

def test_snapshot_verification_completion_requires_none(tmp_path,monkeypatch):
    root=operation_root(tmp_path);source=subject._observe_validated_source(root/"source-set",expected_root_identity=subject.resolve_operation_root(root).source_identity);monkeypatch.setattr(subject,"verify_run_bound_snapshot",lambda *args,**kwargs:object())
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject._verify_snapshot_completion(source.snapshot,now=NOW)

def test_accept_uses_two_snapshot_completion_checks(tmp_path,monkeypatch):
    root=operation_root(tmp_path);seen=[];original=subject._verify_snapshot_completion
    def verified(*args,**kwargs): value=original(*args,**kwargs);seen.append((args,kwargs));return value
    monkeypatch.setattr(subject,"_verify_snapshot_completion",verified);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root)
    assert len(seen)==2 and seen[0][0]==seen[1][0] and seen[0][1]==seen[1][1]=={"now":NOW}

@pytest.mark.parametrize("call",(1,2))
def test_accept_rejects_foreign_snapshot_completion_at_each_stage(tmp_path,monkeypatch,call):
    root=operation_root(tmp_path);calls=0;original=subject.verify_run_bound_snapshot
    def completed(*args,**kwargs):
        nonlocal calls
        calls+=1
        original(*args,**kwargs)
        return object() if calls==call else None
    monkeypatch.setattr(subject,"verify_run_bound_snapshot",completed);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.accept_once(root)
    assert len(tuple((root/"accepted-runs").iterdir()))==1

def test_accepted_audit_uses_one_outer_snapshot_completion(tmp_path,monkeypatch):
    root=_accepted(tmp_path,monkeypatch);seen=[];original=subject._verify_snapshot_completion
    def verified(*args,**kwargs): value=original(*args,**kwargs);seen.append((args,kwargs));return value
    monkeypatch.setattr(subject,"_verify_snapshot_completion",verified);subject.audit(root,accepted_source=True)
    assert len(seen)==1 and seen[0][1]=={"now":NOW}

def test_accepted_audit_rejects_foreign_snapshot_completion(tmp_path,monkeypatch):
    root=_accepted(tmp_path,monkeypatch);monkeypatch.setattr(subject,"verify_run_bound_snapshot",lambda *args,**kwargs:True)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.audit(root,accepted_source=True)

def test_normal_snapshot_verification_completion_is_none(tmp_path):
    root=operation_root(tmp_path);resolved=subject.resolve_operation_root(root);source=subject._observe_validated_source(root/"source-set",expected_root_identity=resolved.source_identity)
    assert subject._verify_snapshot_completion(source.snapshot,now=NOW) is None
