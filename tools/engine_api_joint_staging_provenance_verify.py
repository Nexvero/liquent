"""Combined detached-signature and evidence-bundle verifier."""
from __future__ import annotations
from pathlib import Path
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_trust import load_manifest_handoff_supervisor_engine_api_staging_trust, verify_manifest_handoff_supervisor_engine_api_staging_signature
from tools.engine_api_joint_staging_evidence_bundle_verify import _read, verify as verify_bundle

def verify(trust_file:Path,signature_file:Path,evidence_file:Path,*artifact_files:Path,maximum_age_seconds:int,now=None)->None:
    try:
        if len(artifact_files)!=5: raise ManifestHandoffRegistryUnavailable
        trust=load_manifest_handoff_supervisor_engine_api_staging_trust(trust_file)
        evidence=_read(evidence_file,4096)
        verify_manifest_handoff_supervisor_engine_api_staging_signature(trust,evidence,signature_file)
        verify_bundle(evidence_file,*artifact_files,expected_environment=trust.environment_id,maximum_age_seconds=maximum_age_seconds,now=now)
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None
