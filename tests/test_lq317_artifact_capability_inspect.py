from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import liquent_platform.operators.artifact_capability_inspect as inspect


TOKEN = "a" * 64


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "artifacts"
    root.mkdir(mode=0o700)
    return root


def test_capability_sequence_succeeds_and_leaves_no_probe_object(tmp_path: Path) -> None:
    root = _root(tmp_path)
    assert inspect.inspect_artifact_capabilities(TOKEN, artifact_root=root) is True
    assert list(root.iterdir()) == []


def test_output_is_exact_neutral_fact(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(inspect, "inspect_artifact_capabilities", lambda token: token == TOKEN)
    assert inspect.inspect(TOKEN) == (
        b'{"facts":{"artifact_capabilities_valid":true},'
        b'"phase":"artifact_capabilities","schema_version":1}\n'
    )


def test_existing_prefix_stops_without_changing_it(tmp_path: Path) -> None:
    root = _root(tmp_path)
    prefix = root / f".liquent-staging-probe-{TOKEN}"
    prefix.mkdir()
    marker = prefix / "existing"
    marker.write_bytes(b"keep")
    with pytest.raises(inspect.ArtifactCapabilityInspectUnavailable):
        inspect.inspect_artifact_capabilities(TOKEN, artifact_root=root)
    assert marker.read_bytes() == b"keep"


@pytest.mark.parametrize("token", ["", "A" * 64, "a" * 63, "../" + "a" * 61])
def test_token_is_closed_before_mutation(tmp_path: Path, token: str) -> None:
    root = _root(tmp_path)
    with pytest.raises(inspect.ArtifactCapabilityInspectUnavailable):
        inspect.inspect_artifact_capabilities(token, artifact_root=root)
    assert list(root.iterdir()) == []


def test_unsafe_root_is_explicit_false_without_mutation(tmp_path: Path) -> None:
    root = _root(tmp_path)
    os.chmod(root, 0o777)
    assert inspect.inspect_artifact_capabilities(TOKEN, artifact_root=root) is False
    assert list(root.iterdir()) == []


def test_unknown_publish_outcome_is_unavailable_and_not_blindly_cleaned(
    tmp_path: Path, monkeypatch,
) -> None:
    root = _root(tmp_path)
    original = inspect.os.link

    def unknown_link(*args, **kwargs):
        original(*args, **kwargs)
        raise OSError("lost acknowledgement")

    monkeypatch.setattr(inspect.os, "link", unknown_link)
    with pytest.raises(inspect.ArtifactCapabilityInspectUnavailable) as caught:
        inspect.inspect_artifact_capabilities(TOKEN, artifact_root=root)
    assert str(caught.value) == "artifact_capability_inspect_unavailable"
    assert caught.value.__cause__ is None
    prefix = root / f".liquent-staging-probe-{TOKEN}"
    assert prefix.is_dir()
    assert sorted(item.name for item in prefix.iterdir()) == [
        ".capability.tmp", "capability.json",
    ]


def test_cli_failure_is_silent_and_repr_is_detail_free(capsys) -> None:
    assert inspect.main(["--run-token", "bad"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""
    error = inspect.ArtifactCapabilityInspectUnavailable()
    assert str(error) == "artifact_capability_inspect_unavailable"
    assert repr(error) == "ArtifactCapabilityInspectUnavailable('artifact_capability_inspect_unavailable')"
