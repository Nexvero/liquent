from dataclasses import replace
import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_acceptance_audit as audit_subject
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject

def _accepted(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root);monkeypatch.setattr(audit_subject,"_utc_now",lambda:NOW);return root

def test_empty_registry_audit_result_is_closed_and_redacted():
    value=subject.JointEngineApiRegistryAuditResult((),())
    assert repr(value)=="JointEngineApiRegistryAuditResult()"

def test_registry_audit_result_rejects_value_observation_mismatch(tmp_path,monkeypatch):
    root=_accepted(tmp_path,monkeypatch);values=subject.inspect_registry(root/"accepted-runs");observations=subject.observe_registry(root/"accepted-runs")
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.JointEngineApiRegistryAuditResult((),observations)
    assert subject.JointEngineApiRegistryAuditResult(values,observations).values==values

def test_accepted_audit_result_rejects_wrong_correlated_marker(tmp_path,monkeypatch):
    root=_accepted(tmp_path,monkeypatch);source,marker=audit_subject.verify_accepted_current(root/"source-set",root/"accepted-runs");wrong=replace(marker,acceptance=replace(marker.acceptance,envelope_sha256="b"*64))
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.JointEngineApiAcceptedAuditResult(source,wrong,(marker,))
    assert repr(subject.JointEngineApiAcceptedAuditResult(source,marker,(marker,)))=="JointEngineApiAcceptedAuditResult()"

def test_operation_audits_use_closed_results(tmp_path,monkeypatch):
    root=_accepted(tmp_path,monkeypatch);subject.audit(root,accepted_source=False);subject.audit(root,accepted_source=True)
