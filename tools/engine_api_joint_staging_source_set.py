"""Fixed-layout, descriptor-relative private staging provenance source set."""
from __future__ import annotations
from dataclasses import dataclass
import os,stat
from pathlib import Path
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tools.engine_api_joint_staging_evidence_bundle_verify import _MAX_ARTIFACT_BYTES
from tools.engine_api_joint_staging_provenance_snapshot import JointEngineApiImageBoundProvenanceSnapshot,JointEngineApiPolicyBoundProvenanceSnapshot,JointEngineApiRunBoundProvenanceSnapshot,JointEngineApiStagingProvenanceSnapshot

_SOURCES=("verification-policy","trust","signature","evidence","receipt","render","inspect","health","staging-policy","shutdown")
_LIMITS=(1024,1024,256,4096,2048,*(_MAX_ARTIFACT_BYTES for _ in range(5)))
_MAX_SOURCE_SET_BYTES=64*1024*1024
_STATE_FIELDS=("st_dev","st_ino","st_mode","st_uid","st_gid","st_nlink","st_size","st_mtime_ns","st_ctime_ns")

def _state(facts): return tuple(getattr(facts,name) for name in _STATE_FIELDS)

@dataclass(frozen=True,slots=True)
class JointEngineApiRunBoundSourceObservation:
    snapshot:JointEngineApiRunBoundProvenanceSnapshot
    root_state:tuple[int,...]
    child_states:tuple[tuple[int,...],...]
    def __post_init__(self):
        invalid_shape=type(self.snapshot)is not JointEngineApiRunBoundProvenanceSnapshot or type(self.root_state)is not tuple or len(self.root_state)!=9 or any(type(item)is not int or item<0 for item in self.root_state) or type(self.child_states)is not tuple or len(self.child_states)!=14 or any(type(value)is not tuple or len(value)!=9 or any(type(item)is not int or item<0 for item in value) for value in self.child_states)
        invalid_root=not invalid_shape and (not stat.S_ISDIR(self.root_state[2]) or self.root_state[3]!=os.geteuid() or stat.S_IMODE(self.root_state[2])!=0o700)
        invalid_children=not invalid_shape and any(not stat.S_ISREG(value[2]) or value[3]!=os.geteuid() or stat.S_IMODE(value[2])!=0o600 or value[5]!=1 or not 1<=value[6]<=limit for value,limit in zip(self.child_states,(1024,2048,256,1024,*_LIMITS)))
        if invalid_shape or invalid_root or invalid_children: raise ManifestHandoffRegistryUnavailable
    def __repr__(self): return "JointEngineApiRunBoundSourceObservation()"

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

def _child(directory:int,name:str,maximum:int)->bytes:
    descriptor=None
    try:
        descriptor=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=directory);before=os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_uid!=os.geteuid() or stat.S_IMODE(before.st_mode)!=0o600 or before.st_nlink!=1 or not 1<=before.st_size<=maximum or os.get_inheritable(descriptor): raise ManifestHandoffRegistryUnavailable
        content=bytearray()
        while len(content)<=maximum:
            part=os.read(descriptor,min(65536,maximum+1-len(content)))
            if not part: break
            content.extend(part)
        after=os.fstat(descriptor);stable=("st_dev","st_ino","st_mode","st_nlink","st_size","st_mtime_ns","st_ctime_ns")
        if len(content)!=before.st_size or any(getattr(before,name)!=getattr(after,name) for name in stable): raise ManifestHandoffRegistryUnavailable
        return bytes(content)
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None
    finally:
        if descriptor is not None:
            try: os.close(descriptor)
            except Exception: pass

def _child_observed(directory:int,name:str,maximum:int):
    descriptor=None
    try:
        descriptor=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=directory);before=os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_uid!=os.geteuid() or stat.S_IMODE(before.st_mode)!=0o600 or before.st_nlink!=1 or not 1<=before.st_size<=maximum or os.get_inheritable(descriptor): raise ManifestHandoffRegistryUnavailable
        content=bytearray()
        while len(content)<=maximum:
            part=os.read(descriptor,min(65536,maximum+1-len(content)))
            if not part: break
            content.extend(part)
        after=os.fstat(descriptor)
        if len(content)!=before.st_size or _state(before)!=_state(after): raise ManifestHandoffRegistryUnavailable
        return bytes(content),_state(before)
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None
    finally:
        if descriptor is not None:
            try: os.close(descriptor)
            except Exception: pass

def _children(directory:int,names:tuple[str,...],limits:tuple[int,...])->tuple[bytes,...]:
    if len(names)!=len(limits): raise ManifestHandoffRegistryUnavailable
    values=[];total=0
    for name,limit in zip(names,limits):
        remaining=_MAX_SOURCE_SET_BYTES-total
        if remaining<=0: raise ManifestHandoffRegistryUnavailable
        value=_child(directory,name,min(limit,remaining));total+=len(value)
        values.append(value)
    return tuple(values)

