import math
import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_acceptance_audit as audit_subject
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject

@pytest.mark.parametrize("value",(None,0,True,-1.0,math.inf,-math.inf,math.nan))
def test_monotonic_validator_rejects_noncanonical_values(value):
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject._validate_monotonic(value)

def test_monotonic_validator_accepts_exact_nonnegative_float():
    assert subject._validate_monotonic(0.0)==0.0

def _clock(invalid_call=None):
    calls=[]
    def read():
        calls.append(len(calls)+1)
        return None if len(calls)==invalid_call else float(len(calls))
    return read,calls

@pytest.mark.parametrize("call",(1,2,3))
def test_accept_validates_every_outer_monotonic_read(tmp_path,monkeypatch,call):
    root=operation_root(tmp_path);clock,calls=_clock(call);monkeypatch.setattr(subject,"_monotonic_now",clock);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.accept_once(root)
    assert calls==list(range(1,call+1))

@pytest.mark.parametrize("accepted",(False,True))
@pytest.mark.parametrize("call",(1,2,3))
def test_audit_validates_every_outer_monotonic_read(tmp_path,monkeypatch,accepted,call):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root);monkeypatch.setattr(audit_subject,"_utc_now",lambda:NOW);clock,calls=_clock(call);monkeypatch.setattr(subject,"_monotonic_now",clock)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.audit(root,accepted_source=accepted)
    assert calls==list(range(1,call+1))

@pytest.mark.parametrize("accepted",(False,True))
def test_audit_uses_three_validated_outer_monotonic_reads(tmp_path,monkeypatch,accepted):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root);monkeypatch.setattr(audit_subject,"_utc_now",lambda:NOW);clock,calls=_clock();monkeypatch.setattr(subject,"_monotonic_now",clock);subject.audit(root,accepted_source=accepted)
    assert calls==[1,2,3]
