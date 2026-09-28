import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1123_lq1134_engine_api_run_bound_root import run_root
from tests.test_lq1135_lq1146_engine_api_run_acceptance import roots
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_source_set as source_subject


def test_source_observation_reads_each_child_twice(tmp_path, monkeypatch):
    root = run_root(tmp_path);calls=[];original=source_subject.os.open
    def opening(path,*args,**kwargs):
        if isinstance(path,str) and path in ("run-authority","render","shutdown"): calls.append(path)
        return original(path,*args,**kwargs)
    monkeypatch.setattr(source_subject.os,"open",opening);source_subject.observe_run_bound_source_set(root)
    assert calls.count("run-authority")==2 and calls.count("render")==2 and calls.count("shutdown")==2


def test_source_observation_rejects_content_change_between_passes(tmp_path, monkeypatch):
    root=run_root(tmp_path);target=root/"render";original=source_subject._children
    def changing(directory,names,limits):
        values=original(directory,names,limits);target.write_bytes(b"changed");target.chmod(0o600);return values
    monkeypatch.setattr(source_subject,"_children",changing)
    with pytest.raises(ManifestHandoffRegistryUnavailable): source_subject.observe_run_bound_source_set(root)


def test_source_observation_rejects_mode_change_between_passes(tmp_path, monkeypatch):
    root=run_root(tmp_path);target=root/"render";original=source_subject._children
    def changing(directory,names,limits):
        values=original(directory,names,limits);target.chmod(0o640);return values
    monkeypatch.setattr(source_subject,"_children",changing)
    with pytest.raises(ManifestHandoffRegistryUnavailable): source_subject.observe_run_bound_source_set(root)


def test_one_shot_rejects_source_change_during_initial_observation(tmp_path, monkeypatch):
    source,registry=roots(tmp_path);target=source/"render";original=source_subject._children
    def changing(directory,names,limits):
        values=original(directory,names,limits);target.write_bytes(b"changed");target.chmod(0o600);return values
    monkeypatch.setattr(source_subject,"_children",changing);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): accept_subject.verify_and_accept(source,registry)
    assert list(registry.iterdir())==[]


def test_stable_two_pass_source_observation_remains_supported(tmp_path):
    root=run_root(tmp_path);assert source_subject.observe_run_bound_source_set(root).snapshot==source_subject.load_run_bound_source_set(root)
