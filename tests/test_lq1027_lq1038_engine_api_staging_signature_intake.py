from datetime import datetime,timezone
import base64
from pathlib import Path
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_trust import ManifestHandoffSupervisorEngineApiStagingTrust,build_manifest_handoff_supervisor_engine_api_provenance_receipt,decode_manifest_handoff_supervisor_engine_api_staging_signature,encode_manifest_handoff_supervisor_engine_api_provenance_receipt,write_verified_manifest_handoff_supervisor_engine_api_staging_signature

def materials():
    key=Ed25519PrivateKey.generate();public=key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
    trust=ManifestHandoffSupervisorEngineApiStagingTrust("staging-a","staging-key-a",public);evidence=b'{"canonical":"evidence"}\n';content=base64.b64encode(key.sign(evidence))+b"\n"
    return trust,evidence,content

def test_external_signature_is_canonical_and_secret_free():
    _,_,content=materials();assert len(decode_manifest_handoff_supervisor_engine_api_staging_signature(content))==64
    with pytest.raises(ManifestHandoffRegistryUnavailable): decode_manifest_handoff_supervisor_engine_api_staging_signature(content.rstrip())

def test_verified_signature_is_materialized_once_owner_private(tmp_path):
    trust,evidence,content=materials();target=(tmp_path/"signature").resolve()
    write_verified_manifest_handoff_supervisor_engine_api_staging_signature(target,trust,evidence,content)
    assert target.read_bytes()==content and target.stat().st_mode&0o777==0o600
    with pytest.raises(ManifestHandoffRegistryUnavailable): write_verified_manifest_handoff_supervisor_engine_api_staging_signature(target,trust,evidence,content)

@pytest.mark.parametrize("mutation",("evidence","signature","relative"))
def test_materialization_fails_closed_without_partial_target(tmp_path,mutation):
    trust,evidence,content=materials();target=(tmp_path/"signature").resolve()
    if mutation=="evidence": evidence+=b"x"
    elif mutation=="signature": content=base64.b64encode(b"x"*64)+b"\n"
    else: target=Path("signature")
    with pytest.raises(ManifestHandoffRegistryUnavailable): write_verified_manifest_handoff_supervisor_engine_api_staging_signature(target,trust,evidence,content)
    if target.is_absolute(): assert not target.exists()

def test_receipt_binds_trust_evidence_signature_and_time():
    trust,evidence,content=materials();receipt=build_manifest_handoff_supervisor_engine_api_provenance_receipt(trust,evidence,content,"2026-08-29T12:00:00Z")
    encoded=encode_manifest_handoff_supervisor_engine_api_provenance_receipt(receipt)
    assert receipt.environment_id=="staging-a" and receipt.key_id=="staging-key-a" and encoded.endswith(b"\n") and repr(receipt)=="ManifestHandoffSupervisorEngineApiProvenanceReceipt()"

def test_receipt_rejects_unverified_or_non_utc_input():
    trust,evidence,content=materials()
    with pytest.raises(ManifestHandoffRegistryUnavailable): build_manifest_handoff_supervisor_engine_api_provenance_receipt(trust,evidence,base64.b64encode(b"x"*64)+b"\n","2026-08-29T12:00:00Z")
    with pytest.raises(ManifestHandoffRegistryUnavailable): build_manifest_handoff_supervisor_engine_api_provenance_receipt(trust,evidence,content,"2026-08-29T12:00:00+01:00")
