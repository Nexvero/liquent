import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_acceptance import ManifestHandoffSupervisorEngineApiStagingRunAcceptance, encode_staging_run_acceptance
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1123_lq1134_engine_api_run_bound_root import RUN
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as operation_subject


def test_operation_accept_observes_bound_source_for_expected_delta(tmp_path,monkeypatch):
    root=operation_root(tmp_path);seen=[];original=operation_subject.observe_run_bound_source_set
    def observed(path,**kwargs): seen.append((path,kwargs));return original(path,**kwargs)
    monkeypatch.setattr(operation_subject,"observe_run_bound_source_set",observed);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);operation_subject.accept_once(root)
    assert len(seen)==4 and all(value[0]==root/"source-set" for value in seen) and seen[0][1]==seen[1][1]==seen[2][1]==seen[3][1] and seen[0][1]["expected_root_identity"] is not None


def test_operation_accept_rejects_canonical_marker_for_different_run(tmp_path,monkeypatch):
    root=operation_root(tmp_path);registry=root/"accepted-runs";original=operation_subject.verify_and_accept;other="87654321-4321-4321-8321-cba987654321"
    def replacing(source,acceptance,**kwargs):
        original(source,acceptance,**kwargs)
        for marker in registry.iterdir(): marker.unlink()
        value=ManifestHandoffSupervisorEngineApiStagingRunAcceptance(1,other,"b"*64);path=registry/(other+".accepted");path.write_bytes(encode_staging_run_acceptance(value));path.chmod(0o600)
    monkeypatch.setattr(operation_subject,"verify_and_accept",replacing);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): operation_subject.accept_once(root)


def test_operation_accept_rejects_same_run_with_wrong_envelope_hash(tmp_path,monkeypatch):
    root=operation_root(tmp_path);registry=root/"accepted-runs";original=operation_subject.verify_and_accept
    def replacing(source,acceptance,**kwargs):
        original(source,acceptance,**kwargs);marker=next(registry.iterdir());marker.unlink();value=ManifestHandoffSupervisorEngineApiStagingRunAcceptance(1,RUN,"b"*64);marker.write_bytes(encode_staging_run_acceptance(value));marker.chmod(0o600)
    monkeypatch.setattr(operation_subject,"verify_and_accept",replacing);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): operation_subject.accept_once(root)


def test_operation_accept_allows_exact_source_derived_acceptance(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);operation_subject.accept_once(root);assert next((root/"accepted-runs").iterdir()).name==RUN+".accepted"
