from dataclasses import FrozenInstanceError,replace
import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject

def _evidence(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root);source=subject.observe_run_bound_source_set(root/"source-set");marker=subject.observe_registry(root/"accepted-runs")[0];return source,marker

def test_accept_result_derives_created_marker(tmp_path,monkeypatch):
    source,marker=_evidence(tmp_path,monkeypatch);result=subject.JointEngineApiAcceptResult(source,(marker,))
    assert result.created is marker and result.created in result.registry

def test_accept_result_created_marker_is_not_caller_supplied(tmp_path,monkeypatch):
    source,marker=_evidence(tmp_path,monkeypatch)
    with pytest.raises(TypeError): subject.JointEngineApiAcceptResult(source,(marker,),marker)

def test_accept_result_created_marker_is_immutable(tmp_path,monkeypatch):
    source,marker=_evidence(tmp_path,monkeypatch);result=subject.JointEngineApiAcceptResult(source,(marker,))
    with pytest.raises(FrozenInstanceError): result.created=marker

def test_accept_result_rejects_only_unrelated_marker(tmp_path,monkeypatch):
    source,marker=_evidence(tmp_path,monkeypatch);other=replace(marker,acceptance=replace(marker.acceptance,run_id="87654321-4321-4321-8321-cba987654321"))
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.JointEngineApiAcceptResult(source,(other,))
