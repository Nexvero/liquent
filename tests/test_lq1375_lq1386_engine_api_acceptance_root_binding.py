import os

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport import manifest_handoff_supervisor_engine_api_staging_acceptance as subject
from tests.test_lq1135_lq1146_engine_api_run_acceptance import roots
from tools.engine_api_joint_staging_source_set import load_run_bound_source_set
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_acceptance import build_staging_run_acceptance
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_run import decode_staging_run_authority


def _value(tmp_path):
    source, registry = roots(tmp_path)
    snapshot = load_run_bound_source_set(source)
    authority = decode_staging_run_authority(snapshot.run_authority)
    return registry, build_staging_run_acceptance(authority, snapshot.run_envelope)


@pytest.mark.parametrize("operation", ("load", "inspect", "record"))
def test_acceptance_operation_rejects_symlinked_parent_component(tmp_path, operation):
    real_parent = tmp_path / "real-parent"
    real_parent.mkdir()
    registry, value = _value(real_parent)
    alias_parent = tmp_path / "alias-parent"
    alias_parent.symlink_to(real_parent, target_is_directory=True)
    alias = alias_parent / registry.name
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        if operation == "load":
            subject.load_staging_run_acceptance(alias, value.run_id)
        elif operation == "inspect":
            subject.inspect_staging_run_acceptance_registry(alias)
        else:
            subject.record_staging_run_acceptance(alias, value)


def test_unchanged_registry_supports_record_load_and_inspect(tmp_path):
    registry, value = _value(tmp_path)
    subject.record_staging_run_acceptance(registry, value)
    assert subject.load_staging_run_acceptance(registry, value.run_id) == value
    assert subject.inspect_staging_run_acceptance_registry(registry) == (value,)


def test_load_rejects_parent_symlink_rebinding_after_marker_read(tmp_path, monkeypatch):
    parent = tmp_path / "real-parent"
    parent.mkdir()
    registry, value = _value(parent)
    subject.record_staging_run_acceptance(registry, value)
    moved = tmp_path / "moved-parent"
    original = subject._load_acceptance_at

    def rebinding(directory, run_id):
        result = original(directory, run_id)
        parent.rename(moved)
        parent.symlink_to(moved, target_is_directory=True)
        return result

    monkeypatch.setattr(subject, "_load_acceptance_at", rebinding)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        subject.load_staging_run_acceptance(registry, value.run_id)


def test_inspect_rejects_parent_symlink_rebinding_after_marker_read(tmp_path, monkeypatch):
    parent = tmp_path / "real-parent"
    parent.mkdir()
    registry, value = _value(parent)
    subject.record_staging_run_acceptance(registry, value)
    moved = tmp_path / "moved-parent"
    original = subject._load_acceptance_at

    def rebinding(directory, run_id):
        result = original(directory, run_id)
        parent.rename(moved)
        parent.symlink_to(moved, target_is_directory=True)
        return result

    monkeypatch.setattr(subject, "_load_acceptance_at", rebinding)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        subject.inspect_staging_run_acceptance_registry(registry)


def test_record_rejects_parent_rebinding_without_writing_to_rebound_path(tmp_path, monkeypatch):
    parent = tmp_path / "real-parent"
    parent.mkdir()
    registry, value = _value(parent)
    moved = tmp_path / "moved-parent"
    original = subject._validate_visible_root
    calls = 0

    def rebinding(root, directory, before=None):
        nonlocal calls
        calls += 1
        if calls == 2:
            parent.rename(moved)
            parent.mkdir()
            rebound = parent / registry.name
            rebound.mkdir(mode=0o700)
        return original(root, directory, before)

    monkeypatch.setattr(subject, "_validate_visible_root", rebinding)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        subject.record_staging_run_acceptance(registry, value)
    assert (moved / registry.name / (value.run_id + ".accepted")).is_file()
    assert not (parent / registry.name / (value.run_id + ".accepted")).exists()


def test_visible_root_validation_closes_reopened_descriptor(tmp_path, monkeypatch):
    registry, _ = _value(tmp_path)
    descriptor = subject._open_root(registry)
    real_open = subject._open_root
    real_close = subject.os.close
    reopened = []
    closed = []

    def recording_open(path):
        value = real_open(path)
        reopened.append(value)
        return value

    def recording_close(value):
        closed.append(value)
        return real_close(value)

    monkeypatch.setattr(subject, "_open_root", recording_open)
    monkeypatch.setattr(subject.os, "close", recording_close)
    try:
        subject._validate_visible_root(registry, descriptor)
        assert reopened == [closed[-1]]
    finally:
        real_close(descriptor)
