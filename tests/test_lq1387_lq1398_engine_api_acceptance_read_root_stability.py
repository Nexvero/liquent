import os

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport import manifest_handoff_supervisor_engine_api_staging_acceptance as subject
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_acceptance import build_staging_run_acceptance
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_run import decode_staging_run_authority
from tests.test_lq1135_lq1146_engine_api_run_acceptance import roots
from tools.engine_api_joint_staging_source_set import load_run_bound_source_set


def _accepted(tmp_path):
    source, registry = roots(tmp_path)
    snapshot = load_run_bound_source_set(source)
    value = build_staging_run_acceptance(decode_staging_run_authority(snapshot.run_authority), snapshot.run_envelope)
    subject.record_staging_run_acceptance(registry, value)
    return registry, value


@pytest.mark.parametrize("operation", ("load", "inspect"))
def test_unchanged_read_only_registry_root_remains_valid(tmp_path, operation):
    registry, value = _accepted(tmp_path)
    if operation == "load":
        assert subject.load_staging_run_acceptance(registry, value.run_id) == value
    else:
        assert subject.inspect_staging_run_acceptance_registry(registry) == (value,)


@pytest.mark.parametrize("operation", ("load", "inspect"))
@pytest.mark.parametrize("mutation", ("mode-cycle", "timestamp"))
def test_read_only_registry_rejects_transient_root_metadata_change(tmp_path, monkeypatch, operation, mutation):
    registry, value = _accepted(tmp_path)
    original = subject._load_acceptance_at
    changed = False

    def mutating(directory, run_id):
        nonlocal changed
        result = original(directory, run_id)
        if not changed:
            changed = True
            if mutation == "mode-cycle":
                registry.chmod(0o750)
                registry.chmod(0o700)
            else:
                os.utime(registry, None)
        return result

    monkeypatch.setattr(subject, "_load_acceptance_at", mutating)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        if operation == "load":
            subject.load_staging_run_acceptance(registry, value.run_id)
        else:
            subject.inspect_staging_run_acceptance_registry(registry)


def test_complete_read_root_validation_compares_initial_held_and_visible_facts(tmp_path, monkeypatch):
    registry, _ = _accepted(tmp_path)
    descriptor = subject._open_root(registry)
    before = os.fstat(descriptor)
    original = subject._open_root

    def changed(path):
        registry.chmod(0o750)
        registry.chmod(0o700)
        return original(path)

    monkeypatch.setattr(subject, "_open_root", changed)
    try:
        with pytest.raises(ManifestHandoffRegistryUnavailable):
            subject._validate_visible_root(registry, descriptor, before)
    finally:
        os.close(descriptor)


def test_record_uses_identity_validation_without_read_only_baseline(tmp_path, monkeypatch):
    source, registry = roots(tmp_path)
    snapshot = load_run_bound_source_set(source)
    value = build_staging_run_acceptance(decode_staging_run_authority(snapshot.run_authority), snapshot.run_envelope)
    observed = []
    original = subject._validate_visible_root

    def recording(root, directory, before=None):
        observed.append(before)
        return original(root, directory, before)

    monkeypatch.setattr(subject, "_validate_visible_root", recording)
    subject.record_staging_run_acceptance(registry, value)
    assert observed == [None, None]
