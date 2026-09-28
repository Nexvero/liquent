from pathlib import Path
import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_evidence import ManifestHandoffSupervisorEngineApiStagingEvidence, encode_manifest_handoff_supervisor_engine_api_staging_evidence, decode_manifest_handoff_supervisor_engine_api_staging_evidence, write_manifest_handoff_supervisor_engine_api_staging_evidence
from tools.engine_api_joint_staging_evidence_verify import verify

def evidence(**changes):
    values={"schema_version":1,"environment_id":"staging-a","observed_at":"2026-08-29T12:00:00Z","image_digest":"sha256:"+"a"*64,"render_sha256":"1"*64,"inspect_sha256":"2"*64,"health_sha256":"3"*64,"policy_sha256":"4"*64,"shutdown_sha256":"5"*64}; values.update(changes); return ManifestHandoffSupervisorEngineApiStagingEvidence(**values)

def test_canonical_round_trip_is_detail_free():
    value=evidence(); content=encode_manifest_handoff_supervisor_engine_api_staging_evidence(value)
    assert decode_manifest_handoff_supervisor_engine_api_staging_evidence(content)==value
    assert repr(value)=="ManifestHandoffSupervisorEngineApiStagingEvidence()"

@pytest.mark.parametrize("change", ({"schema_version":2},{"environment_id":"Staging"},{"observed_at":"2026-08-29"},{"image_digest":"a"*64},{"shutdown_sha256":"1"*64}))
def test_invalid_or_ambiguous_evidence_is_rejected(change):
    with pytest.raises(ManifestHandoffRegistryUnavailable): evidence(**change)

def test_noncanonical_json_is_rejected():
    content=encode_manifest_handoff_supervisor_engine_api_staging_evidence(evidence())
    with pytest.raises(ManifestHandoffRegistryUnavailable): decode_manifest_handoff_supervisor_engine_api_staging_evidence(b" " + content)

def test_owner_private_immutable_write_and_verify(tmp_path):
    path=tmp_path/"evidence.json"; write_manifest_handoff_supervisor_engine_api_staging_evidence(path.resolve(), evidence())
    assert path.stat().st_mode & 0o777 == 0o600; verify(path.resolve())
    with pytest.raises(ManifestHandoffRegistryUnavailable): write_manifest_handoff_supervisor_engine_api_staging_evidence(path.resolve(), evidence())

def test_verifier_rejects_mode_and_link(tmp_path):
    path=tmp_path/"evidence.json"; write_manifest_handoff_supervisor_engine_api_staging_evidence(path.resolve(), evidence()); path.chmod(0o640)
    with pytest.raises(ManifestHandoffRegistryUnavailable): verify(path.resolve())
