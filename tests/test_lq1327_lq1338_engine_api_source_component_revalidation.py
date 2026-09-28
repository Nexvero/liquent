import os
import shutil

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1123_lq1134_engine_api_run_bound_root import run_root
from tools import engine_api_joint_staging_source_set as subject


def _layout(tmp_path, generation):
    parent = tmp_path / "visible-parent"
    parent.mkdir()
    root = run_root(parent)
    if generation < 14:
        for name in ("run-authority", "run-envelope", "run-signature"):
            (root / name).unlink()
    if generation < 11:
        (root / "image-authority").unlink()
    loader = {10: subject.load_source_set, 11: subject.load_image_bound_source_set, 14: subject.load_run_bound_source_set}[generation]
    return parent, root, loader


def _after_capture(monkeypatch, action):
    original = subject._children

    def changing(directory, names, limits):
        values = original(directory, names, limits)
        action()
        return values

    monkeypatch.setattr(subject, "_children", changing)


@pytest.mark.parametrize("generation", (10, 11, 14))
def test_unchanged_component_chain_revalidates(tmp_path, generation):
    _, root, loader = _layout(tmp_path, generation)
    assert loader(root) is not None


@pytest.mark.parametrize("generation", (10, 11, 14))
def test_parent_disappearance_after_capture_is_rejected(tmp_path, monkeypatch, generation):
    parent, root, loader = _layout(tmp_path, generation)
    moved = tmp_path / "moved-parent"
    _after_capture(monkeypatch, lambda: parent.rename(moved))
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        loader(root)


@pytest.mark.parametrize("generation", (10, 11, 14))
def test_parent_symlink_rebinding_after_capture_is_rejected(tmp_path, monkeypatch, generation):
    parent, root, loader = _layout(tmp_path, generation)
    moved = tmp_path / "moved-parent"

    def rebind():
        parent.rename(moved)
        os.symlink(moved, parent)

    _after_capture(monkeypatch, rebind)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        loader(root)


@pytest.mark.parametrize("generation", (10, 11, 14))
def test_same_content_parent_replacement_after_capture_is_rejected(tmp_path, monkeypatch, generation):
    parent, root, loader = _layout(tmp_path, generation)
    moved = tmp_path / "moved-parent"

    def replace():
        parent.rename(moved)
        shutil.copytree(moved, parent)
        parent.chmod(moved.stat().st_mode & 0o777)
        for path in parent.rglob("*"):
            path.chmod((moved / path.relative_to(parent)).stat().st_mode & 0o777)

    _after_capture(monkeypatch, replace)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        loader(root)


def test_final_component_descriptor_is_closed(tmp_path, monkeypatch):
    _, root, _ = _layout(tmp_path, 14)
    directory = subject._open_root(root)
    before = os.fstat(directory)
    names = tuple(path.name for path in root.iterdir())
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
    try:
        subject._validate_root(root, directory, before, names)
        assert final == [closed[-1]]
    finally:
        real_close(directory)
