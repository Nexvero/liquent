"""Run-bound canonical signature envelope for staging evidence."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib,json,re,uuid
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_evidence import decode_manifest_handoff_supervisor_engine_api_staging_evidence
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_trust import ManifestHandoffSupervisorEngineApiStagingTrust,verify_manifest_handoff_supervisor_engine_api_staging_signature_bytes

_ID=re.compile(r"[a-z][a-z0-9-]{0,62}\Z");_HASH=re.compile(r"[0-9a-f]{64}\Z");_DIGEST=re.compile(r"sha256:[0-9a-f]{64}\Z")
def _run(value):
    try: parsed=uuid.UUID(value)
    except Exception: return False
    return type(value)is str and parsed.version==4 and str(parsed)==value

@dataclass(frozen=True,slots=True)
class ManifestHandoffSupervisorEngineApiStagingRunAuthority:
    environment_id:str
    key_id:str
    run_id:str
    def __post_init__(self):
        if type(self.environment_id)is not str or not _ID.fullmatch(self.environment_id) or type(self.key_id)is not str or not _ID.fullmatch(self.key_id) or not _run(self.run_id): raise ManifestHandoffRegistryUnavailable
    def __repr__(self): return "ManifestHandoffSupervisorEngineApiStagingRunAuthority()"

@dataclass(frozen=True,slots=True)
class ManifestHandoffSupervisorEngineApiStagingSignatureEnvelope:
    schema_version:int
    environment_id:str
    key_id:str
    run_id:str
    evidence_sha256:str
    image_digest:str
    def __post_init__(self):
        if self.schema_version!=1 or type(self.schema_version)is not int or type(self.environment_id)is not str or not _ID.fullmatch(self.environment_id) or type(self.key_id)is not str or not _ID.fullmatch(self.key_id) or not _run(self.run_id) or type(self.evidence_sha256)is not str or not _HASH.fullmatch(self.evidence_sha256) or type(self.image_digest)is not str or not _DIGEST.fullmatch(self.image_digest): raise ManifestHandoffRegistryUnavailable
    def __repr__(self): return "ManifestHandoffSupervisorEngineApiStagingSignatureEnvelope()"

def encode_staging_run_authority(value)->bytes:
    if type(value)is not ManifestHandoffSupervisorEngineApiStagingRunAuthority: raise ManifestHandoffRegistryUnavailable
    return f"environment_id={value.environment_id}\nkey_id={value.key_id}\nrun_id={value.run_id}\n".encode("ascii")

def decode_staging_run_authority(content:bytes):
    try:
        if type(content)is not bytes or len(content)>1024: raise ManifestHandoffRegistryUnavailable
        lines=content.decode("ascii").splitlines(keepends=True);keys=("environment_id","key_id","run_id")
        if len(lines)!=3 or any(not line.endswith("\n") or "=" not in line for line in lines): raise ManifestHandoffRegistryUnavailable
        values=dict(line[:-1].split("=",1) for line in lines)
        if tuple(values)!=keys: raise ManifestHandoffRegistryUnavailable
        value=ManifestHandoffSupervisorEngineApiStagingRunAuthority(**values)
        if encode_staging_run_authority(value)!=content: raise ManifestHandoffRegistryUnavailable
        return value
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None

def build_staging_signature_envelope(authority,evidence:bytes):
    try:
        if type(authority)is not ManifestHandoffSupervisorEngineApiStagingRunAuthority: raise ManifestHandoffRegistryUnavailable
        observed=decode_manifest_handoff_supervisor_engine_api_staging_evidence(evidence)
        if observed.environment_id!=authority.environment_id: raise ManifestHandoffRegistryUnavailable
        return ManifestHandoffSupervisorEngineApiStagingSignatureEnvelope(1,authority.environment_id,authority.key_id,authority.run_id,hashlib.sha256(evidence).hexdigest(),observed.image_digest)
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None

def encode_staging_signature_envelope(value)->bytes:
    if type(value)is not ManifestHandoffSupervisorEngineApiStagingSignatureEnvelope: raise ManifestHandoffRegistryUnavailable
    keys=("schema_version","environment_id","key_id","run_id","evidence_sha256","image_digest")
    return (json.dumps({key:getattr(value,key) for key in keys},sort_keys=True,separators=(",",":"),ensure_ascii=True)+"\n").encode("ascii")

def decode_staging_signature_envelope(content:bytes):
    try:
        if type(content)is not bytes or not content.endswith(b"\n") or len(content)>2048: raise ManifestHandoffRegistryUnavailable
        payload=json.loads(content);keys=("schema_version","environment_id","key_id","run_id","evidence_sha256","image_digest")
        if type(payload)is not dict or set(payload)!=set(keys): raise ManifestHandoffRegistryUnavailable
        value=ManifestHandoffSupervisorEngineApiStagingSignatureEnvelope(**payload)
        if encode_staging_signature_envelope(value)!=content: raise ManifestHandoffRegistryUnavailable
        return value
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None

def verify_staging_run_signature(trust,authority,evidence:bytes,envelope_content:bytes,signature_content:bytes)->None:
    try:
        if type(trust)is not ManifestHandoffSupervisorEngineApiStagingTrust or type(authority)is not ManifestHandoffSupervisorEngineApiStagingRunAuthority: raise ManifestHandoffRegistryUnavailable
        envelope=decode_staging_signature_envelope(envelope_content);expected=build_staging_signature_envelope(authority,evidence)
        if trust.environment_id!=authority.environment_id or trust.key_id!=authority.key_id or envelope!=expected: raise ManifestHandoffRegistryUnavailable
        verify_manifest_handoff_supervisor_engine_api_staging_signature_bytes(trust,envelope_content,signature_content)
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None
