from datetime import timedelta
import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_acceptance_audit as audit_subject
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject

def _values(values):
    iterator=iter(values);calls=[]
    def read(): value=next(iterator);calls.append(value);return value
    return read,calls

def _accepted(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root);monkeypatch.setattr(audit_subject,"_utc_now",lambda:NOW);return root

def test_registry_audit_outer_duration_includes_rechecks(tmp_path,monkeypatch):
    root=operation_root(tmp_path);clock,calls=_values((100.0,129.0,130.0));monkeypatch.setattr(subject,"_monotonic_now",clock);subject.audit(root,accepted_source=False)
    assert calls==[100.0,129.0,130.0]

def test_registry_audit_rejects_outer_duration_overrun(tmp_path,monkeypatch):
    root=operation_root(tmp_path);clock,_=_values((100.0,130.000001));monkeypatch.setattr(subject,"_monotonic_now",clock)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.audit(root,accepted_source=False)

def test_accepted_audit_revalidates_retained_source_at_outer_final_time(tmp_path,monkeypatch):
    root=_accepted(tmp_path,monkeypatch);times,_=_values((NOW,NOW,NOW,NOW+timedelta(hours=2)));clock,_=_values((100.0,101.0));monkeypatch.setattr(audit_subject,"_utc_now",times);monkeypatch.setattr(subject,"_monotonic_now",clock)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.audit(root,accepted_source=True)

def test_stable_outer_audit_time_completes_both_modes(tmp_path,monkeypatch):
    root=_accepted(tmp_path,monkeypatch)
    for accepted in (False,True):
        clock,_=_values((100.0,101.0,102.0));monkeypatch.setattr(subject,"_monotonic_now",clock);subject.audit(root,accepted_source=accepted)
