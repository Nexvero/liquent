import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject

def _evidence(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root);source=subject.observe_run_bound_source_set(root/"source-set");registry=subject.observe_registry(root/"accepted-runs");return root,source,registry

def test_accept_result_is_closed_and_redacted(tmp_path,monkeypatch):
    _,source,registry=_evidence(tmp_path,monkeypatch);value=subject.JointEngineApiAcceptResult(source,registry)
    assert repr(value)=="JointEngineApiAcceptResult()" and value.registry==registry

def test_accept_result_rejects_missing_source_acceptance(tmp_path,monkeypatch):
    _,source,_=_evidence(tmp_path,monkeypatch)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.JointEngineApiAcceptResult(source,())

def test_accept_result_rejects_malformed_registry_shape(tmp_path,monkeypatch):
    _,source,registry=_evidence(tmp_path,monkeypatch)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.JointEngineApiAcceptResult(source,list(registry))

def test_accept_once_uses_closed_result_in_success_check(tmp_path,monkeypatch):
    root=operation_root(tmp_path);seen=[];original=subject._within_operation_roots
    def within(path,operation,**kwargs):
        check=kwargs["success_check"]
        def observed(resolved,result): seen.append(result);return check(resolved,result)
        return original(path,operation,**{**kwargs,"success_check":observed})
    monkeypatch.setattr(subject,"_within_operation_roots",within);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root)
    assert len(seen)==1 and type(seen[0]) is subject.JointEngineApiAcceptResult
