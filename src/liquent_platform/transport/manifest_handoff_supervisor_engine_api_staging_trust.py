"""Fixed Ed25519 trust and detached verification for staging evidence."""
from __future__ import annotations
import base64
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable

_ID = re.compile(r"[a-z][a-z0-9-]{0,62}\Z")

def _private(path: Path, maximum: int) -> bytes:
    descriptor=None
    try:
        if not isinstance(path,Path) or not path.is_absolute() or path==Path("/") or ".." in path.parts: raise ManifestHandoffRegistryUnavailable
        descriptor=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC); facts=os.fstat(descriptor)
        if not stat.S_ISREG(facts.st_mode) or facts.st_uid!=os.geteuid() or stat.S_IMODE(facts.st_mode)!=0o600 or facts.st_nlink!=1 or facts.st_size<1 or facts.st_size>maximum or os.get_inheritable(descriptor): raise ManifestHandoffRegistryUnavailable
        content=os.read(descriptor,maximum+1)
        if len(content)!=facts.st_size: raise ManifestHandoffRegistryUnavailable
        return content
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None
    finally:
        if descriptor is not None:
            try: os.close(descriptor)
            except Exception: pass

@dataclass(frozen=True,slots=True)
class ManifestHandoffSupervisorEngineApiStagingTrust:
    environment_id:str
    key_id:str
    public_key:bytes
    def __post_init__(self):
        if type(self.environment_id)is not str or not _ID.fullmatch(self.environment_id) or type(self.key_id)is not str or not _ID.fullmatch(self.key_id) or type(self.public_key)is not bytes or len(self.public_key)!=32: raise ManifestHandoffRegistryUnavailable
    def __repr__(self): return "ManifestHandoffSupervisorEngineApiStagingTrust()"

@dataclass(frozen=True,slots=True)
class ManifestHandoffSupervisorEngineApiStagingVerificationPolicy:
    environment_id:str
    key_id:str
    evidence_max_age_seconds:int
    receipt_max_age_seconds:int
    def __post_init__(self):
        if type(self.environment_id)is not str or not _ID.fullmatch(self.environment_id) or type(self.key_id)is not str or not _ID.fullmatch(self.key_id) or any(type(value)is not int or isinstance(value,bool) or not 1<=value<=604800 for value in (self.evidence_max_age_seconds,self.receipt_max_age_seconds)): raise ManifestHandoffRegistryUnavailable
    def __repr__(self): return "ManifestHandoffSupervisorEngineApiStagingVerificationPolicy()"

@dataclass(frozen=True,slots=True)
class ManifestHandoffSupervisorEngineApiStagingImageAuthority:
    environment_id:str
    key_id:str
    image_digest:str
    def __post_init__(self):
        if type(self.environment_id)is not str or not _ID.fullmatch(self.environment_id) or type(self.key_id)is not str or not _ID.fullmatch(self.key_id) or type(self.image_digest)is not str or not re.fullmatch(r"sha256:[0-9a-f]{64}",self.image_digest): raise ManifestHandoffRegistryUnavailable
    def __repr__(self): return "ManifestHandoffSupervisorEngineApiStagingImageAuthority()"

def decode_manifest_handoff_supervisor_engine_api_staging_trust(content:bytes):
    try:
        if type(content)is not bytes or len(content)>1024: raise ManifestHandoffRegistryUnavailable
        lines=content.decode("ascii").splitlines(keepends=True)
        if len(lines)!=3 or any(not line.endswith("\n") or "=" not in line for line in lines): raise ManifestHandoffRegistryUnavailable
        values=dict(line[:-1].split("=",1) for line in lines)
        if set(values)!={"environment_id","key_id","ed25519_public_key"}: raise ManifestHandoffRegistryUnavailable
        key=base64.b64decode(values["ed25519_public_key"],validate=True)
        if base64.b64encode(key).decode("ascii")!=values["ed25519_public_key"]: raise ManifestHandoffRegistryUnavailable
        return ManifestHandoffSupervisorEngineApiStagingTrust(values["environment_id"],values["key_id"],key)
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None

def load_manifest_handoff_supervisor_engine_api_staging_trust(path:Path):
    return decode_manifest_handoff_supervisor_engine_api_staging_trust(_private(path,1024))

