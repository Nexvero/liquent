import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1135_lq1146_engine_api_run_acceptance import roots
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as operation_subject

def test_one_shot_returns_final_marker_observation(tmp_path,monkeypatch):
    source,registry=roots(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);created=accept_subject.verify_and_accept(source,registry)
    assert created.acceptance.run_id and created.marker_state[:2]==created.marker_identity

def test_operation_delta_matches_exact_one_shot_observation(tmp_path,monkeypatch):
    root=operation_root(tmp_path);created=[];original=operation_subject.verify_and_accept
    def observed(*args,**kwargs): value=original(*args,**kwargs);created.append(value);return value
    monkeypatch.setattr(operation_subject,"verify_and_accept",observed);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);operation_subject.accept_once(root)
    assert len(created)==1

def test_operation_rejects_new_marker_replacement_after_one_shot(tmp_path,monkeypatch):
    root=operation_root(tmp_path);registry=root/"accepted-runs";original=operation_subject.verify_and_accept
    def replacing(*args,**kwargs):
        created=original(*args,**kwargs);marker=next(registry.iterdir());content=marker.read_bytes();marker.unlink();marker.write_bytes(content);marker.chmod(0o600);return created
    monkeypatch.setattr(operation_subject,"verify_and_accept",replacing);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): operation_subject.accept_once(root)

def test_stable_created_marker_handoff_completes(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);operation_subject.accept_once(root);assert len(list((root/"accepted-runs").iterdir()))==1
