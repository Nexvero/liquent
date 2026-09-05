import os
import shutil

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_operation_root as subject


def test_real_operation_root_component_chain_resolves(tmp_path):
    root = operation_root(tmp_path)
    assert subject.resolve_operation_root(root).root_identity == (root.stat().st_dev, root.stat().st_ino)


def test_symlinked_operation_root_parent_is_rejected(tmp_path):
    real_parent = tmp_path / "real-parent"
    real_parent.mkdir()
    root = operation_root(real_parent)
    alias = tmp_path / "alias-parent"
    alias.symlink_to(real_parent, target_is_directory=True)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        subject.resolve_operation_root(alias / root.name)


def test_symlinked_operation_root_leaf_is_rejected(tmp_path):
    root = operation_root(tmp_path)
    alias = tmp_path / "operation-alias"
    alias.symlink_to(root, target_is_directory=True)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        subject.resolve_operation_root(alias)


@pytest.mark.parametrize("replacement", ("missing", "symlink", "copy"))
def test_operation_root_path_rebinding_during_resolution_is_rejected(tmp_path, monkeypatch, replacement):
    root = operation_root(tmp_path)
    moved = tmp_path / "moved-operation"
    original = subject._child_identity
    calls = 0

    def changing(directory, name):
        nonlocal calls
        identity = original(directory, name)
        calls += 1
        if calls == 2:
            root.rename(moved)
            if replacement == "symlink":
                root.symlink_to(moved, target_is_directory=True)
            elif replacement == "copy":
                shutil.copytree(moved, root)
                root.chmod(0o700)
                for path in root.rglob("*"):
                    path.chmod((moved / path.relative_to(root)).stat().st_mode & 0o777)
        return identity

    monkeypatch.setattr(subject, "_child_identity", changing)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        subject.resolve_operation_root(root)


@pytest.mark.parametrize("name", subject._CHILDREN)
def test_operation_child_replacement_during_resolution_is_rejected(tmp_path, monkeypatch, name):
    root = operation_root(tmp_path)
    original = subject._child_identity
    calls = 0

    def changing(directory, child_name):
        nonlocal calls
        identity = original(directory, child_name)
        calls += 1
        if calls == 2:
            target = root / name
            moved = root / (name + "-moved")
            target.rename(moved)
            shutil.copytree(moved, target)
            target.chmod(0o700)
            for path in target.rglob("*"):
                path.chmod((moved / path.relative_to(target)).stat().st_mode & 0o777)
        return identity

    monkeypatch.setattr(subject, "_child_identity", changing)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        subject.resolve_operation_root(root)


def test_operation_root_final_descriptor_is_closed(tmp_path, monkeypatch):
    root = operation_root(tmp_path)
    real_open = subject._open_root
    real_close = subject.os.close
    final = []
    closed = []

    def recording_open(path):
        descriptor = real_open(path)
        final.append(descriptor)
        return descriptor

    def recording_close(descriptor):
        closed.append(descriptor)
        return real_close(descriptor)

    monkeypatch.setattr(subject, "_open_root", recording_open)
    monkeypatch.setattr(subject.os, "close", recording_close)
    subject.resolve_operation_root(root)
    assert len(final) == 2
    assert final[-1] in closed
