import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject

def _raises(error):
    def fail(*args,**kwargs): raise error
    return fail

@pytest.mark.parametrize("api",("accept","registry-audit","accepted-audit"))
def test_direct_api_normalizes_ordinary_technical_failure(tmp_path,monkeypatch,api):
    root=operation_root(tmp_path)
    if api=="accept": monkeypatch.setattr(subject,"resolve_operation_root",_raises(ValueError("secret")));call=lambda:subject.accept_once(root)
    elif api=="registry-audit": monkeypatch.setattr(subject,"inspect_registry",_raises(OSError("secret")));call=lambda:subject.audit(root,accepted_source=False)
    else: monkeypatch.setattr(subject,"verify_accepted_current",_raises(RuntimeError("secret")));call=lambda:subject.audit(root,accepted_source=True)
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught: call()
    assert caught.value.__cause__ is None

@pytest.mark.parametrize("api",("accept","audit"))
def test_direct_api_preserves_existing_unavailable(tmp_path,monkeypatch,api):
    root=operation_root(tmp_path);error=ManifestHandoffRegistryUnavailable();monkeypatch.setattr(subject,"resolve_operation_root",_raises(error))
    call=(lambda:subject.accept_once(root)) if api=="accept" else (lambda:subject.audit(root,accepted_source=False))
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught: call()
    assert caught.value is error

@pytest.mark.parametrize("error",(KeyboardInterrupt(),SystemExit()))
def test_direct_boundary_does_not_swallow_system_exit(error):
    with pytest.raises(type(error)) as caught: subject._run_detail_free(_raises(error))
    assert caught.value is error

def test_late_accept_failure_is_normalized_without_rollback(tmp_path,monkeypatch):
    root=operation_root(tmp_path);calls=0;monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW)
    def clock():
        nonlocal calls
        calls+=1
        if calls==2: raise ValueError("secret")
        return NOW
    monkeypatch.setattr(subject,"_accept_utc_now",clock)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.accept_once(root)
    assert len(tuple((root/"accepted-runs").iterdir()))==1

def test_valid_direct_operations_remain_unchanged(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);assert subject.accept_once(root) is None;assert subject.audit(root,accepted_source=False) is None
