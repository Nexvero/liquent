from dataclasses import replace
import base64,uuid
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_run import ManifestHandoffSupervisorEngineApiStagingRunAuthority,build_staging_signature_envelope,decode_staging_run_authority,decode_staging_signature_envelope,encode_staging_run_authority,encode_staging_signature_envelope,verify_staging_run_signature
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_trust import ManifestHandoffSupervisorEngineApiStagingTrust
from tests.test_lq1039_lq1050_engine_api_staging_receipt import materials

RUN="12345678-1234-4234-9234-123456789abc"
def signed(tmp_path):
    _,_,_,_,_,evidence,_,_=materials(tmp_path);key=Ed25519PrivateKey.generate();public=key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw);trust=ManifestHandoffSupervisorEngineApiStagingTrust("staging-a","staging-key-a",public);authority=ManifestHandoffSupervisorEngineApiStagingRunAuthority("staging-a","staging-key-a",RUN);envelope=encode_staging_signature_envelope(build_staging_signature_envelope(authority,evidence));signature=base64.b64encode(key.sign(envelope))+b"\n";return trust,authority,evidence,envelope,signature

def test_run_authority_is_canonical_and_secret_free():
    value=ManifestHandoffSupervisorEngineApiStagingRunAuthority("staging-a","staging-key-a",RUN);content=encode_staging_run_authority(value)
    assert decode_staging_run_authority(content)==value and repr(value)=="ManifestHandoffSupervisorEngineApiStagingRunAuthority()"

@pytest.mark.parametrize("run",("",RUN.upper(),"12345678-1234-1234-9234-123456789abc",str(uuid.uuid1())))
def test_run_authority_rejects_noncanonical_or_non_v4_run(run):
    with pytest.raises(ManifestHandoffRegistryUnavailable): ManifestHandoffSupervisorEngineApiStagingRunAuthority("staging-a","staging-key-a",run)

def test_envelope_is_canonical_and_binds_evidence(tmp_path):
    _,authority,evidence,envelope,_=signed(tmp_path);value=decode_staging_signature_envelope(envelope)
    assert value==build_staging_signature_envelope(authority,evidence) and repr(value)=="ManifestHandoffSupervisorEngineApiStagingSignatureEnvelope()"

@pytest.mark.parametrize("mutation",("run","environment","key","evidence","envelope","signature"))
def test_run_signature_rejects_every_binding_mismatch(tmp_path,mutation):
    trust,authority,evidence,envelope,signature=signed(tmp_path)
    if mutation=="run": authority=replace(authority,run_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    elif mutation=="environment": authority=replace(authority,environment_id="staging-b")
    elif mutation=="key": authority=replace(authority,key_id="staging-key-b")
    elif mutation=="evidence": evidence+=b"x"
    elif mutation=="envelope": envelope=envelope.replace(RUN.encode(),b"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    else: signature=base64.b64encode(b"x"*64)+b"\n"
    with pytest.raises(ManifestHandoffRegistryUnavailable): verify_staging_run_signature(trust,authority,evidence,envelope,signature)

def test_run_signature_verifies_exact_envelope(tmp_path):
    verify_staging_run_signature(*signed(tmp_path))