def decode_manifest_handoff_supervisor_engine_api_staging_verification_policy(content:bytes):
    try:
        if type(content)is not bytes or len(content)>1024: raise ManifestHandoffRegistryUnavailable
        lines=content.decode("ascii").splitlines(keepends=True)
        if len(lines)!=4 or any(not line.endswith("\n") or "=" not in line for line in lines): raise ManifestHandoffRegistryUnavailable
        values=dict(line[:-1].split("=",1) for line in lines)
        keys=("environment_id","key_id","evidence_max_age_seconds","receipt_max_age_seconds")
        if tuple(values)!=keys or any(not values[name].isdigit() or (len(values[name])>1 and values[name].startswith("0")) for name in keys[2:]): raise ManifestHandoffRegistryUnavailable
        policy=ManifestHandoffSupervisorEngineApiStagingVerificationPolicy(values["environment_id"],values["key_id"],int(values["evidence_max_age_seconds"]),int(values["receipt_max_age_seconds"]))
        if encode_manifest_handoff_supervisor_engine_api_staging_verification_policy(policy)!=content: raise ManifestHandoffRegistryUnavailable
        return policy
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None

def encode_manifest_handoff_supervisor_engine_api_staging_verification_policy(value)->bytes:
    if type(value)is not ManifestHandoffSupervisorEngineApiStagingVerificationPolicy: raise ManifestHandoffRegistryUnavailable
    return f"environment_id={value.environment_id}\nkey_id={value.key_id}\nevidence_max_age_seconds={value.evidence_max_age_seconds}\nreceipt_max_age_seconds={value.receipt_max_age_seconds}\n".encode("ascii")

def load_manifest_handoff_supervisor_engine_api_staging_verification_policy(path:Path):
    return decode_manifest_handoff_supervisor_engine_api_staging_verification_policy(_private(path,1024))

def encode_manifest_handoff_supervisor_engine_api_staging_image_authority(value)->bytes:
    if type(value)is not ManifestHandoffSupervisorEngineApiStagingImageAuthority: raise ManifestHandoffRegistryUnavailable
    return f"environment_id={value.environment_id}\nkey_id={value.key_id}\nimage_digest={value.image_digest}\n".encode("ascii")

def decode_manifest_handoff_supervisor_engine_api_staging_image_authority(content:bytes):
    try:
        if type(content)is not bytes or len(content)>1024: raise ManifestHandoffRegistryUnavailable
        lines=content.decode("ascii").splitlines(keepends=True);keys=("environment_id","key_id","image_digest")
        if len(lines)!=3 or any(not line.endswith("\n") or "=" not in line for line in lines): raise ManifestHandoffRegistryUnavailable
        values=dict(line[:-1].split("=",1) for line in lines)
        if tuple(values)!=keys: raise ManifestHandoffRegistryUnavailable
        value=ManifestHandoffSupervisorEngineApiStagingImageAuthority(**values)
        if encode_manifest_handoff_supervisor_engine_api_staging_image_authority(value)!=content: raise ManifestHandoffRegistryUnavailable
        return value
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None

def decode_manifest_handoff_supervisor_engine_api_staging_signature(content:bytes)->bytes:
    try:
        if type(content)is not bytes or not content.endswith(b"\n") or content.count(b"\n")!=1: raise ManifestHandoffRegistryUnavailable
        signature=base64.b64decode(content[:-1],validate=True)
        if len(signature)!=64 or base64.b64encode(signature)!=content[:-1]: raise ManifestHandoffRegistryUnavailable
        return signature
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None

def _verify(trust,evidence:bytes,signature:bytes)->None:
    if type(trust)is not ManifestHandoffSupervisorEngineApiStagingTrust or type(evidence)is not bytes or not evidence or type(signature)is not bytes or len(signature)!=64: raise ManifestHandoffRegistryUnavailable
    try: Ed25519PublicKey.from_public_bytes(trust.public_key).verify(signature,evidence)
    except InvalidSignature: raise ManifestHandoffRegistryUnavailable from None
    except Exception: raise ManifestHandoffRegistryUnavailable from None

def verify_manifest_handoff_supervisor_engine_api_staging_signature_bytes(trust,payload:bytes,signature_content:bytes)->None:
    try: _verify(trust,payload,decode_manifest_handoff_supervisor_engine_api_staging_signature(signature_content))
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None

def verify_manifest_handoff_supervisor_engine_api_staging_signature(trust, evidence:bytes, signature_file:Path)->None:
    try:
        _verify(trust,evidence,decode_manifest_handoff_supervisor_engine_api_staging_signature(_private(signature_file,256)))
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None

def write_verified_manifest_handoff_supervisor_engine_api_staging_signature(path:Path,trust,evidence:bytes,content:bytes)->None:
    descriptor=None
    try:
        if not isinstance(path,Path) or not path.is_absolute() or path==Path("/") or ".." in path.parts: raise ManifestHandoffRegistryUnavailable
        signature=decode_manifest_handoff_supervisor_engine_api_staging_signature(content);_verify(trust,evidence,signature)
        descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
        written=0
        while written<len(content):
            count=os.write(descriptor,content[written:])
            if type(count)is not int or count<1: raise ManifestHandoffRegistryUnavailable
            written+=count
        os.fsync(descriptor)
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None
    finally:
        if descriptor is not None:
            try: os.close(descriptor)
            except Exception: pass