def _validate_root(root:Path,directory:int,before:os.stat_result,names:tuple[str,...])->None:
    visible_directory=None
    try:
        after=os.fstat(directory);visible_directory=_open_root(root);visible=os.fstat(visible_directory)
        stable=("st_dev","st_ino","st_mode","st_uid","st_gid","st_nlink","st_size","st_mtime_ns","st_ctime_ns")
        if any(getattr(before,name)!=getattr(after,name) or getattr(after,name)!=getattr(visible,name) for name in stable) or set(os.listdir(directory))!=set(names): raise ManifestHandoffRegistryUnavailable
    finally:
        if visible_directory is not None:
            try: os.close(visible_directory)
            except Exception: pass

def load_source_set(root:Path)->JointEngineApiPolicyBoundProvenanceSnapshot:
    directory=None
    try:
        if not isinstance(root,Path) or not root.is_absolute() or root==Path("/") or ".." in root.parts: raise ManifestHandoffRegistryUnavailable
        directory=_open_root(root);before=os.fstat(directory)
        if not stat.S_ISDIR(before.st_mode) or before.st_uid!=os.geteuid() or stat.S_IMODE(before.st_mode)!=0o700 or os.get_inheritable(directory) or set(os.listdir(directory))!=set(_SOURCES): raise ManifestHandoffRegistryUnavailable
        values=_children(directory,_SOURCES,_LIMITS);_validate_root(root,directory,before,_SOURCES)
        return JointEngineApiPolicyBoundProvenanceSnapshot(values[0],JointEngineApiStagingProvenanceSnapshot(values[1],values[2],values[3],values[4],values[5:]))
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None
    finally:
        if directory is not None:
            try: os.close(directory)
            except Exception: pass

def load_image_bound_source_set(root:Path)->JointEngineApiImageBoundProvenanceSnapshot:
    directory=None
    try:
        names=("image-authority",*_SOURCES);limits=(1024,*_LIMITS)
        if not isinstance(root,Path) or not root.is_absolute() or root==Path("/") or ".." in root.parts: raise ManifestHandoffRegistryUnavailable
        directory=_open_root(root);before=os.fstat(directory)
        if not stat.S_ISDIR(before.st_mode) or before.st_uid!=os.geteuid() or stat.S_IMODE(before.st_mode)!=0o700 or os.get_inheritable(directory) or set(os.listdir(directory))!=set(names): raise ManifestHandoffRegistryUnavailable
        values=_children(directory,names,limits);_validate_root(root,directory,before,names)
        provenance=JointEngineApiPolicyBoundProvenanceSnapshot(values[1],JointEngineApiStagingProvenanceSnapshot(values[2],values[3],values[4],values[5],values[6:]))
        return JointEngineApiImageBoundProvenanceSnapshot(values[0],provenance)
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None
    finally:
        if directory is not None:
            try: os.close(directory)
            except Exception: pass

def observe_run_bound_source_set(root:Path,*,expected_root_identity:tuple[int,int]|None=None)->JointEngineApiRunBoundSourceObservation:
    directory=None
    try:
        names=("run-authority","run-envelope","run-signature","image-authority",*_SOURCES);limits=(1024,2048,256,1024,*_LIMITS)
        if not isinstance(root,Path) or not root.is_absolute() or root==Path("/") or ".." in root.parts or (expected_root_identity is not None and (type(expected_root_identity)is not tuple or len(expected_root_identity)!=2 or any(type(item)is not int or item<0 for item in expected_root_identity))): raise ManifestHandoffRegistryUnavailable
        directory=_open_root(root);before=os.fstat(directory)
        if not stat.S_ISDIR(before.st_mode) or before.st_uid!=os.geteuid() or stat.S_IMODE(before.st_mode)!=0o700 or os.get_inheritable(directory) or set(os.listdir(directory))!=set(names): raise ManifestHandoffRegistryUnavailable
        if expected_root_identity is not None and (before.st_dev,before.st_ino)!=expected_root_identity: raise ManifestHandoffRegistryUnavailable
        values=_children(directory,names,limits);confirmed=tuple(_child_observed(directory,name,limit) for name,limit in zip(names,limits))
        if tuple(value for value,_ in confirmed)!=values: raise ManifestHandoffRegistryUnavailable
        states=tuple(state for _,state in confirmed);_validate_root(root,directory,before,names)
        base=JointEngineApiStagingProvenanceSnapshot(values[5],values[6],values[7],values[8],values[9:]);policy=JointEngineApiPolicyBoundProvenanceSnapshot(values[4],base);image=JointEngineApiImageBoundProvenanceSnapshot(values[3],policy)
        return JointEngineApiRunBoundSourceObservation(JointEngineApiRunBoundProvenanceSnapshot(values[0],values[1],values[2],image),_state(before),states)
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None
    finally:
        if directory is not None:
            try: os.close(directory)
            except Exception: pass

def load_run_bound_source_set(root:Path,*,expected_root_identity:tuple[int,int]|None=None)->JointEngineApiRunBoundProvenanceSnapshot:
    return observe_run_bound_source_set(root,expected_root_identity=expected_root_identity).snapshot
