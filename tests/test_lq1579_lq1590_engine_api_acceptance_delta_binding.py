import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1123_lq1134_engine_api_run_bound_root import RUN
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as operation_subject

def test_operation_accept_inspects_registry_before_and_after(tmp_path,monkeypatch):
    root=operation_root(tmp_path);calls=[];original=operation_subject.observe_registry
    def observed(path,**kwargs): calls.append((path,kwargs));return original(path,**kwargs)
    monkeypatch.setattr(operation_subject,"observe_registry",observed);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);operation_subject.accept_once(root)
    assert len(calls)==4 and calls[0][1]==calls[1][1]==calls[2][1]==calls[3][1]

def test_operation_accept_rejects_unrelated_registry_file(tmp_path,monkeypatch):
    root=operation_root(tmp_path);registry=root/"accepted-runs";original=operation_subject.verify_and_accept
    def adding(source,acceptance,**kwargs):
        original(source,acceptance,**kwargs);extra=registry/"unexpected";extra.write_bytes(b"x");extra.chmod(0o600)
    monkeypatch.setattr(operation_subject,"verify_and_accept",adding);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): operation_subject.accept_once(root)

def test_operation_accept_rejects_missing_single_marker_delta(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(operation_subject,"verify_and_accept",lambda *args,**kwargs:None)
    with pytest.raises(ManifestHandoffRegistryUnavailable): operation_subject.accept_once(root)

def test_operation_accept_allows_exact_single_canonical_marker_delta(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);operation_subject.accept_once(root)
    assert [path.name for path in (root/"accepted-runs").iterdir()]==[RUN+".accepted"]
