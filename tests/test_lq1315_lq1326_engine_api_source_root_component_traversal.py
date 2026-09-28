import os

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1123_lq1134_engine_api_run_bound_root import run_root
from tools import engine_api_joint_staging_source_set as subject


def _layout(parent, generation):
    root = run_root(parent)
    if generation < 14:
        for name in ("run-authority", "run-envelope", "run-signature"):
            (root / name).unlink()
    if generation < 11:
        (root / "image-authority").unlink()
    loader = {10: subject.load_source_set, 11: subject.load_image_bound_source_set, 14: subject.load_run_bound_source_set}[generation]
    return root, loader


@pytest.mark.parametrize("generation", (10, 11, 14))
def test_real_component_chain_loads_each_source_layout(tmp_path, generation):
    parent = tmp_path / "real-parent"
    parent.mkdir()
    root, loader = _layout(parent, generation)
    assert loader(root) is not None


@pytest.mark.parametrize("generation", (10, 11, 14))
def test_symlinked_parent_component_is_rejected(tmp_path, generation):
    parent = tmp_path / "real-parent"
    parent.mkdir()
    root, loader = _layout(parent, generation)
    alias_parent = tmp_path / "alias-parent"
    alias_parent.symlink_to(parent, target_is_directory=True)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        loader(alias_parent / root.name)


@pytest.mark.parametrize("generation", (10, 11, 14))
def test_symlinked_leaf_component_remains_rejected(tmp_path, generation):
    parent = tmp_path / "real-parent"
    parent.mkdir()
    root, loader = _layout(parent, generation)
    alias = parent / "alias-source-set"
    alias.symlink_to(root, target_is_directory=True)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        loader(alias)


def test_component_walk_returns_the_exact_leaf_identity(tmp_path):
    parent = tmp_path / "real-parent"
    parent.mkdir()
    root, _ = _layout(parent, 14)
    descriptor = subject._open_root(root)
    try:
        opened = os.fstat(descriptor)
        visible = os.stat(root, follow_symlinks=False)
        assert (opened.st_dev, opened.st_ino) == (visible.st_dev, visible.st_ino)
        assert not os.get_inheritable(descriptor)
    finally:
        os.close(descriptor)


def test_component_walk_closes_prior_descriptors(tmp_path, monkeypatch):
    parent = tmp_path / "real-parent"
    parent.mkdir()
    root, _ = _layout(parent, 14)
    real_open = subject.os.open
    real_close = subject.os.close
    opened = []
    closed = []

    def recording_open(*args, **kwargs):
        descriptor = real_open(*args, **kwargs)
        opened.append(descriptor)
        return descriptor

    def recording_close(descriptor):
        closed.append(descriptor)
        return real_close(descriptor)

    monkeypatch.setattr(subject.os, "open", recording_open)
    monkeypatch.setattr(subject.os, "close", recording_close)
    descriptor = subject._open_root(root)
    try:
        assert closed == opened[:-1]
        assert descriptor == opened[-1]
    finally:
        real_close(descriptor)
