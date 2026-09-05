from pathlib import Path
import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tools import engine_api_joint_staging_operation_verify as subject

@pytest.mark.parametrize("mode,expected",(("accept-once",("accept",None)),("audit-registry",("audit",False)),("audit-accepted-source",("audit",True))))
def test_cli_dispatch_binds_each_mode_once(monkeypatch,mode,expected):
    calls=[];root=Path("/root")
    monkeypatch.setattr(subject,"accept_once",lambda value:calls.append(("accept",None)))
    monkeypatch.setattr(subject,"audit",lambda value,*,accepted_source:calls.append(("audit",accepted_source)))
    assert subject._dispatch_cli(root,mode) is None and calls==[expected]

@pytest.mark.parametrize("mode",(None,False,0,"","accept","AUDIT-REGISTRY",object()))
def test_cli_dispatch_rejects_invalid_mode_before_operation(monkeypatch,mode):
    monkeypatch.setattr(subject,"accept_once",lambda *args,**kwargs:pytest.fail("unexpected accept"));monkeypatch.setattr(subject,"audit",lambda *args,**kwargs:pytest.fail("unexpected audit"))
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject._dispatch_cli(Path("/root"),mode)

@pytest.mark.parametrize("mode",("accept-once","audit-registry","audit-accepted-source"))
@pytest.mark.parametrize("value",(False,0,(),object()))
def test_cli_dispatch_rejects_non_none_operation_completion(monkeypatch,mode,value):
    monkeypatch.setattr(subject,"accept_once",lambda root:value);monkeypatch.setattr(subject,"audit",lambda root,*,accepted_source:value)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject._dispatch_cli(Path("/root"),mode)

@pytest.mark.parametrize("mode",("accept-once","audit-registry","audit-accepted-source"))
def test_main_maps_foreign_completion_to_silent_status_two(tmp_path,monkeypatch,mode,capsys):
    monkeypatch.setattr(subject,"accept_once",lambda root:object());monkeypatch.setattr(subject,"audit",lambda root,*,accepted_source:object())
    assert subject.main(["--operation-root",str(tmp_path),"--mode",mode])==2
    captured=capsys.readouterr();assert captured.out==captured.err==""
