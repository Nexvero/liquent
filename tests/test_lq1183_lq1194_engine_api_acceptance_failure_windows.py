import os
import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport import manifest_handoff_supervisor_engine_api_staging_acceptance as subject
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_acceptance import build_staging_run_acceptance,load_staging_run_acceptance,record_staging_run_acceptance
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_run import decode_staging_run_authority
from tools import engine_api_joint_staging_one_shot_verify as command
from tools.engine_api_joint_staging_source_set import load_run_bound_source_set
from tests.test_lq1135_lq1146_engine_api_run_acceptance import roots
from tests.test_lq1123_lq1134_engine_api_run_bound_root import RUN
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW

def prepared(tmp_path):
    source,root=roots(tmp_path);snapshot=load_run_bound_source_set(source);value=build_staging_run_acceptance(decode_staging_run_authority(snapshot.run_authority),snapshot.run_envelope);return source,root,value

@pytest.mark.parametrize("failure",("write","file-fsync"))
def test_pre_durable_failure_removes_new_marker(tmp_path,monkeypatch,failure):
    _,root,value=prepared(tmp_path)
    if failure=="write": monkeypatch.setattr(subject.os,"write",lambda *_:(_ for _ in ()).throw(OSError("write")))
    else:
        original=subject.os.fsync;calls=[]
        def failed(descriptor): calls.append(descriptor);raise OSError("fsync")
        monkeypatch.setattr(subject.os,"fsync",failed)
    with pytest.raises(ManifestHandoffRegistryUnavailable): record_staging_run_acceptance(root,value)
    assert list(root.iterdir())==[]

def test_directory_fsync_failure_preserves_durable_marker(tmp_path,monkeypatch):
    _,root,value=prepared(tmp_path);original=subject.os.fsync;calls=0
    def failed_second(descriptor):
        nonlocal calls
        calls+=1
        if calls==2: raise OSError("directory fsync")
        return original(descriptor)
    monkeypatch.setattr(subject.os,"fsync",failed_second)
    with pytest.raises(ManifestHandoffRegistryUnavailable): record_staging_run_acceptance(root,value)
    assert load_staging_run_acceptance(root,RUN)==value

def test_retry_after_pre_durable_failure_can_succeed(tmp_path,monkeypatch):
    _,root,value=prepared(tmp_path);original=subject.os.write;monkeypatch.setattr(subject.os,"write",lambda *_:(_ for _ in ()).throw(OSError("write")))
    with pytest.raises(ManifestHandoffRegistryUnavailable): record_staging_run_acceptance(root,value)
    monkeypatch.setattr(subject.os,"write",original);record_staging_run_acceptance(root,value);assert load_staging_run_acceptance(root,RUN)==value

def test_retry_after_uncertain_outcome_is_stopped_by_precheck(tmp_path,monkeypatch):
    source,root,_=prepared(tmp_path);original=subject.os.fsync;calls=0
    def failed_second(descriptor):
        nonlocal calls
        calls+=1
        if calls==2: raise OSError("directory fsync")
        return original(descriptor)
    monkeypatch.setattr(subject.os,"fsync",failed_second);monkeypatch.setattr(command,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): command.verify_and_accept(source,root)
    monkeypatch.setattr(subject.os,"fsync",original)
    with pytest.raises(ManifestHandoffRegistryUnavailable): command.verify_and_accept(source,root)

def test_existing_marker_is_never_removed_on_rejected_retry(tmp_path):
    _,root,value=prepared(tmp_path);record_staging_run_acceptance(root,value);before=(root/(RUN+".accepted")).read_bytes()
    with pytest.raises(ManifestHandoffRegistryUnavailable): record_staging_run_acceptance(root,value)
    assert (root/(RUN+".accepted")).read_bytes()==before
