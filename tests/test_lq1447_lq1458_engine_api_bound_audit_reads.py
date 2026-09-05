import shutil

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport import manifest_handoff_supervisor_engine_api_staging_acceptance as registry_subject
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1123_lq1134_engine_api_run_bound_root import RUN
from tests.test_lq1135_lq1146_engine_api_run_acceptance import roots
from tests.test_lq1159_lq1170_engine_api_acceptance_audit import accept
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_acceptance_audit as audit_subject
from tools import engine_api_joint_staging_operation_verify as operation_subject
from tools.engine_api_joint_staging_operation_root import resolve_operation_root


@pytest.mark.parametrize("operation", ("load", "inspect"))
def test_acceptance_reads_accept_exact_expected_registry_identity(tmp_path, operation):
    source, registry = roots(tmp_path)
    identity = (registry.stat().st_dev, registry.stat().st_ino)
    if operation == "load":
        assert registry_subject.load_staging_run_acceptance(registry, RUN, expected_root_identity=identity) is None
    else:
        assert registry_subject.inspect_staging_run_acceptance_registry(registry, expected_root_identity=identity) == ()


@pytest.mark.parametrize("expected", ((-1, 1), (True, 1), (1,), [1, 2], "1:2"))
@pytest.mark.parametrize("operation", ("load", "inspect"))
def test_acceptance_reads_reject_malformed_expected_identity(tmp_path, expected, operation):
    _, registry = roots(tmp_path)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        if operation == "load":
            registry_subject.load_staging_run_acceptance(registry, RUN, expected_root_identity=expected)
        else:
            registry_subject.inspect_staging_run_acceptance_registry(registry, expected_root_identity=expected)


@pytest.mark.parametrize("operation", ("load", "inspect"))
def test_acceptance_reads_reject_same_content_registry_replacement(tmp_path, operation):
    _, registry = roots(tmp_path)
    identity = (registry.stat().st_dev, registry.stat().st_ino)
    moved = registry.with_name("old-accepted-runs")
    registry.rename(moved)
    shutil.copytree(moved, registry)
    registry.chmod(0o700)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        if operation == "load":
            registry_subject.load_staging_run_acceptance(registry, RUN, expected_root_identity=identity)
        else:
            registry_subject.inspect_staging_run_acceptance_registry(registry, expected_root_identity=identity)


def test_accepted_source_audit_passes_both_identities_to_all_reads(tmp_path, monkeypatch):
    source, registry = roots(tmp_path)
    accept(source, registry)
    source_identity = (source.stat().st_dev, source.stat().st_ino)
    acceptance_identity = (registry.stat().st_dev, registry.stat().st_ino)
    source_observed = []
    acceptance_observed = []
    original_source = audit_subject.observe_run_bound_source_set
    original_acceptance = audit_subject.observe_staging_run_acceptance

    def source_read(root, *, expected_root_identity=None):
        source_observed.append(expected_root_identity)
        return original_source(root, expected_root_identity=expected_root_identity)

    def acceptance_read(root, run_id, *, expected_root_identity=None):
        acceptance_observed.append(expected_root_identity)
        return original_acceptance(root, run_id, expected_root_identity=expected_root_identity)

    monkeypatch.setattr(audit_subject, "observe_run_bound_source_set", source_read)
    monkeypatch.setattr(audit_subject, "observe_staging_run_acceptance", acceptance_read)
    monkeypatch.setattr(audit_subject, "_utc_now", lambda: NOW)
    audit_subject.verify_accepted_current(source, registry, expected_source_identity=source_identity, expected_acceptance_identity=acceptance_identity)
    assert source_observed == [source_identity, source_identity]
    assert acceptance_observed == [acceptance_identity, acceptance_identity]


@pytest.mark.parametrize("accepted_source", (False, True))
def test_operation_audit_passes_resolved_child_identities(tmp_path, monkeypatch, accepted_source):
    root = operation_root(tmp_path)
    expected = resolve_operation_root(root)
    observed = []

    def inspect(acceptance, *, expected_acceptance_identity=None):
        observed.append((None, expected_acceptance_identity))
        return ()

    def verify(source, acceptance, *, expected_source_identity=None, expected_acceptance_identity=None):
        observed.append((expected_source_identity, expected_acceptance_identity))

    monkeypatch.setattr(operation_subject, "inspect_registry", inspect)
    monkeypatch.setattr(operation_subject, "verify_accepted_current", verify)
    source_identity = expected.source_identity if accepted_source else None
    expected_read = (source_identity, expected.acceptance_identity)
    if accepted_source:
        with pytest.raises(ManifestHandoffRegistryUnavailable):
            operation_subject.audit(root, accepted_source=True)
        assert observed == [expected_read]
    else:
        operation_subject.audit(root, accepted_source=False)
        assert observed == [expected_read] * 3


@pytest.mark.parametrize("accepted_source,target", ((False, "acceptance"), (True, "source"), (True, "acceptance")))
def test_operation_audit_rejects_child_swap_before_inner_read(tmp_path, monkeypatch, accepted_source, target):
    root = operation_root(tmp_path)
    original = operation_subject.verify_accepted_current if accepted_source else operation_subject.inspect_registry

    def swapping(*args, **kwargs):
        path = root / ("source-set" if target == "source" else "accepted-runs")
        moved = root / ("old-source-set" if target == "source" else "old-accepted-runs")
        path.rename(moved)
        shutil.copytree(moved, path)
        path.chmod(0o700)
        for child in path.iterdir():
            child.chmod(0o600)
        return original(*args, **kwargs)

    if accepted_source:
        monkeypatch.setattr(operation_subject, "verify_accepted_current", swapping)
    else:
        monkeypatch.setattr(operation_subject, "inspect_registry", swapping)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        operation_subject.audit(root, accepted_source=accepted_source)


def test_unbound_standalone_audit_reads_remain_supported(tmp_path):
    _, registry = roots(tmp_path)
    assert registry_subject.load_staging_run_acceptance(registry, RUN) is None
    assert audit_subject.inspect_registry(registry) == ()
