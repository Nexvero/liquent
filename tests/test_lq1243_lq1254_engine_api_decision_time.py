from datetime import timedelta
import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tools import engine_api_joint_staging_acceptance_audit as audit_subject
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tests.test_lq1135_lq1146_engine_api_run_acceptance import roots
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW

def clock(values):
    iterator=iter(values);calls=[]
    def read(): value=next(iterator);calls.append(value);return value
    return read,calls

def test_acceptance_reads_initial_and_final_utc(tmp_path,monkeypatch):
    source,root=roots(tmp_path);read,calls=clock((NOW,NOW+timedelta(seconds=30)));monkeypatch.setattr(accept_subject,"_utc_now",read);accept_subject.verify_and_accept(source,root);assert calls==[NOW,NOW+timedelta(seconds=30)]

@pytest.mark.parametrize("outcome",("expired","rollback","clock-failure"))
def test_acceptance_final_time_failure_preserves_marker(tmp_path,monkeypatch,outcome):
    source,root=roots(tmp_path)
    if outcome=="expired": values=(NOW,NOW+timedelta(minutes=31))
    elif outcome=="rollback": values=(NOW,NOW-timedelta(seconds=1))
    else: values=(NOW,)
    read,_=clock(values);monkeypatch.setattr(accept_subject,"_utc_now",read)
    with pytest.raises((ManifestHandoffRegistryUnavailable,StopIteration)): accept_subject.verify_and_accept(source,root)
    assert len(list(root.iterdir()))==1

def accepted(tmp_path,monkeypatch):
    source,root=roots(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);accept_subject.verify_and_accept(source,root);return source,root

def test_audit_reads_initial_and_final_utc(tmp_path,monkeypatch):
    source,root=accepted(tmp_path,monkeypatch);read,calls=clock((NOW,NOW+timedelta(seconds=30)));monkeypatch.setattr(audit_subject,"_utc_now",read);audit_subject.verify_accepted_current(source,root);assert calls==[NOW,NOW+timedelta(seconds=30)]

@pytest.mark.parametrize("outcome",("expired","rollback","clock-failure"))
def test_audit_rejects_invalid_final_time(tmp_path,monkeypatch,outcome):
    source,root=accepted(tmp_path,monkeypatch)
    if outcome=="expired": values=(NOW,NOW+timedelta(minutes=31))
    elif outcome=="rollback": values=(NOW,NOW-timedelta(seconds=1))
    else: values=(NOW,)
    read,_=clock(values);monkeypatch.setattr(audit_subject,"_utc_now",read)
    with pytest.raises((ManifestHandoffRegistryUnavailable,StopIteration)): audit_subject.verify_accepted_current(source,root)

def test_final_verification_reuses_exact_initial_snapshot(tmp_path,monkeypatch):
    source,root=roots(tmp_path);snapshots=[];original=accept_subject.verify_run_bound_snapshot
    def observed(snapshot,**kwargs): snapshots.append(snapshot);return original(snapshot,**kwargs)
    monkeypatch.setattr(accept_subject,"verify_run_bound_snapshot",observed);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);accept_subject.verify_and_accept(source,root);assert len(snapshots)==2 and snapshots[0] is snapshots[1]
