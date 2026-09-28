import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tools import engine_api_joint_staging_source_set as subject
from tests.test_lq1123_lq1134_engine_api_run_bound_root import run_root

def test_run_source_snapshot_remains_valid_when_unchanged(tmp_path):
    root=run_root(tmp_path);assert subject.load_run_bound_source_set(root).run_authority==(root/"run-authority").read_bytes()

@pytest.mark.parametrize("target",("run-authority","trust","evidence","render"))
def test_source_snapshot_rejects_metadata_change_during_child_read(tmp_path,monkeypatch,target):
    root=run_root(tmp_path);original=subject.os.read;changed=False
    def mutating(descriptor,size):
        nonlocal changed
        value=original(descriptor,size)
        if not changed:
            candidate=root/target
            if candidate.stat().st_ino==subject.os.fstat(descriptor).st_ino: changed=True;candidate.touch()
        return value
    monkeypatch.setattr(subject.os,"read",mutating)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.load_run_bound_source_set(root)

def test_source_snapshot_rejects_name_set_change_during_capture(tmp_path,monkeypatch):
    root=run_root(tmp_path);original=subject._child;changed=False
    def mutating(directory,name,maximum):
        nonlocal changed
        value=original(directory,name,maximum)
        if not changed: changed=True;path=root/"unexpected";path.write_bytes(b"x");path.chmod(0o600)
        return value
    monkeypatch.setattr(subject,"_child",mutating)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.load_run_bound_source_set(root)

def test_source_snapshot_rejects_missing_name_during_capture(tmp_path,monkeypatch):
    root=run_root(tmp_path);original=subject._child;changed=False
    def mutating(directory,name,maximum):
        nonlocal changed
        value=original(directory,name,maximum)
        if not changed: changed=True;(root/"shutdown").unlink()
        return value
    monkeypatch.setattr(subject,"_child",mutating)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.load_run_bound_source_set(root)

def test_all_source_layout_generations_use_stable_directory_metadata(tmp_path):
    root=run_root(tmp_path);subject.load_run_bound_source_set(root)
    for name in ("run-authority","run-envelope","run-signature"): (root/name).unlink()
    subject.load_image_bound_source_set(root)
    (root/"image-authority").unlink();subject.load_source_set(root)
