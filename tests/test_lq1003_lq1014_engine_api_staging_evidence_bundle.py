from datetime import datetime, timezone
import hashlib
from pathlib import Path
import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_evidence import ManifestHandoffSupervisorEngineApiStagingEvidence, write_manifest_handoff_supervisor_engine_api_staging_evidence
from tools.engine_api_joint_staging_evidence_bundle_verify import verify

def bundle(tmp_path):
    contents=(b"render",b"inspect",b"health",b"policy",b"shutdown")
    files=[]
    for index,content in enumerate(contents):
        path=(tmp_path/f"artifact-{index}"); path.write_bytes(content); path.chmod(0o600); files.append(path.resolve())
    hashes=[hashlib.sha256(value).hexdigest() for value in contents]
    evidence=ManifestHandoffSupervisorEngineApiStagingEvidence(1,"staging-a","2026-08-29T12:00:00Z","sha256:"+"a"*64,*hashes)
    evidence_file=(tmp_path/"evidence.json").resolve(); write_manifest_handoff_supervisor_engine_api_staging_evidence(evidence_file,evidence)
    return evidence_file,files

def test_bundle_hashes_environment_and_freshness_are_verified(tmp_path):
    evidence,files=bundle(tmp_path)
    verify(evidence,*files,expected_environment="staging-a",maximum_age_seconds=3600,now=datetime(2026,8,29,12,30,tzinfo=timezone.utc))

@pytest.mark.parametrize("mutation",("content","mode","environment","future","stale"))
def test_every_bundle_or_freshness_mismatch_fails_closed(tmp_path,mutation):
    evidence,files=bundle(tmp_path); environment="staging-a"; now=datetime(2026,8,29,12,30,tzinfo=timezone.utc); maximum=3600
    if mutation=="content": files[0].write_bytes(b"changed")
    elif mutation=="mode": files[0].chmod(0o640)
    elif mutation=="environment": environment="production"
    elif mutation=="future": now=datetime(2026,8,29,11,59,tzinfo=timezone.utc)
    else: now=datetime(2026,8,30,12,tzinfo=timezone.utc)
    with pytest.raises(ManifestHandoffRegistryUnavailable): verify(evidence,*files,expected_environment=environment,maximum_age_seconds=maximum,now=now)

def test_duplicate_paths_and_unbounded_age_are_rejected(tmp_path):
    evidence,files=bundle(tmp_path)
    with pytest.raises(ManifestHandoffRegistryUnavailable): verify(evidence,files[0],files[0],*files[2:],expected_environment="staging-a",maximum_age_seconds=3600,now=datetime(2026,8,29,12,30,tzinfo=timezone.utc))
    with pytest.raises(ManifestHandoffRegistryUnavailable): verify(evidence,*files,expected_environment="staging-a",maximum_age_seconds=604801,now=datetime(2026,8,29,12,30,tzinfo=timezone.utc))

def test_naive_clock_is_rejected(tmp_path):
    evidence,files=bundle(tmp_path)
    with pytest.raises(ManifestHandoffRegistryUnavailable): verify(evidence,*files,expected_environment="staging-a",maximum_age_seconds=3600,now=datetime(2026,8,29,12,30))
