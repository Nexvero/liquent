import argparse
from pathlib import Path
import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tools import engine_api_joint_staging_operation_verify as subject

@pytest.mark.parametrize("value",(None,object(),argparse.Namespace(),argparse.Namespace(operation_root=Path("/root")),argparse.Namespace(mode="audit-registry"),argparse.Namespace(operation_root=Path("/root"),mode="audit-registry",extra=True),argparse.Namespace(operation_root="/root",mode="audit-registry"),argparse.Namespace(operation_root=Path("/root"),mode=False),argparse.Namespace(operation_root=Path("/root"),mode="unknown")))
def test_cli_namespace_validator_rejects_malformed_handoff(value):
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject._validate_cli_namespace(value)

@pytest.mark.parametrize("mode",("accept-once","audit-registry","audit-accepted-source"))
def test_cli_namespace_validator_returns_exact_fields(mode):
    root=Path("/root");assert subject._validate_cli_namespace(argparse.Namespace(operation_root=root,mode=mode))==(root,mode)

@pytest.mark.parametrize("value",(argparse.Namespace(),argparse.Namespace(operation_root=Path("/root"),mode="unknown"),argparse.Namespace(operation_root=Path("/root"),mode="audit-registry",extra=True)))
def test_main_rejects_malformed_parser_handoff_before_dispatch(monkeypatch,value,capsys):
    monkeypatch.setattr(subject._DetailFreeArgumentParser,"parse_args",lambda self,argv:value);monkeypatch.setattr(subject,"_dispatch_cli",lambda *args:pytest.fail("unexpected dispatch"))
    assert subject.main([])==2
    captured=capsys.readouterr();assert captured.out==captured.err==""

@pytest.mark.parametrize("value",(False,0,(),object()))
def test_main_rejects_foreign_dispatch_completion(monkeypatch,value,capsys):
    monkeypatch.setattr(subject,"_dispatch_cli",lambda root,mode:value)
    assert subject.main(["--operation-root","/root","--mode","audit-registry"])==2
    captured=capsys.readouterr();assert captured.out==captured.err==""

def test_main_accepts_exact_dispatch_none(monkeypatch,capsys):
    calls=[];monkeypatch.setattr(subject,"_dispatch_cli",lambda root,mode:calls.append((root,mode)))
    assert subject.main(["--operation-root","/root","--mode","audit-registry"])==0 and calls==[(Path("/root"),"audit-registry")]
    captured=capsys.readouterr();assert captured.out==captured.err==""
