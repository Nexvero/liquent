from pathlib import Path
import pytest
from tools import engine_api_joint_staging_operation_verify as subject

@pytest.mark.parametrize("argv",(("--operation-r","/root","--mode","audit-registry"),("--operation-root","/root","--m","audit-registry"),("--oper","/root","--mode","audit-registry")))
def test_cli_rejects_option_abbreviations_before_dispatch(monkeypatch,argv,capsys):
    monkeypatch.setattr(subject,"_dispatch_cli",lambda *args:pytest.fail("abbreviation reached dispatch"))
    assert subject.main(list(argv))==2
    captured=capsys.readouterr();assert captured.out==captured.err==""

@pytest.mark.parametrize("argv",(("--operation-root","/a","--operation-root","/b","--mode","audit-registry"),("--operation-root","/a","--operation-root","/a","--mode","audit-registry"),("--operation-root","/a","--mode","accept-once","--mode","audit-registry"),("--operation-root","/a","--mode","audit-registry","--mode","audit-registry")))
def test_cli_rejects_duplicate_options_before_dispatch(monkeypatch,argv,capsys):
    monkeypatch.setattr(subject,"_dispatch_cli",lambda *args:pytest.fail("duplicate reached dispatch"))
    assert subject.main(list(argv))==2
    captured=capsys.readouterr();assert captured.out==captured.err==""

@pytest.mark.parametrize("argv",(("--operation-root","/root","--mode","audit-registry"),("--mode","audit-registry","--operation-root","/root")))
def test_cli_accepts_each_exact_option_once_in_any_order(monkeypatch,argv,capsys):
    calls=[];monkeypatch.setattr(subject,"_dispatch_cli",lambda root,mode:calls.append((root,mode)))
    assert subject.main(list(argv))==0 and calls==[(Path("/root"),"audit-registry")]
    captured=capsys.readouterr();assert captured.out==captured.err==""

def test_single_value_action_rejects_second_value():
    parser=subject._DetailFreeArgumentParser(add_help=False,allow_abbrev=False);parser.add_argument("--value",required=True,action=subject._SingleValueAction)
    assert parser.parse_args(["--value","one"]).value=="one"
    with pytest.raises(Exception): parser.parse_args(["--value","one","--value","two"])
