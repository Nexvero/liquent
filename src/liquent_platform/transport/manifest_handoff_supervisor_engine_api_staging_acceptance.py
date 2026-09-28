"""Durable one-shot acceptance marker for verified staging runs."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib,json,os,stat
from pathlib import Path
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_run import ManifestHandoffSupervisorEngineApiStagingRunAuthority,decode_staging_signature_envelope

_MARKER_STATE_FIELDS=("st_dev","st_ino","st_mode","st_uid","st_gid","st_nlink","st_size","st_mtime_ns","st_ctime_ns")

def _marker_state(facts:os.stat_result)->tuple[int,...]:
    return tuple(getattr(facts,name) for name in _MARKER_STATE_FIELDS)

def _open_root(root:Path)->int:
    descriptor=None
    try:
        flags=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC
        descriptor=os.open("/",flags)
        for component in root.parts[1:]:
            child=os.open(component,flags,dir_fd=descriptor)
            os.close(descriptor);descriptor=child
        result=descriptor;descriptor=None
        return result
    finally:
        if descriptor is not None:
            try: os.close(descriptor)
            except Exception: pass

def _validate_visible_root(root:Path,directory:int,before:os.stat_result|None=None)->None:
    visible=None
    try:
        held=os.fstat(directory);visible=_open_root(root);current=os.fstat(visible)
        stable=("st_dev","st_ino","st_mode","st_uid","st_gid","st_nlink")
        if any(getattr(held,name)!=getattr(current,name) for name in stable) or not stat.S_ISDIR(held.st_mode) or held.st_uid!=os.geteuid() or stat.S_IMODE(held.st_mode)!=0o700 or os.get_inheritable(directory) or os.get_inheritable(visible): raise ManifestHandoffRegistryUnavailable
        if before is not None:
            complete=("st_dev","st_ino","st_mode","st_uid","st_gid","st_nlink","st_size","st_mtime_ns","st_ctime_ns")
            if any(getattr(before,name)!=getattr(held,name) or getattr(held,name)!=getattr(current,name) for name in complete): raise ManifestHandoffRegistryUnavailable
    finally:
        if visible is not None:
            try: os.close(visible)
            except Exception: pass

@dataclass(frozen=True,slots=True)
class ManifestHandoffSupervisorEngineApiStagingRunAcceptance:
    schema_version:int
    run_id:str
    envelope_sha256:str
    def __post_init__(self):
        try: authority=ManifestHandoffSupervisorEngineApiStagingRunAuthority("staging","key",self.run_id)
        except Exception: raise ManifestHandoffRegistryUnavailable from None
        if self.schema_version!=1 or type(self.schema_version)is not int or type(self.envelope_sha256)is not str or len(self.envelope_sha256)!=64 or any(character not in "0123456789abcdef" for character in self.envelope_sha256): raise ManifestHandoffRegistryUnavailable
    def __repr__(self): return "ManifestHandoffSupervisorEngineApiStagingRunAcceptance()"

@dataclass(frozen=True,slots=True)
class ManifestHandoffSupervisorEngineApiStagingRunAcceptanceObservation:
    acceptance:ManifestHandoffSupervisorEngineApiStagingRunAcceptance
    marker_identity:tuple[int,int]
    marker_state:tuple[int,...]
    def __post_init__(self):
        invalid_shape=type(self.acceptance)is not ManifestHandoffSupervisorEngineApiStagingRunAcceptance or type(self.marker_identity)is not tuple or len(self.marker_identity)!=2 or any(type(item)is not int or item<0 for item in self.marker_identity) or type(self.marker_state)is not tuple or len(self.marker_state)!=len(_MARKER_STATE_FIELDS) or any(type(item)is not int or item<0 for item in self.marker_state) or self.marker_state[:2]!=self.marker_identity
        invalid_semantics=not invalid_shape and (not stat.S_ISREG(self.marker_state[2]) or self.marker_state[3]!=os.geteuid() or stat.S_IMODE(self.marker_state[2])!=0o600 or self.marker_state[5]!=1 or self.marker_state[6]!=len(encode_staging_run_acceptance(self.acceptance)))
        if invalid_shape or invalid_semantics: raise ManifestHandoffRegistryUnavailable
    def __repr__(self): return "ManifestHandoffSupervisorEngineApiStagingRunAcceptanceObservation()"

def build_staging_run_acceptance(authority,envelope_content:bytes):
    try:
        if type(authority)is not ManifestHandoffSupervisorEngineApiStagingRunAuthority: raise ManifestHandoffRegistryUnavailable
        envelope=decode_staging_signature_envelope(envelope_content)
        if (envelope.environment_id,envelope.key_id,envelope.run_id)!=(authority.environment_id,authority.key_id,authority.run_id): raise ManifestHandoffRegistryUnavailable
        return ManifestHandoffSupervisorEngineApiStagingRunAcceptance(1,authority.run_id,hashlib.sha256(envelope_content).hexdigest())
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None

def encode_staging_run_acceptance(value)->bytes:
    if type(value)is not ManifestHandoffSupervisorEngineApiStagingRunAcceptance: raise ManifestHandoffRegistryUnavailable
    return (json.dumps({"envelope_sha256":value.envelope_sha256,"run_id":value.run_id,"schema_version":value.schema_version},sort_keys=True,separators=(",",":"))+"\n").encode("ascii")

def decode_staging_run_acceptance(content:bytes):
    try:
        if type(content)is not bytes or not content.endswith(b"\n") or len(content)>1024: raise ManifestHandoffRegistryUnavailable
        payload=json.loads(content);keys=("schema_version","run_id","envelope_sha256")
        if type(payload)is not dict or set(payload)!=set(keys): raise ManifestHandoffRegistryUnavailable
        value=ManifestHandoffSupervisorEngineApiStagingRunAcceptance(**payload)
        if encode_staging_run_acceptance(value)!=content: raise ManifestHandoffRegistryUnavailable
        return value
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None

def verify_staging_run_acceptance(value,authority,envelope_content:bytes)->None:
    try:
        if type(value)is not ManifestHandoffSupervisorEngineApiStagingRunAcceptance or value!=build_staging_run_acceptance(authority,envelope_content): raise ManifestHandoffRegistryUnavailable
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None

def _observe_acceptance_at(directory:int,run_id:str):
    descriptor=None
    try:
        try: descriptor=os.open(run_id+".accepted",os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=directory)
        except FileNotFoundError: return None
        before=os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_uid!=os.geteuid() or stat.S_IMODE(before.st_mode)!=0o600 or before.st_nlink!=1 or not 1<=before.st_size<=1024 or os.get_inheritable(descriptor): raise ManifestHandoffRegistryUnavailable
        content=bytearray()
        while len(content)<=1024:
            part=os.read(descriptor,1025-len(content))
            if not part: break
            content.extend(part)
        after=os.fstat(descriptor);stable=("st_dev","st_ino","st_mode","st_nlink","st_size","st_mtime_ns","st_ctime_ns")
        if len(content)!=before.st_size or any(getattr(before,name)!=getattr(after,name) for name in stable): raise ManifestHandoffRegistryUnavailable
        value=decode_staging_run_acceptance(bytes(content))
        if value.run_id!=run_id: raise ManifestHandoffRegistryUnavailable
        return ManifestHandoffSupervisorEngineApiStagingRunAcceptanceObservation(value,(before.st_dev,before.st_ino),_marker_state(before))
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None
    finally:
        if descriptor is not None:
            try: os.close(descriptor)
            except Exception: pass

def _load_acceptance_at(directory:int,run_id:str):
    observed=_observe_acceptance_at(directory,run_id)
    return None if observed is None else observed.acceptance

def _verify_created_acceptance(descriptor:int,content:bytes)->None:
    before=os.fstat(descriptor)
    if not stat.S_ISREG(before.st_mode) or before.st_uid!=os.geteuid() or stat.S_IMODE(before.st_mode)!=0o600 or before.st_nlink!=1 or before.st_size!=len(content) or os.get_inheritable(descriptor): raise ManifestHandoffRegistryUnavailable
    os.lseek(descriptor,0,os.SEEK_SET);observed=bytearray()
    while len(observed)<=len(content):
        part=os.read(descriptor,len(content)+1-len(observed))
        if not part: break
        observed.extend(part)
    after=os.fstat(descriptor);stable=("st_dev","st_ino","st_mode","st_uid","st_gid","st_nlink","st_size","st_mtime_ns","st_ctime_ns")
    if bytes(observed)!=content or any(getattr(before,name)!=getattr(after,name) for name in stable): raise ManifestHandoffRegistryUnavailable

def load_staging_run_acceptance(root:Path,run_id:str,*,expected_root_identity:tuple[int,int]|None=None):
    directory=None
    try:
        ManifestHandoffSupervisorEngineApiStagingRunAuthority("staging","key",run_id)
        if not isinstance(root,Path) or not root.is_absolute() or root==Path("/") or ".." in root.parts or (expected_root_identity is not None and (type(expected_root_identity)is not tuple or len(expected_root_identity)!=2 or any(type(item)is not int or item<0 for item in expected_root_identity))): raise ManifestHandoffRegistryUnavailable
        directory=_open_root(root);facts=os.fstat(directory)
        if not stat.S_ISDIR(facts.st_mode) or facts.st_uid!=os.geteuid() or stat.S_IMODE(facts.st_mode)!=0o700 or os.get_inheritable(directory): raise ManifestHandoffRegistryUnavailable
        if expected_root_identity is not None and (facts.st_dev,facts.st_ino)!=expected_root_identity: raise ManifestHandoffRegistryUnavailable
        value=_load_acceptance_at(directory,run_id);_validate_visible_root(root,directory,facts);return value
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None
    finally:
        if directory is not None:
            try: os.close(directory)
            except Exception: pass

def observe_staging_run_acceptance(root:Path,run_id:str,*,expected_root_identity:tuple[int,int]|None=None):
    directory=None
    try:
        ManifestHandoffSupervisorEngineApiStagingRunAuthority("staging","key",run_id)
        if not isinstance(root,Path) or not root.is_absolute() or root==Path("/") or ".." in root.parts or (expected_root_identity is not None and (type(expected_root_identity)is not tuple or len(expected_root_identity)!=2 or any(type(item)is not int or item<0 for item in expected_root_identity))): raise ManifestHandoffRegistryUnavailable
        directory=_open_root(root);facts=os.fstat(directory)
        if not stat.S_ISDIR(facts.st_mode) or facts.st_uid!=os.geteuid() or stat.S_IMODE(facts.st_mode)!=0o700 or os.get_inheritable(directory): raise ManifestHandoffRegistryUnavailable
        if expected_root_identity is not None and (facts.st_dev,facts.st_ino)!=expected_root_identity: raise ManifestHandoffRegistryUnavailable
        value=_observe_acceptance_at(directory,run_id);_validate_visible_root(root,directory,facts);return value
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None
    finally:
        if directory is not None:
            try: os.close(directory)
            except Exception: pass

def inspect_staging_run_acceptance_registry(root:Path,*,expected_root_identity:tuple[int,int]|None=None):
    directory=None
    try:
        if not isinstance(root,Path) or not root.is_absolute() or root==Path("/") or ".." in root.parts or (expected_root_identity is not None and (type(expected_root_identity)is not tuple or len(expected_root_identity)!=2 or any(type(item)is not int or item<0 for item in expected_root_identity))): raise ManifestHandoffRegistryUnavailable
        directory=_open_root(root);before=os.fstat(directory)
        if not stat.S_ISDIR(before.st_mode) or before.st_uid!=os.geteuid() or stat.S_IMODE(before.st_mode)!=0o700 or os.get_inheritable(directory): raise ManifestHandoffRegistryUnavailable
        if expected_root_identity is not None and (before.st_dev,before.st_ino)!=expected_root_identity: raise ManifestHandoffRegistryUnavailable
        names=sorted(os.listdir(directory))
        if len(names)>4096: raise ManifestHandoffRegistryUnavailable
        run_ids=[]
        for name in names:
            if not name.endswith(".accepted"): raise ManifestHandoffRegistryUnavailable
            run_id=name[:-9];ManifestHandoffSupervisorEngineApiStagingRunAuthority("staging","key",run_id);run_ids.append(run_id)
        values=tuple(_load_acceptance_at(directory,run_id) for run_id in run_ids);after=os.fstat(directory);stable=("st_dev","st_ino","st_mode","st_mtime_ns","st_ctime_ns")
        if any(value is None for value in values) or any(getattr(before,name)!=getattr(after,name) for name in stable) or sorted(os.listdir(directory))!=names: raise ManifestHandoffRegistryUnavailable
        _validate_visible_root(root,directory,before)
        return values
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None
    finally:
        if directory is not None:
            try: os.close(directory)
            except Exception: pass

def observe_staging_run_acceptance_registry(root:Path,*,expected_root_identity:tuple[int,int]|None=None):
    directory=None
    try:
        if not isinstance(root,Path) or not root.is_absolute() or root==Path("/") or ".." in root.parts or (expected_root_identity is not None and (type(expected_root_identity)is not tuple or len(expected_root_identity)!=2 or any(type(item)is not int or item<0 for item in expected_root_identity))): raise ManifestHandoffRegistryUnavailable
        directory=_open_root(root);before=os.fstat(directory)
        if not stat.S_ISDIR(before.st_mode) or before.st_uid!=os.geteuid() or stat.S_IMODE(before.st_mode)!=0o700 or os.get_inheritable(directory): raise ManifestHandoffRegistryUnavailable
        if expected_root_identity is not None and (before.st_dev,before.st_ino)!=expected_root_identity: raise ManifestHandoffRegistryUnavailable
        names=sorted(os.listdir(directory))
        if len(names)>4096: raise ManifestHandoffRegistryUnavailable
        run_ids=[]
        for name in names:
            if not name.endswith(".accepted"): raise ManifestHandoffRegistryUnavailable
            run_id=name[:-9];ManifestHandoffSupervisorEngineApiStagingRunAuthority("staging","key",run_id);run_ids.append(run_id)
        values=tuple(_observe_acceptance_at(directory,run_id) for run_id in run_ids);after=os.fstat(directory);stable=("st_dev","st_ino","st_mode","st_mtime_ns","st_ctime_ns")
        if any(value is None for value in values) or any(getattr(before,name)!=getattr(after,name) for name in stable) or sorted(os.listdir(directory))!=names: raise ManifestHandoffRegistryUnavailable
        _validate_visible_root(root,directory,before);return values
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None
    finally:
        if directory is not None:
            try: os.close(directory)
            except Exception: pass

def record_staging_run_acceptance(root:Path,value,*,expected_root_identity:tuple[int,int]|None=None)->ManifestHandoffSupervisorEngineApiStagingRunAcceptanceObservation:
    directory=descriptor=None;created=False;file_synced=False
    try:
        if not isinstance(root,Path) or not root.is_absolute() or root==Path("/") or ".." in root.parts or type(value)is not ManifestHandoffSupervisorEngineApiStagingRunAcceptance or (expected_root_identity is not None and (type(expected_root_identity)is not tuple or len(expected_root_identity)!=2 or any(type(item)is not int or item<0 for item in expected_root_identity))): raise ManifestHandoffRegistryUnavailable
        directory=_open_root(root);facts=os.fstat(directory)
        if not stat.S_ISDIR(facts.st_mode) or facts.st_uid!=os.geteuid() or stat.S_IMODE(facts.st_mode)!=0o700 or os.get_inheritable(directory): raise ManifestHandoffRegistryUnavailable
        if expected_root_identity is not None and (facts.st_dev,facts.st_ino)!=expected_root_identity: raise ManifestHandoffRegistryUnavailable
        content=encode_staging_run_acceptance(value);_validate_visible_root(root,directory);descriptor=os.open(value.run_id+".accepted",os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=directory);created=True;written=0
        while written<len(content):
            count=os.write(descriptor,content[written:])
            if type(count)is not int or count<1: raise ManifestHandoffRegistryUnavailable
            written+=count
        os.fsync(descriptor);_verify_created_acceptance(descriptor,content);file_synced=True;os.fsync(directory);_validate_visible_root(root,directory);marker=os.fstat(descriptor);return ManifestHandoffSupervisorEngineApiStagingRunAcceptanceObservation(value,(marker.st_dev,marker.st_ino),_marker_state(marker))
    except ManifestHandoffRegistryUnavailable:
        if created and not file_synced and directory is not None:
            try: os.unlink(value.run_id+".accepted",dir_fd=directory);os.fsync(directory)
            except Exception: pass
        raise
    except Exception:
        if created and not file_synced and directory is not None:
            try: os.unlink(value.run_id+".accepted",dir_fd=directory);os.fsync(directory)
            except Exception: pass
        raise ManifestHandoffRegistryUnavailable from None
    finally:
        if descriptor is not None:
            try: os.close(descriptor)
            except Exception: pass
        if directory is not None:
            try: os.close(directory)
            except Exception: pass