@dataclass(frozen=True,slots=True)
class ManifestHandoffSupervisorEngineApiProvenanceReceipt:
    schema_version:int
    environment_id:str
    key_id:str
    evidence_sha256:str
    signature_sha256:str
    verified_at:str
    def __post_init__(self):
        try: parsed=datetime.fromisoformat(self.verified_at.replace("Z","+00:00"))
        except Exception: raise ManifestHandoffRegistryUnavailable from None
        if self.schema_version!=1 or type(self.schema_version)is not int or not _ID.fullmatch(self.environment_id) or not _ID.fullmatch(self.key_id) or any(type(value)is not str or not re.fullmatch(r"[0-9a-f]{64}",value) for value in (self.evidence_sha256,self.signature_sha256)) or type(self.verified_at)is not str or not self.verified_at.endswith("Z") or parsed.tzinfo is None or parsed.utcoffset().total_seconds()!=0: raise ManifestHandoffRegistryUnavailable
    def __repr__(self): return "ManifestHandoffSupervisorEngineApiProvenanceReceipt()"

def build_manifest_handoff_supervisor_engine_api_provenance_receipt(trust,evidence:bytes,signature_content:bytes,verified_at:str):
    signature=decode_manifest_handoff_supervisor_engine_api_staging_signature(signature_content);_verify(trust,evidence,signature)
    return ManifestHandoffSupervisorEngineApiProvenanceReceipt(1,trust.environment_id,trust.key_id,hashlib.sha256(evidence).hexdigest(),hashlib.sha256(signature_content).hexdigest(),verified_at)

def encode_manifest_handoff_supervisor_engine_api_provenance_receipt(value)->bytes:
    if type(value)is not ManifestHandoffSupervisorEngineApiProvenanceReceipt: raise ManifestHandoffRegistryUnavailable
    return (json.dumps({name:getattr(value,name) for name in ("schema_version","environment_id","key_id","evidence_sha256","signature_sha256","verified_at")},sort_keys=True,separators=(",",":"),ensure_ascii=True)+"\n").encode("ascii")

def decode_manifest_handoff_supervisor_engine_api_provenance_receipt(content:bytes):
    try:
        if type(content)is not bytes or not content.endswith(b"\n") or len(content)>2048: raise ManifestHandoffRegistryUnavailable
        payload=json.loads(content)
        keys=("schema_version","environment_id","key_id","evidence_sha256","signature_sha256","verified_at")
        if type(payload)is not dict or set(payload)!=set(keys): raise ManifestHandoffRegistryUnavailable
        value=ManifestHandoffSupervisorEngineApiProvenanceReceipt(**payload)
        if encode_manifest_handoff_supervisor_engine_api_provenance_receipt(value)!=content: raise ManifestHandoffRegistryUnavailable
        return value
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None

def write_manifest_handoff_supervisor_engine_api_provenance_receipt(path:Path,value)->None:
    descriptor=None
    try:
        if not isinstance(path,Path) or not path.is_absolute() or path==Path("/") or ".." in path.parts: raise ManifestHandoffRegistryUnavailable
        content=encode_manifest_handoff_supervisor_engine_api_provenance_receipt(value)
        descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
        written=0
        while written<len(content):
            count=os.write(descriptor,content[written:])
            if type(count)is not int or count<1: raise ManifestHandoffRegistryUnavailable
            written+=count
        os.fsync(descriptor)
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None
    finally:
        if descriptor is not None:
            try: os.close(descriptor)
            except Exception: pass

def verify_manifest_handoff_supervisor_engine_api_provenance_receipt(trust,evidence:bytes,signature_content:bytes,receipt,*,now:datetime,maximum_age_seconds:int)->None:
    try:
        if type(receipt)is not ManifestHandoffSupervisorEngineApiProvenanceReceipt or type(now)is not datetime or now.tzinfo is None or now.utcoffset().total_seconds()!=0 or type(maximum_age_seconds)is not int or isinstance(maximum_age_seconds,bool) or not 1<=maximum_age_seconds<=604800: raise ManifestHandoffRegistryUnavailable
        signature=decode_manifest_handoff_supervisor_engine_api_staging_signature(signature_content);_verify(trust,evidence,signature)
        verified=datetime.fromisoformat(receipt.verified_at.replace("Z","+00:00"));age=(now-verified).total_seconds()
        if receipt.environment_id!=trust.environment_id or receipt.key_id!=trust.key_id or receipt.evidence_sha256!=hashlib.sha256(evidence).hexdigest() or receipt.signature_sha256!=hashlib.sha256(signature_content).hexdigest() or age<0 or age>maximum_age_seconds: raise ManifestHandoffRegistryUnavailable
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None
