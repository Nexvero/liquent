import os
from pathlib import Path
import stat

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_host_preflight import (
    ManifestHandoffSupervisorEngineApiHostPreflight,
)


def setup_host(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    uid, gid = os.geteuid(), os.getegid()
    if uid < 1 or gid < 1:
        pytest.skip("non-root identity required for exact host ownership evidence")
    root = tmp_path
    control, source, target = (
        root / "control", root / "source", root / "target"
    )
    for path, mode in ((control, 0o700), (source, 0o750), (target, 0o750)):
        path.mkdir(mode=mode)
        path.chmod(mode)
    proxy_path, daemon_path = root / "proxy.sock", root / "daemon.sock"
    proxy_path.write_bytes(b"")
    daemon_path.write_bytes(b"")
    proxy_path.chmod(0o660)
    daemon_path.chmod(0o660)
    original_lstat = os.lstat
    socket_identities = {
        proxy_path: (
            original_lstat(proxy_path).st_dev,
            original_lstat(proxy_path).st_ino,
            original_lstat(proxy_path).st_ctime_ns,
        ),
        daemon_path: (
            original_lstat(daemon_path).st_dev,
            original_lstat(daemon_path).st_ino,
            original_lstat(daemon_path).st_ctime_ns,
        ),
    }

    def socket_aware_lstat(path):
        facts = original_lstat(path)
        candidate = Path(path)
        if socket_identities.get(candidate) == (
            facts.st_dev,
            facts.st_ino,
            facts.st_ctime_ns,
        ):
            return os.stat_result((stat.S_IFSOCK | stat.S_IMODE(facts.st_mode), *facts[1:]))
        return facts

    monkeypatch.setattr(os, "lstat", socket_aware_lstat)
    preflight = ManifestHandoffSupervisorEngineApiHostPreflight(
        proxy_socket=proxy_path, daemon_socket=daemon_path,
        control_root=control, source_root=source, target_root=target,
        proxy_uid=uid, client_gid=gid, daemon_uid=uid, daemon_gid=gid,
        host_owner_uid=uid, host_owner_gid=gid,
        data_owner_uid=uid, data_gid=gid,
    )
    return preflight, {
        "proxy": proxy_path, "daemon": daemon_path,
        "control": control, "source": source, "target": target,
    }


def test_exact_host_facts_are_ready_without_connecting_or_mutating(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    preflight, paths = setup_host(tmp_path, monkeypatch)
    before = {name: path.stat() for name, path in paths.items()}
    result = preflight.check()
    after = {name: path.stat() for name, path in paths.items()}
    assert result.ready is True
    assert result.reason == "manifest_handoff_supervisor_host_ready"
    assert {
        name: (facts.st_ino, facts.st_mode, facts.st_uid, facts.st_gid)
        for name, facts in before.items()
    } == {
        name: (facts.st_ino, facts.st_mode, facts.st_uid, facts.st_gid)
        for name, facts in after.items()
    }


def test_dependency_preflight_precedes_proxy_listener_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    preflight, paths = setup_host(tmp_path, monkeypatch)
    paths["proxy"].unlink()
    before = preflight.check_before_listener()
    assert before.ready is True
    assert before.reason == "manifest_handoff_supervisor_host_dependencies_ready"
    assert preflight.check().ready is False


@pytest.mark.parametrize("role", ("proxy", "daemon", "control", "source", "target"))
def test_any_mode_drift_is_detail_free_not_ready(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, role: str,
) -> None:
    preflight, paths = setup_host(tmp_path, monkeypatch)
    paths[role].chmod(0o777)
    result = preflight.check()
    assert result.ready is False
    assert result.reason == "manifest_handoff_supervisor_host_unavailable"
    assert role not in result.reason


def test_regular_file_cannot_replace_proxy_socket(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    preflight, paths = setup_host(tmp_path, monkeypatch)
    paths["proxy"].unlink()
    paths["proxy"].write_bytes(b"not a socket")
    paths["proxy"].chmod(0o660)
    assert preflight.check().ready is False


def test_symlink_cannot_replace_a_data_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    preflight, paths = setup_host(tmp_path, monkeypatch)
    source = paths["source"]
    source.rmdir()
    source.symlink_to(paths["target"], target_is_directory=True)
    assert preflight.check().ready is False


def test_invalid_or_overlapping_configuration_fails_before_check(tmp_path: Path) -> None:
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        ManifestHandoffSupervisorEngineApiHostPreflight(
            proxy_socket=Path("proxy.sock"), daemon_socket=tmp_path / "daemon.sock",
            control_root=tmp_path / "same", source_root=tmp_path / "same",
            target_root=tmp_path / "target", proxy_uid=1, client_gid=1,
            daemon_uid=0, daemon_gid=1, host_owner_uid=1, host_owner_gid=1,
            data_owner_uid=1, data_gid=1,
        )


def test_preflight_has_no_create_chmod_chown_connect_or_cleanup_surface() -> None:
    surface = vars(ManifestHandoffSupervisorEngineApiHostPreflight)
    for name in ("create", "chmod", "chown", "connect", "bind", "remove", "cleanup"):
        assert name not in surface
