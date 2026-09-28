"""Single-read private snapshot and pure staging provenance verification."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime,timezone
import hashlib
from pathlib import Path
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_evidence import decode_manifest_handoff_supervisor_engine_api_staging_evidence
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_run import decode_staging_run_authority,verify_staging_run_signature
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_trust import decode_manifest_handoff_supervisor_engine_api_provenance_receipt,decode_manifest_handoff_supervisor_engine_api_staging_image_authority,decode_manifest_handoff_supervisor_engine_api_staging_trust,decode_manifest_handoff_supervisor_engine_api_staging_verification_policy,verify_manifest_handoff_supervisor_engine_api_provenance_receipt
from tools.engine_api_joint_staging_evidence_bundle_verify import _MAX_ARTIFACT_BYTES,_read

@dataclass(frozen=True,slots=True)
class JointEngineApiStagingProvenanceSnapshot:
    trust:bytes
    signature:bytes
    evidence:bytes
    receipt:bytes
    artifacts:tuple[bytes,bytes,bytes,bytes,bytes]
    def __post_init__(self):
        if any(type(value)is not bytes or not value for value in (self.trust,self.signature,self.evidence,self.receipt,*self.artifacts)) or type(self.artifacts)is not tuple or len(self.artifacts)!=5: raise ManifestHandoffRegistryUnavailable
    def __repr__(self): return "JointEngineApiStagingProvenanceSnapshot()"

def load_snapshot(trust_file:Path,signature_file:Path,evidence_file:Path,receipt_file:Path,*artifact_files:Path):
    try:
        paths=(trust_file,signature_file,evidence_file,receipt_file,*artifact_files)
        if len(paths)!=9 or len(set(paths))!=9 or any(not isinstance(path,Path) or not path.is_absolute() or path==Path("/") or ".." in path.parts for path in paths): raise ManifestHandoffRegistryUnavailable
        fixed=(_read(trust_file,1024),_read(signature_file,256),_read(evidence_file,4096),_read(receipt_file,2048));artifacts=tuple(_read(path,_MAX_ARTIFACT_BYTES) for path in artifact_files)
        return JointEngineApiStagingProvenanceSnapshot(*fixed,artifacts)
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None

def verify_snapshot(snapshot:JointEngineApiStagingProvenanceSnapshot,*,maximum_age_seconds:int,now:datetime)->None:
    try:
        if type(snapshot)is not JointEngineApiStagingProvenanceSnapshot or type(now)is not datetime or now.tzinfo is None: raise ManifestHandoffRegistryUnavailable
        trust=decode_manifest_handoff_supervisor_engine_api_staging_trust(snapshot.trust);evidence=decode_manifest_handoff_supervisor_engine_api_staging_evidence(snapshot.evidence);receipt=decode_manifest_handoff_supervisor_engine_api_provenance_receipt(snapshot.receipt)
        verify_manifest_handoff_supervisor_engine_api_provenance_receipt(trust,snapshot.evidence,snapshot.signature,receipt,now=now.astimezone(timezone.utc),maximum_age_seconds=maximum_age_seconds)
        observed=datetime.fromisoformat(evidence.observed_at.replace("Z","+00:00"));age=(now.astimezone(timezone.utc)-observed).total_seconds()
        expected=(evidence.render_sha256,evidence.inspect_sha256,evidence.health_sha256,evidence.policy_sha256,evidence.shutdown_sha256);actual=tuple(hashlib.sha256(value).hexdigest() for value in snapshot.artifacts)
        if evidence.environment_id!=trust.environment_id or age<0 or age>maximum_age_seconds or actual!=expected: raise ManifestHandoffRegistryUnavailable
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None

@dataclass(frozen=True,slots=True)
class JointEngineApiPolicyBoundProvenanceSnapshot:
    policy:bytes
    provenance:JointEngineApiStagingProvenanceSnapshot
    def __post_init__(self):
        if type(self.policy)is not bytes or not self.policy or type(self.provenance)is not JointEngineApiStagingProvenanceSnapshot: raise ManifestHandoffRegistryUnavailable
    def __repr__(self): return "JointEngineApiPolicyBoundProvenanceSnapshot()"

def load_policy_bound_snapshot(policy_file:Path,trust_file:Path,signature_file:Path,evidence_file:Path,receipt_file:Path,*artifact_files:Path):
    try:
        paths=(policy_file,trust_file,signature_file,evidence_file,receipt_file,*artifact_files)
        if len(paths)!=10 or len(set(paths))!=10 or any(not isinstance(path,Path) or not path.is_absolute() or path==Path("/") or ".." in path.parts for path in paths): raise ManifestHandoffRegistryUnavailable
        return JointEngineApiPolicyBoundProvenanceSnapshot(_read(policy_file,1024),load_snapshot(trust_file,signature_file,evidence_file,receipt_file,*artifact_files))
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None

def verify_policy_bound_snapshot(snapshot:JointEngineApiPolicyBoundProvenanceSnapshot,*,now:datetime)->None:
    try:
        if type(snapshot)is not JointEngineApiPolicyBoundProvenanceSnapshot or type(now)is not datetime or now.tzinfo is None or now.utcoffset().total_seconds()!=0: raise ManifestHandoffRegistryUnavailable
        policy=decode_manifest_handoff_supervisor_engine_api_staging_verification_policy(snapshot.policy);trust=decode_manifest_handoff_supervisor_engine_api_staging_trust(snapshot.provenance.trust);evidence=decode_manifest_handoff_supervisor_engine_api_staging_evidence(snapshot.provenance.evidence);receipt=decode_manifest_handoff_supervisor_engine_api_provenance_receipt(snapshot.provenance.receipt)
        if policy.environment_id!=trust.environment_id or policy.key_id!=trust.key_id: raise ManifestHandoffRegistryUnavailable
        verify_manifest_handoff_supervisor_engine_api_provenance_receipt(trust,snapshot.provenance.evidence,snapshot.provenance.signature,receipt,now=now,maximum_age_seconds=policy.receipt_max_age_seconds)
        observed=datetime.fromisoformat(evidence.observed_at.replace("Z","+00:00"));age=(now-observed).total_seconds();expected=(evidence.render_sha256,evidence.inspect_sha256,evidence.health_sha256,evidence.policy_sha256,evidence.shutdown_sha256);actual=tuple(hashlib.sha256(value).hexdigest() for value in snapshot.provenance.artifacts)
        if evidence.environment_id!=policy.environment_id or age<0 or age>policy.evidence_max_age_seconds or actual!=expected: raise ManifestHandoffRegistryUnavailable
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None

@dataclass(frozen=True,slots=True)
class JointEngineApiImageBoundProvenanceSnapshot:
    image_authority:bytes
    provenance:JointEngineApiPolicyBoundProvenanceSnapshot
    def __post_init__(self):
        if type(self.image_authority)is not bytes or not self.image_authority or type(self.provenance)is not JointEngineApiPolicyBoundProvenanceSnapshot: raise ManifestHandoffRegistryUnavailable
    def __repr__(self): return "JointEngineApiImageBoundProvenanceSnapshot()"

def verify_image_bound_snapshot(snapshot:JointEngineApiImageBoundProvenanceSnapshot,*,now:datetime)->None:
    try:
        if type(snapshot)is not JointEngineApiImageBoundProvenanceSnapshot: raise ManifestHandoffRegistryUnavailable
        authority=decode_manifest_handoff_supervisor_engine_api_staging_image_authority(snapshot.image_authority);trust=decode_manifest_handoff_supervisor_engine_api_staging_trust(snapshot.provenance.provenance.trust);evidence=decode_manifest_handoff_supervisor_engine_api_staging_evidence(snapshot.provenance.provenance.evidence)
        if authority.environment_id!=trust.environment_id or authority.key_id!=trust.key_id or authority.image_digest!=evidence.image_digest: raise ManifestHandoffRegistryUnavailable
        verify_policy_bound_snapshot(snapshot.provenance,now=now)
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None

@dataclass(frozen=True,slots=True)
class JointEngineApiRunBoundProvenanceSnapshot:
    run_authority:bytes
    run_envelope:bytes
    run_signature:bytes
    provenance:JointEngineApiImageBoundProvenanceSnapshot
    def __post_init__(self):
        if any(type(value)is not bytes or not value for value in (self.run_authority,self.run_envelope,self.run_signature)) or type(self.provenance)is not JointEngineApiImageBoundProvenanceSnapshot: raise ManifestHandoffRegistryUnavailable
    def __repr__(self): return "JointEngineApiRunBoundProvenanceSnapshot()"

def verify_run_bound_snapshot(snapshot:JointEngineApiRunBoundProvenanceSnapshot,*,now:datetime)->None:
    try:
        if type(snapshot)is not JointEngineApiRunBoundProvenanceSnapshot: raise ManifestHandoffRegistryUnavailable
        inner=snapshot.provenance.provenance.provenance;trust=decode_manifest_handoff_supervisor_engine_api_staging_trust(inner.trust);authority=decode_staging_run_authority(snapshot.run_authority)
        verify_staging_run_signature(trust,authority,inner.evidence,snapshot.run_envelope,snapshot.run_signature)
        verify_image_bound_snapshot(snapshot.provenance,now=now)
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None
