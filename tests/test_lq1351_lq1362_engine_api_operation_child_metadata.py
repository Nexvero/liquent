import os

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_operation_root as subject


def test_unchanged_operation_children_preserve_full_state(tmp_path):
    root = operation_root(tmp_path)
    resolved = subject.resolve_operation_root(root)
    assert resolved.source_identity == (os.stat(root / "source-set").st_dev, os.stat(root / "source-set").st_ino)
    assert resolved.acceptance_identity == (os.stat(root / "accepted-runs").st_dev, os.stat(root / "accepted-runs").st_ino)


@pytest.mark.parametrize("name", subject._CHILDREN)
@pytest.mark.parametrize("mutation", ("mode-cycle", "timestamp"))
def test_operation_child_metadata_change_during_resolution_is_rejected(tmp_path, monkeypatch, name, mutation):
    root = operation_root(tmp_path)
    original = subject._child_state
    calls = 0

    def changing(directory, child_name):
        nonlocal calls
        state = original(directory, child_name)
        calls += 1
        if calls == 2:
            target = root / name
            if mutation == "mode-cycle":
                target.chmod(0o750)
                target.chmod(0o700)
            else:
                os.utime(target, None)
        return state

    monkeypatch.setattr(subject, "_child_state", changing)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        subject.resolve_operation_root(root)


@pytest.mark.parametrize("name", subject._CHILDREN)
def test_child_state_contains_complete_stable_metadata(tmp_path, name):
    root = operation_root(tmp_path)
    descriptor = subject._open_root(root)
    try:
        state = subject._child_state(descriptor, name)
        facts = os.stat(root / name, follow_symlinks=False)
        expected = tuple(getattr(facts, field) for field in ("st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns"))
        assert state == expected
    finally:
        os.close(descriptor)


@pytest.mark.parametrize("name", subject._CHILDREN)
def test_child_state_rejects_non_private_directory(tmp_path, name):
    root = operation_root(tmp_path)
    (root / name).chmod(0o750)
    descriptor = subject._open_root(root)
    try:
        with pytest.raises(ManifestHandoffRegistryUnavailable):
            subject._child_state(descriptor, name)
    finally:
        os.close(descriptor)
