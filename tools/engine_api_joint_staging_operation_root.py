"""Fixed owner-private operation root binding source and acceptance state."""
from dataclasses import dataclass,replace
import os,stat
from pathlib import Path
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable

_CHILDREN=("source-set","accepted-runs")

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

def _child_identity(directory:int,name:str)->tuple[int,int]:
    child=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=directory)
    try:
        facts=os.fstat(child)
        if not stat.S_ISDIR(facts.st_mode) or facts.st_uid!=os.geteuid() or stat.S_IMODE(facts.st_mode)!=0o700 or os.get_inheritable(child): raise ManifestHandoffRegistryUnavailable
        return facts.st_dev,facts.st_ino
    finally: os.close(child)

def _child_state(directory:int,name:str)->tuple[int,...]:
    child=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=directory)
    try:
        facts=os.fstat(child)
        if not stat.S_ISDIR(facts.st_mode) or facts.st_uid!=os.geteuid() or stat.S_IMODE(facts.st_mode)!=0o700 or os.get_inheritable(child): raise ManifestHandoffRegistryUnavailable
        return tuple(getattr(facts,field) for field in ("st_dev","st_ino","st_mode","st_uid","st_gid","st_nlink","st_size","st_mtime_ns","st_ctime_ns"))
    finally: os.close(child)

def _validate_root(root:Path,directory:int,before:os.stat_result,identities:tuple[tuple[int,int],...],states:tuple[tuple[int,...],...])->None:
    visible_directory=None
    try:
        after=os.fstat(directory);visible_directory=_open_root(root);visible=os.fstat(visible_directory)
        stable=("st_dev","st_ino","st_mode","st_uid","st_gid","st_nlink","st_size","st_mtime_ns","st_ctime_ns")
        if any(getattr(before,name)!=getattr(after,name) or getattr(after,name)!=getattr(visible,name) for name in stable) or set(os.listdir(directory))!=set(_CHILDREN) or set(os.listdir(visible_directory))!=set(_CHILDREN): raise ManifestHandoffRegistryUnavailable
        if tuple(_child_identity(visible_directory,name) for name in _CHILDREN)!=identities: raise ManifestHandoffRegistryUnavailable
        if tuple(_child_state(visible_directory,name) for name in _CHILDREN)!=states: raise ManifestHandoffRegistryUnavailable
    finally:
        if visible_directory is not None:
            try: os.close(visible_directory)
            except Exception: pass

@dataclass(frozen=True,slots=True)
class JointEngineApiStagingOperationRoots:
    source_root:Path
    acceptance_root:Path
    root_identity:tuple[int,int]
    source_identity:tuple[int,int]
    acceptance_identity:tuple[int,int]
    root_state:tuple[int,...]
    source_state:tuple[int,...]
    acceptance_state:tuple[int,...]
    def __post_init__(self):
        paths=(self.source_root,self.acceptance_root);identities=(self.root_identity,self.source_identity,self.acceptance_identity)
        states=(self.root_state,self.source_state,self.acceptance_state)
        invalid_paths=any(not isinstance(value,Path) or not value.is_absolute() or value==Path("/") or ".." in value.parts for value in paths) or self.source_root.name!="source-set" or self.acceptance_root.name!="accepted-runs" or self.source_root.parent!=self.acceptance_root.parent
        invalid_identities=any(type(value)is not tuple or len(value)!=2 or any(type(item)is not int or item<0 for item in value) for value in identities) or len(set(identities))!=3
        invalid_states=any(type(value)is not tuple or len(value)!=9 or any(type(item)is not int or item<0 for item in value) for value in states) or any(state[:2]!=identity for state,identity in zip(states,identities)) or any(not stat.S_ISDIR(state[2]) or state[3]!=os.geteuid() or stat.S_IMODE(state[2])!=0o700 for state in states)
        if invalid_paths or invalid_identities or invalid_states: raise ManifestHandoffRegistryUnavailable
    def __repr__(self): return "JointEngineApiStagingOperationRoots()"

def resolve_operation_root(root:Path):
    directory=None
    try:
        if not isinstance(root,Path) or not root.is_absolute() or root==Path("/") or ".." in root.parts: raise ManifestHandoffRegistryUnavailable
        directory=_open_root(root);before=os.fstat(directory)
        if not stat.S_ISDIR(before.st_mode) or before.st_uid!=os.geteuid() or stat.S_IMODE(before.st_mode)!=0o700 or os.get_inheritable(directory) or set(os.listdir(directory))!=set(_CHILDREN): raise ManifestHandoffRegistryUnavailable
        identities=tuple(_child_identity(directory,name) for name in _CHILDREN);states=tuple(_child_state(directory,name) for name in _CHILDREN);_validate_root(root,directory,before,identities,states)
        return JointEngineApiStagingOperationRoots(*(root/name for name in _CHILDREN),(before.st_dev,before.st_ino),*identities,_child_state(directory,"."),*states)
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None
    finally:
        if directory is not None:
            try: os.close(directory)
            except Exception: pass

def validate_operation_roots(root:Path,expected:JointEngineApiStagingOperationRoots,*,allow_acceptance_state_change:bool=False)->None:
    try:
        if type(expected)is not JointEngineApiStagingOperationRoots or type(allow_acceptance_state_change)is not bool: raise ManifestHandoffRegistryUnavailable
        current=resolve_operation_root(root)
        if allow_acceptance_state_change: expected=replace(expected,acceptance_state=current.acceptance_state)
        if current!=expected: raise ManifestHandoffRegistryUnavailable
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None
