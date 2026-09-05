"""Combined signed staging provenance and receipt verifier."""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tools.engine_api_joint_staging_provenance_snapshot import load_snapshot,verify_snapshot

def verify(trust_file:Path,signature_file:Path,evidence_file:Path,receipt_file:Path,*artifact_files:Path,maximum_age_seconds:int,now:datetime)->None:
    try:
        verify_snapshot(load_snapshot(trust_file,signature_file,evidence_file,receipt_file,*artifact_files),maximum_age_seconds=maximum_age_seconds,now=now)
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None
