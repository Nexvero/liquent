import os

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport import manifest_handoff_supervisor_engine_api_staging_acceptance as subject
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_acceptance import build_staging_run_acceptance
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_run import decode_staging_run_authority
from tests.test_lq1135_lq1146_engine_api_run_acceptance import roots
from tools.engine_api_joint_staging_source_set import load_run_bound_source_set


def _material(tmp_path):
    source, registry = roots(tmp_path)
    snapshot = load_run_bound_source_set(source)
    value = build_staging_run_acceptance(decode_staging_run_authority(snapshot.run_authority), snapshot.run_envelope)
    return registry, value


def test_record_validates_visible_root_before_and_after_creation(tmp_path, monkeypatch):
    registry, value = _material(tmp_path)
    calls = []
    original = subject._validate_visible_root

    def recording(root, directory, before=None):
        calls.append((root, before))
        return original(root, directory, before)

    monkeypatch.setattr(subject, "_validate_visible_root", recording)
    subject.record_staging_run_acceptance(registry, value)
    assert calls == [(registry, None), (registry, None)]


@pytest.mark.parametrize("replacement", ("missing", "symlink", "directory"))
def test_rebinding_before_marker_creation_is_rejected_without_orphan(tmp_path, monkeypatch, replacement):
    parent = tmp_path / "real-parent"
    parent.mkdir()
    registry, value = _material(parent)
    moved = tmp_path / "moved-parent"
    original = subject.encode_staging_run_acceptance

    def rebinding(candidate):
        content = original(candidate)
        parent.rename(moved)
        if replacement == "symlink":
            parent.symlink_to(moved, target_is_directory=True)
        elif replacement == "directory":
            parent.mkdir()
            (parent / registry.name).mkdir(mode=0o700)
        return content

    monkeypatch.setattr(subject, "encode_staging_run_acceptance", rebinding)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        subject.record_staging_run_acceptance(registry, value)
    marker = value.run_id + ".accepted"
    assert not (moved / registry.name / marker).exists()
    if replacement == "directory":
        assert not (parent / registry.name / marker).exists()


def test_pre_create_gate_failure_never_opens_marker_name(tmp_path, monkeypatch):
    registry, value = _material(tmp_path)
    original_open = subject.os.open
    marker_opens = []

    def recording_open(path, *args, **kwargs):
        if isinstance(path, str) and path.endswith(".accepted"):
            marker_opens.append(path)
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(subject.os, "open", recording_open)
    monkeypatch.setattr(subject, "_validate_visible_root", lambda *args: (_ for _ in ()).throw(ManifestHandoffRegistryUnavailable))
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        subject.record_staging_run_acceptance(registry, value)
    assert marker_opens == []


def test_pre_create_gate_closes_its_visible_descriptor(tmp_path, monkeypatch):
    registry, _ = _material(tmp_path)
    directory = subject._open_root(registry)
    real_open = subject._open_root
    real_close = subject.os.close
    reopened = []
    closed = []

    def recording_open(path):
        descriptor = real_open(path)
        reopened.append(descriptor)
        return descriptor

    def recording_close(descriptor):
        closed.append(descriptor)
        return real_close(descriptor)

    monkeypatch.setattr(subject, "_open_root", recording_open)
    monkeypatch.setattr(subject.os, "close", recording_close)
    try:
        subject._validate_visible_root(registry, directory)
        assert reopened == [closed[-1]]
    finally:
        real_close(directory)


def test_pre_create_gate_does_not_mutate_empty_registry(tmp_path):
    registry, _ = _material(tmp_path)
    directory = subject._open_root(registry)
    try:
        before = os.fstat(directory)
        subject._validate_visible_root(registry, directory)
        after = os.fstat(directory)
        assert (before.st_size, before.st_mtime_ns, before.st_ctime_ns) == (after.st_size, after.st_mtime_ns, after.st_ctime_ns)
        assert list(registry.iterdir()) == []
    finally:
        os.close(directory)
