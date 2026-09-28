from pathlib import Path
import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject

@pytest.mark.parametrize("value",("/tmp/cafe\u0301","/tmp/a\u200bb","/tmp/a\nb","/tmp/"+"a"*256))
def test_direct_root_rejects_invalid_rendered_text(value):
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject._validate_direct_root(Path(value))

@pytest.mark.parametrize("api",("accept","registry-audit","accepted-audit"))
@pytest.mark.parametrize("value",("/tmp/cafe\u0301","/tmp/a\u200bb","/tmp/"+"a"*256))
def test_invalid_direct_root_text_stops_before_clock_or_resolution(monkeypatch,api,value):
    def unexpected(*args,**kwargs): pytest.fail("invalid direct root text crossed preflight")
    monkeypatch.setattr(subject,"_accept_utc_now",unexpected);monkeypatch.setattr(subject,"_audit_utc_now",unexpected);monkeypatch.setattr(subject,"_outer_monotonic_now",unexpected);monkeypatch.setattr(subject,"resolve_operation_root",unexpected)
    root=Path(value);call=(lambda:subject.accept_once(root)) if api=="accept" else (lambda:subject.audit(root,accepted_source=api=="accepted-audit"))
    with pytest.raises(ManifestHandoffRegistryUnavailable): call()

def test_shared_root_text_returns_canonical_text():
    value="/tmp/caf\u00e9";assert subject._validate_root_text(value) is value

def test_valid_direct_root_remains_accepted(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW)
    assert subject.accept_once(root) is None and subject.audit(root,accepted_source=False) is None
