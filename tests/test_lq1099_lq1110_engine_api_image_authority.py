from dataclasses import replace
import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_trust import ManifestHandoffSupervisorEngineApiStagingImageAuthority,decode_manifest_handoff_supervisor_engine_api_staging_image_authority,encode_manifest_handoff_supervisor_engine_api_staging_image_authority
from tools import engine_api_joint_staging_image_root_verify as command
from tools.engine_api_joint_staging_provenance_snapshot import verify_image_bound_snapshot
from tools.engine_api_joint_staging_source_set import load_image_bound_source_set
from tests.test_lq1087_lq1098_engine_api_fixed_source_root import source_root
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW

DIGEST="sha256:"+"a"*64
def image_root(tmp_path):
    root=source_root(tmp_path);authority=ManifestHandoffSupervisorEngineApiStagingImageAuthority("staging-a","staging-key-a",DIGEST);path=root/"image-authority";path.write_bytes(encode_manifest_handoff_supervisor_engine_api_staging_image_authority(authority));path.chmod(0o600);return root

def test_image_authority_is_canonical_and_secret_free():
    value=ManifestHandoffSupervisorEngineApiStagingImageAuthority("staging-a","staging-key-a",DIGEST);content=encode_manifest_handoff_supervisor_engine_api_staging_image_authority(value)
    assert decode_manifest_handoff_supervisor_engine_api_staging_image_authority(content)==value and repr(value)=="ManifestHandoffSupervisorEngineApiStagingImageAuthority()"

@pytest.mark.parametrize("mutation",("order","digest","extra","partial"))
def test_image_authority_rejects_noncanonical_or_invalid_input(mutation):
    content=encode_manifest_handoff_supervisor_engine_api_staging_image_authority(ManifestHandoffSupervisorEngineApiStagingImageAuthority("staging-a","staging-key-a",DIGEST))
    if mutation=="order": content=b"key_id=staging-key-a\nenvironment_id=staging-a\nimage_digest="+DIGEST.encode()+b"\n"
    elif mutation=="digest": content=content.replace(b"sha256:",b"sha512:")
    elif mutation=="extra": content+=b"allow=true\n"
    else: content=b"environment_id=staging-a\n"
    with pytest.raises(ManifestHandoffRegistryUnavailable): decode_manifest_handoff_supervisor_engine_api_staging_image_authority(content)

@pytest.mark.parametrize("mutation",("environment","key","digest"))
def test_image_bound_verifier_rejects_authority_mismatch(tmp_path,mutation):
    snapshot=load_image_bound_source_set(image_root(tmp_path));authority=decode_manifest_handoff_supervisor_engine_api_staging_image_authority(snapshot.image_authority)
    field={"environment":"environment_id","key":"key_id","digest":"image_digest"}[mutation];value={"environment":"staging-b","key":"staging-key-b","digest":"sha256:"+"b"*64}[mutation];snapshot=replace(snapshot,image_authority=encode_manifest_handoff_supervisor_engine_api_staging_image_authority(replace(authority,**{field:value})))
    with pytest.raises(ManifestHandoffRegistryUnavailable): verify_image_bound_snapshot(snapshot,now=NOW)

def test_image_bound_root_verifier_and_cli(tmp_path,monkeypatch):
    root=image_root(tmp_path);monkeypatch.setattr(command,"_utc_now",lambda:NOW);command.verify_current(root);assert command.main(["--source-root",str(root)])==0

def test_legacy_ten_source_root_is_not_image_authoritative(tmp_path,monkeypatch):
    root=source_root(tmp_path);monkeypatch.setattr(command,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): command.verify_current(root)
