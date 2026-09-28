import os

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1123_lq1134_engine_api_run_bound_root import run_root
from tools import engine_api_joint_staging_source_set as subject


def _layout(tmp_path, generation):
    root = run_root(tmp_path)
    if generation < 14:
        for name in ("run-authority", "run-envelope", "run-signature"):
            (root / name).unlink()
    if generation < 11:
        (root / "image-authority").unlink()
    loader = {10: subject.load_source_set, 11: subject.load_image_bound_source_set, 14: subject.load_run_bound_source_set}[generation]
    return root, loader


def _after_capture(monkeypatch, action):
    original = subject._children

    def changing(directory, names, limits):
        values = original(directory, names, limits)
        action(names)
        return values

    monkeypatch.setattr(subject, "_children", changing)


@pytest.mark.parametrize("generation", (10, 11, 14))
def test_unchanged_visible_root_remains_bound_to_open_descriptor(tmp_path, generation):
    root, loader = _layout(tmp_path, generation)
    assert loader(root) is not None


@pytest.mark.parametrize("generation", (10, 11, 14))
def test_root_path_disappearance_after_capture_is_rejected(tmp_path, monkeypatch, generation):
    root, loader = _layout(tmp_path, generation)
    moved = root.with_name("moved-source-set")
    _after_capture(monkeypatch, lambda names: root.rename(moved))
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        loader(root)


@pytest.mark.parametrize("generation", (10, 11, 14))
def test_root_path_replacement_with_same_contents_is_rejected(tmp_path, monkeypatch, generation):
    root, loader = _layout(tmp_path, generation)
    moved = root.with_name("moved-source-set")

    def replace(names):
        root.rename(moved)
        root.mkdir(mode=0o700)
        for name in names:
            target = root / name
            target.write_bytes((moved / name).read_bytes())
            target.chmod(0o600)

    _after_capture(monkeypatch, replace)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        loader(root)


@pytest.mark.parametrize("generation", (10, 11, 14))
def test_root_path_symlink_rebinding_is_rejected(tmp_path, monkeypatch, generation):
    root, loader = _layout(tmp_path, generation)
    moved = root.with_name("moved-source-set")

    def replace_with_symlink(names):
        root.rename(moved)
        os.symlink(moved, root)

    _after_capture(monkeypatch, replace_with_symlink)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        loader(root)


def test_root_validation_rejects_visible_identity_mismatch(tmp_path):
    root, _ = _layout(tmp_path, 14)
    descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    before = os.fstat(descriptor)
    moved = root.with_name("moved-source-set")
    root.rename(moved)
    root.mkdir(mode=0o700)
    try:
        with pytest.raises(ManifestHandoffRegistryUnavailable):
            subject._validate_root(root, descriptor, before, tuple(path.name for path in moved.iterdir()))
    finally:
        os.close(descriptor)
