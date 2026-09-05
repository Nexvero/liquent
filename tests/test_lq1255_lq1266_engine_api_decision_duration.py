import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tools import engine_api_joint_staging_acceptance_audit as audit_subject
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_policy_verify as clock_subject
from tests.test_lq1135_lq1146_engine_api_run_acceptance import roots
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW

def monotonic(values):
    iterator=iter(values);calls=[]
    def read(): value=next(iterator);calls.append(value);return value
    return read,calls

def test_internal_monotonic_source_is_finite_nonnegative():
    assert clock_subject._monotonic_now()>=0

def test_acceptance_reads_two_monotonic_values(tmp_path,monkeypatch):
    source,root=roots(tmp_path);read,calls=monotonic((100.0,129.0));monkeypatch.setattr(accept_subject,"_monotonic_now",read);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);accept_subject.verify_and_accept(source,root);assert calls==[100.0,129.0]

@pytest.mark.parametrize("values",((100.0,130.000001),(100.0,99.0)))
def test_acceptance_duration_or_monotonic_rollback_preserves_marker(tmp_path,monkeypatch,values):
    source,root=roots(tmp_path);read,_=monotonic(values);monkeypatch.setattr(accept_subject,"_monotonic_now",read);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): accept_subject.verify_and_accept(source,root)
    assert len(list(root.iterdir()))==1

def accepted(tmp_path,monkeypatch):
    source,root=roots(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);accept_subject.verify_and_accept(source,root);return source,root

def test_audit_reads_two_monotonic_values(tmp_path,monkeypatch):
    source,root=accepted(tmp_path,monkeypatch);read,calls=monotonic((200.0,230.0));monkeypatch.setattr(audit_subject,"_monotonic_now",read);monkeypatch.setattr(audit_subject,"_utc_now",lambda:NOW);audit_subject.verify_accepted_current(source,root);assert calls==[200.0,230.0]

@pytest.mark.parametrize("values",((200.0,230.000001),(200.0,199.0)))
def test_audit_rejects_excess_duration_or_monotonic_rollback(tmp_path,monkeypatch,values):
    source,root=accepted(tmp_path,monkeypatch);read,_=monotonic(values);monkeypatch.setattr(audit_subject,"_monotonic_now",read);monkeypatch.setattr(audit_subject,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): audit_subject.verify_accepted_current(source,root)

def test_exact_thirty_second_boundary_is_allowed(tmp_path,monkeypatch):
    source,root=roots(tmp_path);read,_=monotonic((1.0,31.0));monkeypatch.setattr(accept_subject,"_monotonic_now",read);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);accept_subject.verify_and_accept(source,root)
