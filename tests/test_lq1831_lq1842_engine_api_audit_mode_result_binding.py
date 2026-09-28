import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_acceptance_audit as audit_subject
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject

@pytest.mark.parametrize("mode",(None,0,1,"",object()))
def test_audit_rejects_non_boolean_mode(tmp_path,mode):
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.audit(operation_root(tmp_path),accepted_source=mode)

def _accepted(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root);monkeypatch.setattr(audit_subject,"_utc_now",lambda:NOW);return root

def _swap_result(monkeypatch,replacement):
    original=subject._within_operation_roots
    def within(path,operation,**kwargs):
        def changed(resolved): operation(resolved);return replacement(resolved)
        return original(path,changed,**kwargs)
    monkeypatch.setattr(subject,"_within_operation_roots",within)

def test_registry_mode_rejects_accepted_result(tmp_path,monkeypatch):
    root=_accepted(tmp_path,monkeypatch)
    def replacement(resolved):
        source,marker=subject.verify_accepted_current(resolved.source_root,resolved.acceptance_root,expected_source_identity=resolved.source_identity,expected_acceptance_identity=resolved.acceptance_identity)
        return subject.JointEngineApiAcceptedAuditResult(source,marker,subject.observe_registry(resolved.acceptance_root,expected_acceptance_identity=resolved.acceptance_identity))
    _swap_result(monkeypatch,replacement)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.audit(root,accepted_source=False)

def test_accepted_mode_rejects_registry_result(tmp_path,monkeypatch):
    root=_accepted(tmp_path,monkeypatch)
    def replacement(resolved):
        observations=subject.observe_registry(resolved.acceptance_root,expected_acceptance_identity=resolved.acceptance_identity)
        return subject.JointEngineApiRegistryAuditResult(tuple(value.acceptance for value in observations),observations)
    _swap_result(monkeypatch,replacement)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.audit(root,accepted_source=True)

@pytest.mark.parametrize("mode",(False,True))
def test_exact_boolean_audit_modes_complete(tmp_path,monkeypatch,mode):
    root=_accepted(tmp_path,monkeypatch);subject.audit(root,accepted_source=mode)
