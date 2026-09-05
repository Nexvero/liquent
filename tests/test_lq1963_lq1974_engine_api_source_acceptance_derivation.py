import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject

def _source(tmp_path):
    root=operation_root(tmp_path);resolved=subject.resolve_operation_root(root);return root,subject._observe_validated_source(root/"source-set",expected_root_identity=resolved.source_identity)

def test_source_acceptance_derivation_returns_exact_authority_and_value(tmp_path):
    _,source=_source(tmp_path);authority,acceptance=subject._derive_source_acceptance(source)
    assert type(authority) is subject.ManifestHandoffSupervisorEngineApiStagingRunAuthority and type(acceptance) is subject.ManifestHandoffSupervisorEngineApiStagingRunAcceptance and authority.run_id==acceptance.run_id

@pytest.mark.parametrize("source",(None,(),object()))
def test_source_acceptance_derivation_rejects_foreign_source(source):
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject._derive_source_acceptance(source)

def test_source_acceptance_derivation_rejects_foreign_authority(tmp_path,monkeypatch):
    _,source=_source(tmp_path);monkeypatch.setattr(subject,"decode_staging_run_authority",lambda value:object())
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject._derive_source_acceptance(source)

def test_source_acceptance_derivation_rejects_foreign_acceptance(tmp_path,monkeypatch):
    _,source=_source(tmp_path);monkeypatch.setattr(subject,"build_staging_run_acceptance",lambda *args,**kwargs:object())
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject._derive_source_acceptance(source)

def test_accept_uses_shared_source_acceptance_derivation(tmp_path,monkeypatch):
    root=operation_root(tmp_path);seen=[];original=subject._derive_source_acceptance
    def derived(value): result=original(value);seen.append(result);return result
    monkeypatch.setattr(subject,"_derive_source_acceptance",derived);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root)
    assert len(seen)>=2 and all(type(value[0]) is subject.ManifestHandoffSupervisorEngineApiStagingRunAuthority and type(value[1]) is subject.ManifestHandoffSupervisorEngineApiStagingRunAcceptance for value in seen)

def test_source_acceptance_derivation_failure_is_detail_free(tmp_path,monkeypatch):
    _,source=_source(tmp_path);monkeypatch.setattr(subject,"decode_staging_run_authority",lambda value:None)
    with pytest.raises(ManifestHandoffRegistryUnavailable) as failure: subject._derive_source_acceptance(source)
    assert str(failure.value)=="manifest_handoff_registry_unavailable"
