from datetime import timedelta
import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject

def _values(values):
    iterator=iter(values);calls=[]
    def read(): value=next(iterator);calls.append(value);return value
    return read,calls

def test_operation_decision_uses_outer_monotonic_window(tmp_path,monkeypatch):
    root=operation_root(tmp_path);clock,calls=_values((100.0,129.0,129.5));monkeypatch.setattr(subject,"_monotonic_now",clock);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root)
    assert calls==[100.0,129.0,129.5]

@pytest.mark.parametrize("values",((100.0,130.000001),(100.0,99.0)))
def test_operation_decision_rejects_invalid_outer_duration(tmp_path,monkeypatch,values):
    root=operation_root(tmp_path);clock,_=_values(values);monkeypatch.setattr(subject,"_monotonic_now",clock);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.accept_once(root)

def test_operation_revalidates_retained_source_at_final_time(tmp_path,monkeypatch):
    root=operation_root(tmp_path);times,_=_values((NOW,NOW,NOW,NOW,NOW+timedelta(hours=2)));clock,_=_values((100.0,101.0));monkeypatch.setattr(accept_subject,"_utc_now",times);monkeypatch.setattr(subject,"_monotonic_now",clock)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.accept_once(root)

def test_stable_outer_time_and_freshness_complete(tmp_path,monkeypatch):
    root=operation_root(tmp_path);clock,_=_values((100.0,101.0,102.0));monkeypatch.setattr(subject,"_monotonic_now",clock);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root)
    assert len(tuple((root/"accepted-runs").iterdir()))==1
