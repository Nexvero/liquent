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
    return registry, value, subject.encode_staging_run_acceptance(value)


def test_record_verifies_exact_created_marker_bytes(tmp_path, monkeypatch):
    registry, value, content = _material(tmp_path)
    observed = []
    original = subject._verify_created_acceptance

    def recording(descriptor, expected):
        observed.append(expected)
        return original(descriptor, expected)

    monkeypatch.setattr(subject, "_verify_created_acceptance", recording)
    subject.record_staging_run_acceptance(registry, value)
    assert observed == [content]
    assert (registry / (value.run_id + ".accepted")).read_bytes() == content


def test_created_marker_descriptor_is_opened_read_write(tmp_path, monkeypatch):
    registry, value, _ = _material(tmp_path)
    original = subject.os.open
    flags = []

    def recording(path, value_flags, *args, **kwargs):
        if isinstance(path, str) and path.endswith(".accepted"):
            flags.append(value_flags)
        return original(path, value_flags, *args, **kwargs)

    monkeypatch.setattr(subject.os, "open", recording)
    subject.record_staging_run_acceptance(registry, value)
    assert len(flags) == 1 and flags[0] & os.O_RDWR


@pytest.mark.parametrize("mutation", ("mode", "content", "short-read"))
def test_post_write_verification_rejects_and_removes_untrusted_marker(tmp_path, monkeypatch, mutation):
    registry, value, content = _material(tmp_path)
    marker = registry / (value.run_id + ".accepted")
    original = subject._verify_created_acceptance

    def rejecting(descriptor, expected):
        if mutation == "mode":
            marker.chmod(0o640)
            return original(descriptor, expected)
        if mutation == "content":
            os.lseek(descriptor, 0, os.SEEK_SET)
            os.write(descriptor, b"x" * len(content))
            os.fsync(descriptor)
            return original(descriptor, expected)
        real_read = subject.os.read
        monkeypatch.setattr(subject.os, "read", lambda fd, size: b"" if fd == descriptor else real_read(fd, size))
        return original(descriptor, expected)

    monkeypatch.setattr(subject, "_verify_created_acceptance", rejecting)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        subject.record_staging_run_acceptance(registry, value)
    assert not marker.exists()


def test_post_write_verification_rejects_hard_linked_marker(tmp_path):
    registry, value, content = _material(tmp_path)
    marker = registry / (value.run_id + ".accepted")
    marker.write_bytes(content)
    marker.chmod(0o600)
    linked = registry / "linked.accepted"
    os.link(marker, linked)
    descriptor = os.open(marker, os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        with pytest.raises(ManifestHandoffRegistryUnavailable):
            subject._verify_created_acceptance(descriptor, content)
    finally:
        os.close(descriptor)


def test_post_write_verification_rejects_metadata_change_during_readback(tmp_path, monkeypatch):
    registry, value, content = _material(tmp_path)
    marker = registry / (value.run_id + ".accepted")
    marker.write_bytes(content)
    marker.chmod(0o600)
    descriptor = os.open(marker, os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC)
    original = subject.os.read
    changed = False

    def mutating(fd, size):
        nonlocal changed
        result = original(fd, size)
        if not changed:
            changed = True
            marker.touch()
        return result

    monkeypatch.setattr(subject.os, "read", mutating)
    try:
        with pytest.raises(ManifestHandoffRegistryUnavailable):
            subject._verify_created_acceptance(descriptor, content)
    finally:
        os.close(descriptor)
