from datetime import datetime,timedelta,timezone
import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_acceptance_audit as audit_subject
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject

@pytest.mark.parametrize("value",(None,0,datetime.now(),datetime.now(timezone(timedelta(hours=1)))))
def test_utc_validator_rejects_noncanonical_values(value):
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject._validate_utc(value)

def test_utc_validator_accepts_exact_utc_datetime():
    assert subject._validate_utc(NOW) is NOW

def test_accept_uses_three_validated_utc_reads(tmp_path,monkeypatch):
    root=operation_root(tmp_path);seen=[];original=subject._accept_utc_now
    def read(): value=original();seen.append(value);return value
    monkeypatch.setattr(subject,"_accept_utc_now",read);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root)
    assert seen==[NOW,NOW,NOW]

@pytest.mark.parametrize("call",(1,2,3))
def test_accept_rejects_malformed_utc_at_every_stage(tmp_path,monkeypatch,call):
    root=operation_root(tmp_path);calls=0
    def read():
        nonlocal calls
        calls+=1
        return None if calls==call else NOW
    monkeypatch.setattr(subject,"_accept_utc_now",lambda:subject._validate_utc(read()));monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.accept_once(root)
    assert len(tuple((root/"accepted-runs").iterdir()))==(0 if call==1 else 1)

def test_accepted_audit_uses_two_validated_utc_reads(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);subject.accept_once(root);monkeypatch.setattr(audit_subject,"_utc_now",lambda:NOW);seen=[];original=subject._audit_utc_now
    def read(): value=original();seen.append(value);return value
    monkeypatch.setattr(subject,"_audit_utc_now",read);subject.audit(root,accepted_source=True)
    assert seen==[NOW,NOW]

def test_registry_audit_performs_no_utc_read(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(subject,"_audit_utc_now",lambda:pytest.fail("unexpected UTC read"));subject.audit(root,accepted_source=False)
