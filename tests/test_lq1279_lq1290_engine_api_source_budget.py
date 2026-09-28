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
    names = tuple(sorted(path.name for path in root.iterdir()))
    return root, names, sum((root / name).stat().st_size for name in names)


def _load(generation, root):
    return {10: subject.load_source_set, 11: subject.load_image_bound_source_set, 14: subject.load_run_bound_source_set}[generation](root)


def test_source_set_budget_is_fixed_at_sixty_four_mibibytes():
    assert subject._MAX_SOURCE_SET_BYTES == 64 * 1024 * 1024


def test_children_rejects_mismatched_name_and_limit_sets(tmp_path):
    root, _, _ = _layout(tmp_path, 10)
    descriptor = subject.os.open(root, subject.os.O_RDONLY | subject.os.O_DIRECTORY)
    try:
        with pytest.raises(ManifestHandoffRegistryUnavailable):
            subject._children(descriptor, ("trust",), ())
    finally:
        subject.os.close(descriptor)


@pytest.mark.parametrize("generation", (10, 11, 14))
def test_each_source_layout_accepts_its_exact_cumulative_size(tmp_path, monkeypatch, generation):
    root, _, total = _layout(tmp_path, generation)
    monkeypatch.setattr(subject, "_MAX_SOURCE_SET_BYTES", total)
    assert _load(generation, root) is not None


@pytest.mark.parametrize("generation", (10, 11, 14))
def test_each_source_layout_rejects_one_byte_below_its_cumulative_size(tmp_path, monkeypatch, generation):
    root, _, total = _layout(tmp_path, generation)
    monkeypatch.setattr(subject, "_MAX_SOURCE_SET_BYTES", total - 1)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        _load(generation, root)


@pytest.mark.parametrize("generation", (10, 11, 14))
def test_budget_rejection_stops_before_remaining_sources_are_read(tmp_path, monkeypatch, generation):
    root, _, _ = _layout(tmp_path, generation)
    original = subject._child
    calls = []

    def recording(directory, name, maximum):
        calls.append(name)
        return original(directory, name, maximum)

    monkeypatch.setattr(subject, "_child", recording)
    first_names = {10: subject._SOURCES, 11: ("image-authority", *subject._SOURCES), 14: ("run-authority", "run-envelope", "run-signature", "image-authority", *subject._SOURCES)}[generation]
    cutoff = sum((root / name).stat().st_size for name in first_names[:2]) - 1
    monkeypatch.setattr(subject, "_MAX_SOURCE_SET_BYTES", cutoff)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        _load(generation, root)
    assert calls == list(first_names[:2])


def test_budget_is_evaluated_from_loaded_bytes_not_declared_per_file_limits(tmp_path, monkeypatch):
    root, _, total = _layout(tmp_path, 14)
    assert sum((1024, 2048, 256, 1024, *subject._LIMITS)) > total
    monkeypatch.setattr(subject, "_MAX_SOURCE_SET_BYTES", total)
    subject.load_run_bound_source_set(root)
