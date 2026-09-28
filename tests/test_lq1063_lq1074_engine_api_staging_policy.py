from dataclasses import replace
import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_trust import ManifestHandoffSupervisorEngineApiStagingVerificationPolicy,decode_manifest_handoff_supervisor_engine_api_staging_verification_policy,encode_manifest_handoff_supervisor_engine_api_staging_verification_policy,write_manifest_handoff_supervisor_engine_api_provenance_receipt
from tools import engine_api_joint_staging_provenance_snapshot as subject
from tools.engine_api_joint_staging_policy_verify import verify
from tests.test_lq1039_lq1050_engine_api_staging_receipt import materials,NOW

def setup(tmp_path,evidence_age=3600,receipt_age=3600):
    trust,signature,evidence,artifacts,_,_,_,receipt=materials(tmp_path);receipt_file=tmp_path/"receipt";write_manifest_handoff_supervisor_engine_api_provenance_receipt(receipt_file.resolve(),receipt);policy=ManifestHandoffSupervisorEngineApiStagingVerificationPolicy("staging-a","staging-key-a",evidence_age,receipt_age);policy_file=tmp_path/"verification-policy";policy_file.write_bytes(encode_manifest_handoff_supervisor_engine_api_staging_verification_policy(policy));policy_file.chmod(0o600)
    return policy_file.resolve(),trust,signature,evidence,receipt_file.resolve(),artifacts

def test_policy_is_canonical_and_secret_free():
    value=ManifestHandoffSupervisorEngineApiStagingVerificationPolicy("staging-a","staging-key-a",1800,900);content=encode_manifest_handoff_supervisor_engine_api_staging_verification_policy(value)
    assert decode_manifest_handoff_supervisor_engine_api_staging_verification_policy(content)==value and repr(value)=="ManifestHandoffSupervisorEngineApiStagingVerificationPolicy()"

@pytest.mark.parametrize("content",(b"",b"environment_id=staging-a\n",b"environment_id=staging-a\nkey_id=staging-key-a\nevidence_max_age_seconds=01\nreceipt_max_age_seconds=1\n",b"key_id=staging-key-a\nenvironment_id=staging-a\nevidence_max_age_seconds=1\nreceipt_max_age_seconds=1\n"))
def test_policy_rejects_absence_partial_noncanonical_or_reordered(content):
    with pytest.raises(ManifestHandoffRegistryUnavailable): decode_manifest_handoff_supervisor_engine_api_staging_verification_policy(content)

@pytest.mark.parametrize("index",range(10))
def test_policy_snapshot_rejects_all_path_aliases(tmp_path,index):
    policy,trust,signature,evidence,receipt,artifacts=setup(tmp_path);paths=[policy,trust,signature,evidence,receipt,*artifacts];paths[index]=paths[(index+1)%10]
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.load_policy_bound_snapshot(*paths)

@pytest.mark.parametrize("mutation",("environment","key","evidence-age","receipt-age","non-utc"))
def test_policy_bound_verifier_rejects_mismatch_or_expiry(tmp_path,mutation):
    policy,trust,signature,evidence,receipt,artifacts=setup(tmp_path,1 if mutation=="evidence-age" else 3600,1 if mutation=="receipt-age" else 3600);snapshot=subject.load_policy_bound_snapshot(policy,trust,signature,evidence,receipt,*artifacts);now=NOW
    if mutation in ("environment","key"):
        parsed=decode_manifest_handoff_supervisor_engine_api_staging_verification_policy(snapshot.policy);parsed=replace(parsed,**{mutation+"_id":"staging-b" if mutation=="environment" else "staging-key-b"});snapshot=replace(snapshot,policy=encode_manifest_handoff_supervisor_engine_api_staging_verification_policy(parsed))
    elif mutation=="non-utc": now=NOW.astimezone(__import__("datetime").timezone(__import__("datetime").timedelta(hours=1)))
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.verify_policy_bound_snapshot(snapshot,now=now)

def test_policy_bound_end_verifier_has_no_caller_age_override(tmp_path):
    policy,trust,signature,evidence,receipt,artifacts=setup(tmp_path);verify(policy,trust,signature,evidence,receipt,*artifacts,now=NOW)
