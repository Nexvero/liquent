import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject

def test_success_captures_acceptance_state_before_final_validation(tmp_path,monkeypatch):
    root=operation_root(tmp_path);states=[];original_resolve=subject.resolve_operation_root;original_validate=subject.validate_operation_roots
    def observed(*args,**kwargs): value=original_resolve(*args,**kwargs);states.append(value.acceptance_state);return value
    def validated(target,expected,**kwargs): assert expected.acceptance_state==original_resolve(target).acceptance_state;return original_validate(target,expected,**kwargs)
    monkeypatch.setattr(subject,"resolve_operation_root",observed);monkeypatch.setattr(subject,"validate_operation_roots",validated);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root)
    assert len(states)==2 and states[0]!=states[1]

def test_success_rejects_change_after_captured_acceptance_state(tmp_path,monkeypatch):
    root=operation_root(tmp_path);registry=root/"accepted-runs";original=subject.validate_operation_roots
    def replacing(*args,**kwargs):
        marker=next(registry.iterdir());content=marker.read_bytes();marker.unlink();marker.write_bytes(content);marker.chmod(0o600)
        return original(*args,**kwargs)
    monkeypatch.setattr(subject,"validate_operation_roots",replacing);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.accept_once(root)

def test_failure_path_still_allows_recorded_acceptance_state_for_revalidation(tmp_path,monkeypatch):
    root=operation_root(tmp_path);original=subject.verify_and_accept
    def failing(*args,**kwargs): original(*args,**kwargs);raise ManifestHandoffRegistryUnavailable
    monkeypatch.setattr(subject,"verify_and_accept",failing);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.accept_once(root)

def test_stable_success_state_handoff_completes(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root)
    assert len(tuple((root/"accepted-runs").iterdir()))==1
