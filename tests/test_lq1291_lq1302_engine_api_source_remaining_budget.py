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
    names = {10: subject._SOURCES, 11: ("image-authority", *subject._SOURCES), 14: ("run-authority", "run-envelope", "run-signature", "image-authority", *subject._SOURCES)}[generation]
    limits = {10: subject._LIMITS, 11: (1024, *subject._LIMITS), 14: (1024, 2048, 256, 1024, *subject._LIMITS)}[generation]
    loader = {10: subject.load_source_set, 11: subject.load_image_bound_source_set, 14: subject.load_run_bound_source_set}[generation]
    return root, names, limits, loader


@pytest.mark.parametrize("generation", (10, 11, 14))
def test_next_source_receives_only_the_remaining_aggregate_budget(tmp_path, monkeypatch, generation):
    root, names, limits, loader = _layout(tmp_path, generation)
    first_size = (root / names[0]).stat().st_size
    second_size = (root / names[1]).stat().st_size
    monkeypatch.setattr(subject, "_MAX_SOURCE_SET_BYTES", first_size + second_size - 1)
    original = subject._child
    observed = []

    def recording(directory, name, maximum):
        observed.append((name, maximum))
        return original(directory, name, maximum)

    monkeypatch.setattr(subject, "_child", recording)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        loader(root)
    assert observed == [(names[0], min(limits[0], first_size + second_size - 1)), (names[1], second_size - 1)]


@pytest.mark.parametrize("generation", (10, 11, 14))
def test_exhausted_budget_rejects_before_opening_the_next_source(tmp_path, monkeypatch, generation):
    root, names, _, loader = _layout(tmp_path, generation)
    monkeypatch.setattr(subject, "_MAX_SOURCE_SET_BYTES", (root / names[0]).stat().st_size)
    original = subject._child
    opened = []

    def recording(directory, name, maximum):
        opened.append(name)
        return original(directory, name, maximum)

    monkeypatch.setattr(subject, "_child", recording)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        loader(root)
    assert opened == [names[0]]


@pytest.mark.parametrize("generation", (10, 11, 14))
def test_normal_layout_keeps_each_existing_per_source_limit(tmp_path, monkeypatch, generation):
    root, names, limits, loader = _layout(tmp_path, generation)
    original = subject._child
    observed = []

    def recording(directory, name, maximum):
        observed.append((name, maximum))
        return original(directory, name, maximum)

    monkeypatch.setattr(subject, "_child", recording)
    loader(root)
    assert observed == list(zip(names, limits))


def test_zero_aggregate_budget_opens_no_source(tmp_path, monkeypatch):
    root, _, _, loader = _layout(tmp_path, 14)
    monkeypatch.setattr(subject, "_MAX_SOURCE_SET_BYTES", 0)
    monkeypatch.setattr(subject, "_child", lambda *args: pytest.fail("source opened after budget exhaustion"))
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        loader(root)
