import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_acceptance_audit as audit_subject
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject

def test_completed_runner_accepts_exact_none_once():
    calls=[]
    assert subject._run_completed_detail_free(lambda:calls.append(True)) is None
    assert calls==[True]

@pytest.mark.parametrize("value",(False,0,0.0,"",(),[],{},object()))
def test_completed_runner_rejects_every_non_none_value(value):
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject._run_completed_detail_free(lambda:value)

@pytest.mark.parametrize("api",("accept","registry-audit","accepted-audit"))
@pytest.mark.parametrize("value",(False,(),object()))
def test_direct_api_rejects_non_none_private_completion(tmp_path,monkeypatch,api,value):
    root=operation_root(tmp_path)
    if api=="accept": monkeypatch.setattr(subject,"_accept_once",lambda root:value);call=lambda:subject.accept_once(root)
    else: monkeypatch.setattr(subject,"_audit",lambda root,*,accepted_source:value);call=lambda:subject.audit(root,accepted_source=api=="accepted-audit")
    with pytest.raises(ManifestHandoffRegistryUnavailable): call()

def test_direct_completion_gate_preserves_unavailable_identity():
    error=ManifestHandoffRegistryUnavailable()
    def fail(): raise error
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught: subject._run_completed_detail_free(fail)
    assert caught.value is error

def test_valid_direct_completions_remain_none(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);monkeypatch.setattr(audit_subject,"_utc_now",lambda:NOW)
    assert subject.accept_once(root) is None and subject.audit(root,accepted_source=False) is None and subject.audit(root,accepted_source=True) is None
