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

def test_source_change_during_outer_accepted_verification_is_rejected(tmp_path,monkeypatch):
    root=_accepted(tmp_path,monkeypatch);target=root/"source-set"/"render";original=subject.verify_run_bound_snapshot
    def changing(*args,**kwargs):
        result=original(*args,**kwargs);content=target.read_bytes();target.write_bytes(bytes((value+1)%256 for value in content));target.chmod(0o600);return result
    monkeypatch.setattr(subject,"verify_run_bound_snapshot",changing)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.audit(root,accepted_source=True)

def test_marker_change_during_outer_accepted_verification_is_rejected(tmp_path,monkeypatch):
    root=_accepted(tmp_path,monkeypatch);registry=root/"accepted-runs";original=subject.verify_run_bound_snapshot
    def replacing(*args,**kwargs):
        result=original(*args,**kwargs);marker=next(registry.iterdir());content=marker.read_bytes();marker.unlink();marker.write_bytes(content);marker.chmod(0o600);return result
    monkeypatch.setattr(subject,"verify_run_bound_snapshot",replacing)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.audit(root,accepted_source=True)

def test_terminal_accepted_rechecks_are_included_in_duration(tmp_path,monkeypatch):
    root=_accepted(tmp_path,monkeypatch);clock,calls=_values((100.0,129.0,130.000001));monkeypatch.setattr(subject,"_monotonic_now",clock)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.audit(root,accepted_source=True)
    assert calls==[100.0,129.0,130.000001]

def test_stable_terminal_accepted_audit_completes(tmp_path,monkeypatch):
    root=_accepted(tmp_path,monkeypatch);clock,_=_values((100.0,101.0,102.0));monkeypatch.setattr(subject,"_monotonic_now",clock);subject.audit(root,accepted_source=True)
