from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import liquent_platform.operators.runtime_inspect as inspect


class Entry:
    def __init__(self, group="console_scripts", name="liquent-research-worker",
                 value="liquent_platform.operators.research_worker:main"):
        self.group, self.name, self.value = group, name, value


class Distribution:
    def __init__(self, entries): self.entry_points = entries


def _script(tmp_path: Path) -> tuple[Path, Path]:
    prefix = tmp_path / "venv"
    target = prefix / "bin/liquent-research-worker"
    target.parent.mkdir(parents=True)
    target.write_text("launcher")
    os.chmod(target, 0o700)
    return prefix, target


def test_entrypoint_requires_exact_single_metadata_and_safe_executable(tmp_path: Path) -> None:
    prefix, script = _script(tmp_path)
    loader = lambda _: Distribution([Entry()])
    assert inspect.inspect_entrypoint(
        distribution_loader=loader, script_path=script, runtime_prefix=prefix,
    ) is True
    assert inspect.inspect_entrypoint(
        distribution_loader=lambda _: Distribution([]),
        script_path=script, runtime_prefix=prefix,
    ) is False
    assert inspect.inspect_entrypoint(
        distribution_loader=lambda _: Distribution([Entry(), Entry()]),
        script_path=script, runtime_prefix=prefix,
    ) is False
    assert inspect.inspect_entrypoint(
        distribution_loader=lambda _: Distribution([Entry(value="other:main")]),
        script_path=script, runtime_prefix=prefix,
    ) is False
    os.chmod(script, 0o722)
    assert inspect.inspect_entrypoint(
        distribution_loader=loader, script_path=script, runtime_prefix=prefix,
    ) is False


def test_entrypoint_symlink_or_outside_prefix_is_unavailable(tmp_path: Path) -> None:
    prefix, script = _script(tmp_path)
    link = prefix / "bin/link"
    link.symlink_to(script)
    with pytest.raises(inspect.RuntimeInspectUnavailable):
        inspect.inspect_entrypoint(
            distribution_loader=lambda _: Distribution([Entry()]),
            script_path=link, runtime_prefix=prefix,
        )
    with pytest.raises(inspect.RuntimeInspectUnavailable):
        inspect.inspect_entrypoint(
            distribution_loader=lambda _: Distribution([Entry()]),
            script_path=script, runtime_prefix=tmp_path / "other",
        )


def test_input_ownership_checks_descriptors_without_reading_contents(tmp_path: Path) -> None:
    config = tmp_path / "config"
    worker = tmp_path / "worker"
    config.write_bytes(b"not-json-and-never-read")
    worker.write_bytes(b"not-an-id-and-never-read")
    os.chmod(config, 0o400)
    os.chmod(worker, 0o600)
    assert inspect.inspect_input_ownership(
        config_path=config, worker_id_path=worker,
    ) is True
    os.chmod(worker, 0o644)
    assert inspect.inspect_input_ownership(
        config_path=config, worker_id_path=worker,
    ) is False


def _mountinfo(root: Path, options="ro,relatime", super_options="ro,bind") -> Path:
    escaped = str(root).replace(" ", "\\040")
    path = root.parent / "mountinfo"
    path.write_text(f"36 25 0:32 / {escaped} {options} - ext4 /dev/root {super_options}\n")
    return path


def test_data_read_only_observes_mount_and_existing_files_without_write(tmp_path: Path) -> None:
    root = tmp_path / "research data"
    root.mkdir(mode=0o700)
    fixture = root / "fixture.csv"
    fixture.write_text("private-content")
    os.chmod(fixture, 0o400)
    os.chmod(root, 0o500)
    before = fixture.read_bytes()
    assert inspect.inspect_data_read_only(
        root=root, mountinfo_path=_mountinfo(root),
    ) is True
    assert fixture.read_bytes() == before
    assert sorted(item.name for item in root.iterdir()) == ["fixture.csv"]


def test_writable_mount_or_file_is_explicit_false(tmp_path: Path) -> None:
    root = tmp_path / "data"
    root.mkdir(mode=0o700)
    fixture = root / "fixture.csv"
    fixture.write_text("x")
    os.chmod(fixture, 0o400)
    os.chmod(root, 0o500)
    assert inspect.inspect_data_read_only(
        root=root, mountinfo_path=_mountinfo(root, options="rw,relatime", super_options="rw"),
    ) is False
    os.chmod(fixture, 0o600)
    assert inspect.inspect_data_read_only(
        root=root, mountinfo_path=_mountinfo(root),
    ) is False


def test_missing_duplicate_or_empty_mount_observation_is_unavailable(tmp_path: Path) -> None:
    root = tmp_path / "data"
    root.mkdir(mode=0o700)
    mountinfo = _mountinfo(root)
    os.chmod(root, 0o500)
    with pytest.raises(inspect.RuntimeInspectUnavailable):
        inspect.inspect_data_read_only(root=root, mountinfo_path=mountinfo)
    os.chmod(root, 0o700)
    (root / "fixture").write_text("x")
    os.chmod(root / "fixture", 0o400)
    os.chmod(root, 0o500)
    mountinfo.write_text(mountinfo.read_text() * 2)
    with pytest.raises(inspect.RuntimeInspectUnavailable):
        inspect.inspect_data_read_only(root=root, mountinfo_path=mountinfo)


def test_phase_output_is_exact_and_cli_failure_is_silent(monkeypatch, capsys) -> None:
    monkeypatch.setattr(inspect, "inspect_entrypoint", lambda: True)
    expected = b'{"facts":{"entrypoint_present":true},"phase":"entrypoint","schema_version":1}\n'
    assert inspect.inspect_phase("entrypoint") == expected
    assert inspect.main(["--phase", "entrypoint"]) == 0
    assert capsys.readouterr().out.encode() == expected
    assert inspect.main(["--phase", "unknown"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""


def test_repr_and_errors_disclose_no_paths_or_metadata() -> None:
    error = inspect.RuntimeInspectUnavailable()
    assert str(error) == "runtime_inspect_unavailable"
    assert error.__cause__ is None
    assert set(inspect.PHASE_FACT) == {"entrypoint", "input_ownership", "data_read_only"}
