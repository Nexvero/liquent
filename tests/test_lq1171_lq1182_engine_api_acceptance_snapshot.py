import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport import manifest_handoff_supervisor_engine_api_staging_acceptance as subject
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_acceptance import build_staging_run_acceptance,inspect_staging_run_acceptance_registry,record_staging_run_acceptance
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_run import decode_staging_run_authority
from tools.engine_api_joint_staging_source_set import load_run_bound_source_set
from tests.test_lq1135_lq1146_engine_api_run_acceptance import roots

def accepted(tmp_path):
    source,root=roots(tmp_path);snapshot=load_run_bound_source_set(source);record_staging_run_acceptance(root,build_staging_run_acceptance(decode_staging_run_authority(snapshot.run_authority),snapshot.run_envelope));return root

def test_inventory_uses_one_working_and_one_final_registry_root_descriptor(tmp_path,monkeypatch):
    root=accepted(tmp_path);original=subject._open_root;root_calls=[]
    def observed(path):
        root_calls.append(path);return original(path)
    monkeypatch.setattr(subject,"_open_root",observed);assert len(inspect_staging_run_acceptance_registry(root))==1 and root_calls==[root,root]

def test_inventory_uses_descriptor_relative_marker_open(tmp_path,monkeypatch):
    root=accepted(tmp_path);original=subject.os.open;child_calls=[]
    def observed(path,*args,**kwargs):
        if isinstance(path,str) and path.endswith(".accepted"): child_calls.append(kwargs.get("dir_fd"))
        return original(path,*args,**kwargs)
    monkeypatch.setattr(subject.os,"open",observed);inspect_staging_run_acceptance_registry(root);assert len(child_calls)==1 and child_calls[0] is not None

def test_inventory_rejects_name_set_change_during_snapshot(tmp_path,monkeypatch):
    root=accepted(tmp_path);original=subject._load_acceptance_at
    def mutating(directory,run_id):
        value=original(directory,run_id);path=root/"unexpected";path.write_bytes(b"x");path.chmod(0o600);return value
    monkeypatch.setattr(subject,"_load_acceptance_at",mutating)
    with pytest.raises(ManifestHandoffRegistryUnavailable): inspect_staging_run_acceptance_registry(root)

def test_inventory_rejects_marker_metadata_change_during_read(tmp_path,monkeypatch):
    root=accepted(tmp_path);original=subject.os.read;changed=False
    def mutating(descriptor,size):
        nonlocal changed
        value=original(descriptor,size)
        if not changed: changed=True;(next(root.iterdir())).touch()
        return value
    monkeypatch.setattr(subject.os,"read",mutating)
    with pytest.raises(ManifestHandoffRegistryUnavailable): inspect_staging_run_acceptance_registry(root)

def test_empty_registry_is_single_open_stable_snapshot(tmp_path):
    _,root=roots(tmp_path);assert inspect_staging_run_acceptance_registry(root)==()
