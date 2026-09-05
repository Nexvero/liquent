import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_acceptance import ManifestHandoffSupervisorEngineApiStagingRunAcceptance,encode_staging_run_acceptance,observe_staging_run_acceptance_registry
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as operation_subject

def test_registry_observation_inventory_contains_marker_generation(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);operation_subject.accept_once(root);values=observe_staging_run_acceptance_registry(root/"accepted-runs")
    assert len(values)==1 and values[0].marker_state[:2]==values[0].marker_identity

def test_operation_accept_uses_observation_inventory_before_and_after(tmp_path,monkeypatch):
    root=operation_root(tmp_path);seen=[];original=operation_subject.observe_registry
    def observed(path,**kwargs): value=original(path,**kwargs);seen.append(value);return value
    monkeypatch.setattr(operation_subject,"observe_registry",observed);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);operation_subject.accept_once(root)
    assert len(seen)==4 and len(seen[0])==0 and len(seen[1])==1 and seen[1]==seen[2]==seen[3]

def test_operation_accept_rejects_replaced_existing_marker_generation(tmp_path,monkeypatch):
    root=operation_root(tmp_path);registry=root/"accepted-runs";other="87654321-4321-4321-8321-cba987654321";old=registry/(other+".accepted");old.write_bytes(encode_staging_run_acceptance(ManifestHandoffSupervisorEngineApiStagingRunAcceptance(1,other,"b"*64)));old.chmod(0o600);original=operation_subject.verify_and_accept
    def replacing(source,acceptance,**kwargs):
        original(source,acceptance,**kwargs);content=old.read_bytes();old.unlink();old.write_bytes(content);old.chmod(0o600)
    monkeypatch.setattr(operation_subject,"verify_and_accept",replacing);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): operation_subject.accept_once(root)
