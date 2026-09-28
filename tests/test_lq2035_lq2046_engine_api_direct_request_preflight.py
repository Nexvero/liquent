from pathlib import Path
import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject

@pytest.mark.parametrize("root",(None,"/tmp/root",Path("relative"),Path("/"),Path("/tmp/../root")))
def test_direct_root_validator_rejects_noncanonical_root(root):
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject._validate_direct_root(root)

def test_direct_root_validator_returns_canonical_path(tmp_path):
    root=tmp_path.resolve();assert subject._validate_direct_root(root) is root

@pytest.mark.parametrize("api",("accept","registry-audit","accepted-audit"))
def test_invalid_root_fails_before_clock_or_resolution(monkeypatch,api):
    def unexpected(*args,**kwargs): pytest.fail("request crossed preflight")
    monkeypatch.setattr(subject,"_accept_utc_now",unexpected);monkeypatch.setattr(subject,"_audit_utc_now",unexpected);monkeypatch.setattr(subject,"_outer_monotonic_now",unexpected);monkeypatch.setattr(subject,"resolve_operation_root",unexpected)
    call=(lambda:subject.accept_once(Path("relative"))) if api=="accept" else (lambda:subject.audit(Path("relative"),accepted_source=api=="accepted-audit"))
    with pytest.raises(ManifestHandoffRegistryUnavailable): call()

@pytest.mark.parametrize("mode",(None,0,1,"",object()))
def test_invalid_audit_mode_fails_before_root_or_clock(monkeypatch,mode):
    def unexpected(*args,**kwargs): pytest.fail("mode crossed preflight")
    monkeypatch.setattr(subject,"_validate_direct_root",unexpected);monkeypatch.setattr(subject,"_audit_utc_now",unexpected);monkeypatch.setattr(subject,"_outer_monotonic_now",unexpected)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.audit(Path("/unused"),accepted_source=mode)

def test_valid_request_preflight_preserves_operations(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW)
    assert subject.accept_once(root) is None and subject.audit(root,accepted_source=False) is None
