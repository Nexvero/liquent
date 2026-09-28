from pathlib import Path
import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject

@pytest.mark.parametrize("value",(Path("//"),Path("//tmp"),Path("//tmp/root")))
def test_direct_root_rejects_double_slash_anchor(value):
    assert value.anchor=="//"
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject._validate_direct_root(value)

@pytest.mark.parametrize("api",("accept","registry-audit","accepted-audit"))
def test_double_slash_root_stops_before_clock_or_resolution(monkeypatch,api):
    def unexpected(*args,**kwargs): pytest.fail("alias crossed root preflight")
    monkeypatch.setattr(subject,"_accept_utc_now",unexpected);monkeypatch.setattr(subject,"_audit_utc_now",unexpected);monkeypatch.setattr(subject,"_outer_monotonic_now",unexpected);monkeypatch.setattr(subject,"resolve_operation_root",unexpected)
    call=(lambda:subject.accept_once(Path("//tmp/root"))) if api=="accept" else (lambda:subject.audit(Path("//tmp/root"),accepted_source=api=="accepted-audit"))
    with pytest.raises(ManifestHandoffRegistryUnavailable): call()

def test_single_slash_absolute_root_shape_remains_valid(tmp_path):
    root=tmp_path.resolve();assert root.anchor=="/" and subject._validate_direct_root(root) is root

def test_valid_single_anchor_operation_remains_unchanged(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW)
    assert subject.accept_once(root) is None and subject.audit(root,accepted_source=False) is None
