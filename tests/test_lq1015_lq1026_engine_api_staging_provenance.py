from datetime import datetime,timezone
import base64,hashlib
from pathlib import Path
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_evidence import ManifestHandoffSupervisorEngineApiStagingEvidence,write_manifest_handoff_supervisor_engine_api_staging_evidence
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_trust import load_manifest_handoff_supervisor_engine_api_staging_trust,verify_manifest_handoff_supervisor_engine_api_staging_signature
from tools.engine_api_joint_staging_provenance_verify import verify

def files(tmp_path):
    key=Ed25519PrivateKey.generate(); public=key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
    trust=tmp_path/"trust"; trust.write_text(f"environment_id=staging-a\nkey_id=staging-key-a\ned25519_public_key={base64.b64encode(public).decode()}\n"); trust.chmod(0o600)
    contents=(b"render",b"inspect",b"health",b"policy",b"shutdown"); artifacts=[]
    for i,value in enumerate(contents): p=tmp_path/f"a{i}";p.write_bytes(value);p.chmod(0o600);artifacts.append(p.resolve())
    hashes=[hashlib.sha256(v).hexdigest() for v in contents]
    evidence=tmp_path/"evidence";write_manifest_handoff_supervisor_engine_api_staging_evidence(evidence.resolve(),ManifestHandoffSupervisorEngineApiStagingEvidence(1,"staging-a","2026-08-29T12:00:00Z","sha256:"+"a"*64,*hashes))
    signature=tmp_path/"signature";signature.write_bytes(base64.b64encode(key.sign(evidence.read_bytes()))+b"\n");signature.chmod(0o600)
    return trust.resolve(),signature.resolve(),evidence.resolve(),artifacts

def test_fixed_trust_and_detached_signature_verify(tmp_path):
    trust,signature,evidence,_=files(tmp_path); value=load_manifest_handoff_supervisor_engine_api_staging_trust(trust)
    assert value.environment_id=="staging-a" and repr(value)=="ManifestHandoffSupervisorEngineApiStagingTrust()"
    verify_manifest_handoff_supervisor_engine_api_staging_signature(value,evidence.read_bytes(),signature)

@pytest.mark.parametrize("mutation",("signature","evidence","trust-mode","signature-mode"))
def test_signature_or_private_source_mutation_fails(tmp_path,mutation):
    trust,signature,evidence,_=files(tmp_path)
    if mutation=="signature": signature.write_bytes(base64.b64encode(b"x"*64)+b"\n")
    elif mutation=="evidence": evidence.write_bytes(evidence.read_bytes()+b" ")
    elif mutation=="trust-mode": trust.chmod(0o640)
    else: signature.chmod(0o640)
    with pytest.raises(ManifestHandoffRegistryUnavailable): verify_manifest_handoff_supervisor_engine_api_staging_signature(load_manifest_handoff_supervisor_engine_api_staging_trust(trust),evidence.read_bytes(),signature)

def test_combined_provenance_verifier_binds_all_layers(tmp_path):
    trust,signature,evidence,artifacts=files(tmp_path)
    verify(trust,signature,evidence,*artifacts,maximum_age_seconds=3600,now=datetime(2026,8,29,12,30,tzinfo=timezone.utc))

def test_combined_verifier_rejects_wrong_artifact(tmp_path):
    trust,signature,evidence,artifacts=files(tmp_path);artifacts[0].write_bytes(b"wrong")
    with pytest.raises(ManifestHandoffRegistryUnavailable): verify(trust,signature,evidence,*artifacts,maximum_age_seconds=3600,now=datetime(2026,8,29,12,30,tzinfo=timezone.utc))
