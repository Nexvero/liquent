from dataclasses import replace
import base64
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_run import ManifestHandoffSupervisorEngineApiStagingRunAuthority,build_staging_signature_envelope,encode_staging_run_authority,encode_staging_signature_envelope
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_trust import ManifestHandoffSupervisorEngineApiStagingTrust,build_manifest_handoff_supervisor_engine_api_provenance_receipt,write_manifest_handoff_supervisor_engine_api_provenance_receipt
from tools import engine_api_joint_staging_run_root_verify as command
from tools.engine_api_joint_staging_provenance_snapshot import verify_run_bound_snapshot
from tools.engine_api_joint_staging_source_set import load_run_bound_source_set
from tests.test_lq1099_lq1110_engine_api_image_authority import image_root
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW

RUN="12345678-1234-4234-9234-123456789abc"
def run_root(tmp_path):
    root=image_root(tmp_path);evidence=(root/"evidence").read_bytes();key=Ed25519PrivateKey.generate();public=key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw);trust=ManifestHandoffSupervisorEngineApiStagingTrust("staging-a","staging-key-a",public);(root/"trust").write_bytes(b"environment_id=staging-a\nkey_id=staging-key-a\ned25519_public_key="+base64.b64encode(public)+b"\n");signature=base64.b64encode(key.sign(evidence))+b"\n";(root/"signature").write_bytes(signature);(root/"receipt").unlink();write_manifest_handoff_supervisor_engine_api_provenance_receipt((root/"receipt").resolve(),build_manifest_handoff_supervisor_engine_api_provenance_receipt(trust,evidence,signature,"2026-08-29T12:15:00Z"));authority=ManifestHandoffSupervisorEngineApiStagingRunAuthority("staging-a","staging-key-a",RUN);envelope=encode_staging_signature_envelope(build_staging_signature_envelope(authority,evidence));values={"run-authority":encode_staging_run_authority(authority),"run-envelope":envelope,"run-signature":base64.b64encode(key.sign(envelope))+b"\n"}
    for name,value in values.items(): path=root/name;path.write_bytes(value);path.chmod(0o600)
    return root

def test_fourteen_source_run_root_verifies(tmp_path):
    snapshot=load_run_bound_source_set(run_root(tmp_path));verify_run_bound_snapshot(snapshot,now=NOW);assert repr(snapshot)=="JointEngineApiRunBoundProvenanceSnapshot()"

@pytest.mark.parametrize("mutation",("authority","envelope","run-signature","v1-signature","missing","extra"))
def test_run_root_rejects_every_run_or_layout_mutation(tmp_path,mutation):
    root=run_root(tmp_path)
    if mutation=="authority": (root/"run-authority").write_bytes((root/"run-authority").read_bytes().replace(RUN.encode(),b"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"))
    elif mutation=="envelope": (root/"run-envelope").write_bytes((root/"run-envelope").read_bytes().replace(RUN.encode(),b"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"))
    elif mutation=="run-signature": (root/"run-signature").write_bytes(base64.b64encode(b"x"*64)+b"\n")
    elif mutation=="v1-signature": (root/"signature").write_bytes(base64.b64encode(b"x"*64)+b"\n")
    elif mutation=="missing": (root/"run-envelope").unlink()
    else: path=root/"extra";path.write_bytes(b"x");path.chmod(0o600)
    with pytest.raises(ManifestHandoffRegistryUnavailable): verify_run_bound_snapshot(load_run_bound_source_set(root),now=NOW)

def test_run_root_cli_uses_only_root_and_current_time(tmp_path,monkeypatch):
    root=run_root(tmp_path);monkeypatch.setattr(command,"_utc_now",lambda:NOW);command.verify_current(root);assert command.main(["--source-root",str(root)])==0

def test_image_only_root_is_not_run_authoritative(tmp_path,monkeypatch):
    root=image_root(tmp_path);monkeypatch.setattr(command,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): command.verify_current(root)
