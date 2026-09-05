import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject

@pytest.mark.parametrize("created",(None,(),object()))
def test_accept_rejects_non_observation_handoff_before_after_inventory(tmp_path,monkeypatch,created):
    root=operation_root(tmp_path);reads=[];original_observe=subject.observe_registry
    def observed(*args,**kwargs): value=original_observe(*args,**kwargs);reads.append(value);return value
    monkeypatch.setattr(subject,"observe_registry",observed);monkeypatch.setattr(subject,"verify_and_accept",lambda *args,**kwargs:created)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.accept_once(root)
    assert reads==[()]

def test_accept_rejects_acceptance_value_without_observation(tmp_path,monkeypatch):
    root=operation_root(tmp_path);source=subject.observe_run_bound_source_set(root/"source-set");authority=subject.decode_staging_run_authority(source.snapshot.run_authority);value=subject.build_staging_run_acceptance(authority,source.snapshot.run_envelope)
    monkeypatch.setattr(subject,"verify_and_accept",lambda *args,**kwargs:value)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.accept_once(root)

def test_accept_rejects_foreign_handoff_after_real_mutation(tmp_path,monkeypatch):
    root=operation_root(tmp_path);original=subject.verify_and_accept
    def changed(*args,**kwargs): original(*args,**kwargs);return object()
    monkeypatch.setattr(subject,"verify_and_accept",changed);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.accept_once(root)
    assert len(tuple((root/"accepted-runs").iterdir()))==1

def test_exact_acceptance_observation_handoff_completes(tmp_path,monkeypatch):
    root=operation_root(tmp_path);seen=[];original=subject.verify_and_accept
    def observed(*args,**kwargs): value=original(*args,**kwargs);seen.append(value);return value
    monkeypatch.setattr(subject,"verify_and_accept",observed);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root)
    assert len(seen)==1 and type(seen[0]) is subject.ManifestHandoffSupervisorEngineApiStagingRunAcceptanceObservation
