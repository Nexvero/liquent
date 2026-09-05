from dataclasses import replace
import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject
def _evidence(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root);source=subject.observe_run_bound_source_set(root/"source-set");marker=subject.observe_registry(root/"accepted-runs")[0];return source,marker

def _other(marker):
    run_id="87654321-4321-4321-8321-cba987654321";identity=(marker.marker_identity[0],marker.marker_identity[1]+1);state=(identity[0],identity[1],*marker.marker_state[2:])
    return replace(marker,acceptance=replace(marker.acceptance,run_id=run_id),marker_identity=identity,marker_state=state)

def test_registry_result_rejects_duplicate_run_and_generation(tmp_path,monkeypatch):
    _,marker=_evidence(tmp_path,monkeypatch)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.JointEngineApiRegistryAuditResult((marker.acceptance,marker.acceptance),(marker,marker))

def test_registry_result_rejects_noncanonical_run_order(tmp_path,monkeypatch):
    _,marker=_evidence(tmp_path,monkeypatch);other=_other(marker);ordered=tuple(sorted((marker,other),key=lambda value:value.acceptance.run_id));reversed_values=tuple(reversed(ordered))
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.JointEngineApiRegistryAuditResult(tuple(value.acceptance for value in reversed_values),reversed_values)
    assert len(subject.JointEngineApiRegistryAuditResult(tuple(value.acceptance for value in ordered),ordered).observations)==2

def test_accept_result_allows_one_source_acceptance_with_unrelated_marker(tmp_path,monkeypatch):
    source,marker=_evidence(tmp_path,monkeypatch);other=_other(marker);ordered=tuple(sorted((marker,other),key=lambda value:value.acceptance.run_id))
    assert subject.JointEngineApiAcceptResult(source,ordered).registry==ordered

def test_accept_result_rejects_duplicate_source_acceptance(tmp_path,monkeypatch):
    source,marker=_evidence(tmp_path,monkeypatch)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.JointEngineApiAcceptResult(source,(marker,marker))
