import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tools import engine_api_joint_staging_acceptance_audit as audit_subject
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject

def _raises(error):
    def read(): raise error
    return read

@pytest.mark.parametrize("reader",("accept","audit","monotonic"))
def test_clock_reader_normalizes_ordinary_provider_failure(monkeypatch,reader):
    if reader=="accept": monkeypatch.setattr(accept_subject,"_utc_now",_raises(ValueError("secret")));call=subject._accept_utc_now
    elif reader=="audit": monkeypatch.setattr(audit_subject,"_utc_now",_raises(OSError("secret")));call=subject._audit_utc_now
    else: monkeypatch.setattr(subject,"_monotonic_now",_raises(RuntimeError("secret")));call=subject._outer_monotonic_now
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught: call()
    assert caught.value.__cause__ is None and caught.value.__context__ is not None

@pytest.mark.parametrize("reader",("accept","audit","monotonic"))
def test_clock_reader_preserves_unavailable_failure(monkeypatch,reader):
    error=ManifestHandoffRegistryUnavailable()
    if reader=="accept": monkeypatch.setattr(accept_subject,"_utc_now",_raises(error));call=subject._accept_utc_now
    elif reader=="audit": monkeypatch.setattr(audit_subject,"_utc_now",_raises(error));call=subject._audit_utc_now
    else: monkeypatch.setattr(subject,"_monotonic_now",_raises(error));call=subject._outer_monotonic_now
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught: call()
    assert caught.value is error

@pytest.mark.parametrize("error",(KeyboardInterrupt(),SystemExit()))
def test_clock_reader_does_not_swallow_system_exit(error):
    with pytest.raises(type(error)) as caught: subject._read_validated_clock(_raises(error),lambda value:value)
    assert caught.value is error

def test_clock_reader_returns_validated_values(monkeypatch):
    monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);monkeypatch.setattr(audit_subject,"_utc_now",lambda:NOW);monkeypatch.setattr(subject,"_monotonic_now",lambda:1.0)
    assert subject._accept_utc_now() is NOW and subject._audit_utc_now() is NOW and subject._outer_monotonic_now()==1.0
