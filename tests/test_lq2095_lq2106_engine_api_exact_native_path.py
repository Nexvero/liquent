import argparse
from pathlib import Path
import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject

class DerivedPath(type(Path())): pass

def test_native_path_type_is_exact_platform_path():
    assert subject._NATIVE_PATH_TYPE is type(Path()) and type(Path("/root")) is subject._NATIVE_PATH_TYPE

def test_direct_root_rejects_path_subclass():
    value=DerivedPath("/tmp/root");assert isinstance(value,Path) and type(value)is not subject._NATIVE_PATH_TYPE
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject._validate_direct_root(value)

@pytest.mark.parametrize("api",("accept","registry-audit","accepted-audit"))
def test_path_subclass_stops_before_clock_or_resolution(monkeypatch,api):
    def unexpected(*args,**kwargs): pytest.fail("subclass crossed root type gate")
    monkeypatch.setattr(subject,"_accept_utc_now",unexpected);monkeypatch.setattr(subject,"_audit_utc_now",unexpected);monkeypatch.setattr(subject,"_outer_monotonic_now",unexpected);monkeypatch.setattr(subject,"resolve_operation_root",unexpected)
    root=DerivedPath("/tmp/root");call=(lambda:subject.accept_once(root)) if api=="accept" else (lambda:subject.audit(root,accepted_source=api=="accepted-audit"))
    with pytest.raises(ManifestHandoffRegistryUnavailable): call()

def test_cli_namespace_rejects_path_subclass():
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject._validate_cli_namespace(argparse.Namespace(operation_root=DerivedPath("/root"),mode="audit-registry"))

def test_native_path_requests_remain_accepted(tmp_path,monkeypatch):
    root=operation_root(tmp_path);assert type(root)is subject._NATIVE_PATH_TYPE;monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW)
    assert subject.accept_once(root) is None and subject.audit(root,accepted_source=False) is None
