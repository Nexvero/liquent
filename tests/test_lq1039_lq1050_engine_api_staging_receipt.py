from datetime import datetime,timezone
import base64,hashlib
from pathlib import Path
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_evidence import ManifestHandoffSupervisorEngineApiStagingEvidence,write_manifest_handoff_supervisor_engine_api_staging_evidence
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_trust import build_manifest_handoff_supervisor_engine_api_provenance_receipt,decode_manifest_handoff_supervisor_engine_api_provenance_receipt,encode_manifest_handoff_supervisor_engine_api_provenance_receipt,load_manifest_handoff_supervisor_engine_api_staging_trust,verify_manifest_handoff_supervisor_engine_api_provenance_receipt,write_manifest_handoff_supervisor_engine_api_provenance_receipt
from tools.engine_api_joint_staging_receipt_verify import verify

NOW=datetime(2026,8,29,12,30,tzinfo=timezone.utc)
def materials(tmp_path):
    key=Ed25519PrivateKey.generate();public=key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw);trust_file=tmp_path/"trust";trust_file.write_bytes(b"environment_id=staging-a\nkey_id=staging-key-a\ned25519_public_key="+base64.b64encode(public)+b"\n");trust_file.chmod(0o600);trust=load_manifest_handoff_supervisor_engine_api_staging_trust(trust_file.resolve())
    values=(b"render",b"inspect",b"health",b"policy",b"shutdown");artifacts=[]
    for index,value in enumerate(values): path=tmp_path/f"a{index}";path.write_bytes(value);path.chmod(0o600);artifacts.append(path.resolve())
    evidence_file=tmp_path/"evidence";hashes=[hashlib.sha256(value).hexdigest() for value in values];write_manifest_handoff_supervisor_engine_api_staging_evidence(evidence_file.resolve(),ManifestHandoffSupervisorEngineApiStagingEvidence(1,"staging-a","2026-08-29T12:00:00Z","sha256:"+"a"*64,*hashes));evidence=evidence_file.read_bytes()
    signature_file=tmp_path/"signature";signature=base64.b64encode(key.sign(evidence))+b"\n";signature_file.write_bytes(signature);signature_file.chmod(0o600)
    receipt=build_manifest_handoff_supervisor_engine_api_provenance_receipt(trust,evidence,signature,"2026-08-29T12:15:00Z")
    return trust_file.resolve(),signature_file.resolve(),evidence_file.resolve(),artifacts,trust,evidence,signature,receipt

def test_receipt_round_trip_and_owner_private_write(tmp_path):
    *_,receipt=materials(tmp_path);target=(tmp_path/"receipt").resolve();write_manifest_handoff_supervisor_engine_api_provenance_receipt(target,receipt)
    assert decode_manifest_handoff_supervisor_engine_api_provenance_receipt(target.read_bytes())==receipt and target.stat().st_mode&0o777==0o600
    with pytest.raises(ManifestHandoffRegistryUnavailable): write_manifest_handoff_supervisor_engine_api_provenance_receipt(target,receipt)

@pytest.mark.parametrize("mutation",("extra","noncanonical","mode"))
def test_receipt_source_rejects_mutation(tmp_path,mutation):
    trust_file,signature_file,evidence_file,artifacts,_,_,_,receipt=materials(tmp_path);content=encode_manifest_handoff_supervisor_engine_api_provenance_receipt(receipt)
    if mutation=="extra": content=content[:-2]+b',"extra":1}\n'
    elif mutation=="noncanonical": content=content.replace(b'":',b'": ')
    else:
        target=tmp_path/"receipt";write_manifest_handoff_supervisor_engine_api_provenance_receipt(target.resolve(),receipt);target.chmod(0o640)
        with pytest.raises(ManifestHandoffRegistryUnavailable): verify(trust_file,signature_file,evidence_file,target.resolve(),*artifacts,maximum_age_seconds=3600,now=NOW)
        return
    with pytest.raises(ManifestHandoffRegistryUnavailable): decode_manifest_handoff_supervisor_engine_api_provenance_receipt(content)

@pytest.mark.parametrize("mutation",("environment","key","evidence-hash","signature-hash","future","stale"))
def test_receipt_verification_fails_closed(tmp_path,mutation):
    *_,trust,evidence,signature,receipt=materials(tmp_path)
    values={name:getattr(receipt,name) for name in receipt.__dataclass_fields__}
    if mutation=="environment": values["environment_id"]="staging-b"
    elif mutation=="key": values["key_id"]="staging-key-b"
    elif mutation=="evidence-hash": values["evidence_sha256"]="0"*64
    elif mutation=="signature-hash": values["signature_sha256"]="0"*64
    elif mutation=="future": values["verified_at"]="2026-08-29T13:00:00Z"
    else: values["verified_at"]="2026-08-29T10:00:00Z"
    receipt=type(receipt)(**values)
    with pytest.raises(ManifestHandoffRegistryUnavailable): verify_manifest_handoff_supervisor_engine_api_provenance_receipt(trust,evidence,signature,receipt,now=NOW,maximum_age_seconds=3600)

def test_combined_receipt_verifier_binds_every_file(tmp_path):
    trust,signature,evidence,artifacts,_,_,_,receipt=materials(tmp_path);receipt_file=tmp_path/"receipt";write_manifest_handoff_supervisor_engine_api_provenance_receipt(receipt_file.resolve(),receipt)
    verify(trust,signature,evidence,receipt_file.resolve(),*artifacts,maximum_age_seconds=3600,now=NOW)
