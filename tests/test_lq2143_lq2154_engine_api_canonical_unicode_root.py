from pathlib import Path
import unicodedata
import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tools import engine_api_joint_staging_operation_verify as subject

@pytest.mark.parametrize("character",("\u0085","\u200b","\u200e","\u202e","\u2066","\ufeff"))
def test_raw_cli_root_rejects_unicode_control_and_format(character):
    assert unicodedata.category(character) in ("Cc","Cf")
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject._parse_cli_root(f"/tmp/a{character}b")

def test_raw_cli_root_rejects_decomposed_unicode():
    value="/tmp/cafe\u0301";assert unicodedata.normalize("NFC",value)!=value
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject._parse_cli_root(value)

def test_raw_cli_root_accepts_same_visible_text_in_nfc():
    value="/tmp/caf\u00e9";assert unicodedata.normalize("NFC",value)==value and subject._parse_cli_root(value)==Path(value)

@pytest.mark.parametrize("root",("/tmp/cafe\u0301","/tmp/a\u200bb","/tmp/a\u202eb"))
def test_noncanonical_unicode_stops_before_dispatch(monkeypatch,root,capsys):
    monkeypatch.setattr(subject,"_dispatch_cli",lambda *args:pytest.fail("noncanonical Unicode reached dispatch"))
    assert subject.main(["--operation-root",root,"--mode","audit-registry"])==2
    captured=capsys.readouterr();assert captured.out==captured.err==""

def test_canonical_unicode_reaches_dispatch(monkeypatch,capsys):
    calls=[];root="/tmp/caf\u00e9";monkeypatch.setattr(subject,"_dispatch_cli",lambda value,mode:calls.append((value,mode)))
    assert subject.main(["--operation-root",root,"--mode","audit-registry"])==0 and calls==[(Path(root),"audit-registry")]
    captured=capsys.readouterr();assert captured.out==captured.err==""
