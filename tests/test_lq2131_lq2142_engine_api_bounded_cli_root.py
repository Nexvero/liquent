from pathlib import Path
import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tools import engine_api_joint_staging_operation_verify as subject

@pytest.mark.parametrize("character",("\0","\t","\n","\r",chr(31),chr(127)))
def test_raw_cli_root_rejects_ascii_control_characters(character):
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject._parse_cli_root(f"/tmp/a{character}b")

def test_raw_cli_root_rejects_non_utf8_surrogate():
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject._parse_cli_root("/tmp/\ud800")

def test_raw_cli_root_rejects_oversized_component():
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject._parse_cli_root("/tmp/"+"a"*256)

def test_raw_cli_root_rejects_oversized_total_path():
    value="/"+"/".join("a"*255 for _ in range(16))
    assert len(value.encode())>subject._MAX_CLI_ROOT_BYTES
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject._parse_cli_root(value)

def test_raw_cli_root_accepts_exact_component_byte_limit():
    value="/tmp/"+"a"*255;assert subject._parse_cli_root(value)==Path(value)

def test_raw_cli_root_accepts_utf8_component_within_byte_limit():
    value="/tmp/"+"ä"*127;assert len(value.rsplit("/",1)[1].encode())==254 and subject._parse_cli_root(value)==Path(value)

@pytest.mark.parametrize("root",("/tmp/a\nvalue","/tmp/"+"a"*256,"/tmp/\ud800"))
def test_bounded_root_rejection_stops_before_dispatch(monkeypatch,root,capsys):
    monkeypatch.setattr(subject,"_dispatch_cli",lambda *args:pytest.fail("invalid bounded root reached dispatch"))
    assert subject.main(["--operation-root",root,"--mode","audit-registry"])==2
    captured=capsys.readouterr();assert captured.out==captured.err==""
