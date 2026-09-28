from dataclasses import replace
import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_acceptance_audit as audit_subject
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject

def _evidence(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root);monkeypatch.setattr(audit_subject,"_utc_now",lambda:NOW);source,marker=audit_subject.verify_accepted_current(root/"source-set",root/"accepted-runs");return root,source,marker

def test_accepted_audit_result_retains_registry_context(tmp_path,monkeypatch):
    root,source,marker=_evidence(tmp_path,monkeypatch);registry=subject.observe_registry(root/"accepted-runs");result=subject.JointEngineApiAcceptedAuditResult(source,marker,registry)
    assert result.registry==registry and result.registry[0]==marker

def test_accepted_audit_result_rejects_missing_or_duplicate_marker(tmp_path,monkeypatch):
    _,source,marker=_evidence(tmp_path,monkeypatch)
    for registry in ((),(marker,marker)):
        with pytest.raises(ManifestHandoffRegistryUnavailable): subject.JointEngineApiAcceptedAuditResult(source,marker,registry)

def test_accepted_audit_result_rejects_unrelated_only_registry(tmp_path,monkeypatch):
    _,source,marker=_evidence(tmp_path,monkeypatch);other=replace(marker,acceptance=replace(marker.acceptance,run_id="87654321-4321-4321-8321-cba987654321"))
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.JointEngineApiAcceptedAuditResult(source,marker,(other,))

def test_accepted_audit_terminally_rechecks_registry_context(tmp_path,monkeypatch):
    root,_,_=_evidence(tmp_path,monkeypatch);seen=[];original=subject.observe_registry
    def observed(*args,**kwargs): value=original(*args,**kwargs);seen.append(value);return value
    monkeypatch.setattr(subject,"observe_registry",observed);subject.audit(root,accepted_source=True)
    assert len(seen)==3 and seen[0]==seen[1]==seen[2]

def test_accepted_audit_rejects_terminal_registry_context_drift(tmp_path,monkeypatch):
    root,_,_=_evidence(tmp_path,monkeypatch);calls=0;original=subject.observe_registry
    def observed(*args,**kwargs):
        nonlocal calls
        value=original(*args,**kwargs);calls+=1
        return () if calls==3 else value
    monkeypatch.setattr(subject,"observe_registry",observed)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.audit(root,accepted_source=True)
