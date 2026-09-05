from pathlib import Path
import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tools import engine_api_joint_staging_operation_verify as subject

@pytest.mark.parametrize("value",(None,Path("/root"),"","root","/","//root","/tmp/root/","/tmp//root","/tmp/./root","/tmp/../root","/tmp/\0root"))
def test_raw_cli_root_rejects_noncanonical_spelling(value):
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject._parse_cli_root(value)

def test_raw_cli_root_returns_exact_native_path():
    value=subject._parse_cli_root("/tmp/root");assert value==Path("/tmp/root") and type(value)is subject._NATIVE_PATH_TYPE

@pytest.mark.parametrize("root",("//tmp/root","/tmp/root/","/tmp//root","/tmp/./root","/tmp/../root"))
def test_noncanonical_cli_root_stops_before_dispatch(monkeypatch,root,capsys):
    monkeypatch.setattr(subject,"_dispatch_cli",lambda *args:pytest.fail("noncanonical root reached dispatch"))
    assert subject.main(["--operation-root",root,"--mode","audit-registry"])==2
    captured=capsys.readouterr();assert captured.out==captured.err==""

@pytest.mark.parametrize("mode",("accept-once","audit-registry","audit-accepted-source"))
def test_canonical_cli_root_reaches_each_mode(monkeypatch,mode,capsys):
    calls=[];monkeypatch.setattr(subject,"_dispatch_cli",lambda root,value:calls.append((root,value)))
    assert subject.main(["--operation-root","/tmp/root","--mode",mode])==0 and calls==[(Path("/tmp/root"),mode)]
    captured=capsys.readouterr();assert captured.out==captured.err==""
