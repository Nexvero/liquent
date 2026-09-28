from pathlib import Path

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlDirectoryId,
)
from test_lq591_lq593_local_docker_engine_http_client import (
    LABELS,
    FakeTransport,
    client,
    entrypoint,
)


def control_mounts(tmp_path):
    root = tmp_path / "control"
    return [
        f"{root / 'control-artifacts'}:/run/liquent/control:rw",
        f"{root / 'launch-binding.json'}:/run/liquent/launch/launch-binding.json:ro",
    ]


def raw(tmp_path, *, profile, binds):
    labels = dict(LABELS, **{"liquent.supervisor.profile": profile})
    command = entrypoint(labels)
    if profile == "recovery":
        command[0] = "/opt/liquent/recovery-wrapper"
    return {
        "Id": "a" * 64,
        "Config": {
            "Image": "sha256:" + "b" * 64,
            "Labels": labels,
            "Entrypoint": command,
        },
        "State": {"Status": "created"},
        "HostConfig": {
            "Binds": binds, "NetworkMode": "none",
            "RestartPolicy": {"Name": "no"}, "AutoRemove": False,
            "ReadonlyRootfs": True, "CapDrop": ["ALL"],
            "Privileged": False, "PidMode": "private",
        },
    }


def test_writer_mounts_source_read_only_and_target_read_write(tmp_path):
    value = client(tmp_path, FakeTransport([]))
    mounts = value._mounts(
        ManifestHandoffSupervisorControlDirectoryId("directory-591"),
        tmp_path / "source", tmp_path / "target", "writer",
    )
    assert mounts[-2:] == (
        f"{tmp_path / 'source'}:/run/liquent/source:ro",
        f"{tmp_path / 'target'}:/run/liquent/target:rw",
    )


def test_recovery_mounts_only_target_read_only(tmp_path):
    value = client(tmp_path, FakeTransport([]))
    mounts = value._mounts(
        ManifestHandoffSupervisorControlDirectoryId("directory-591"),
        tmp_path / "source", tmp_path / "target", "recovery",
    )
    assert mounts[-1] == f"{tmp_path / 'target'}:/run/liquent/target:ro"
    assert all("/run/liquent/source" not in mount for mount in mounts)
    assert all(not mount.endswith("target:rw") for mount in mounts)


@pytest.mark.parametrize("profile,extra", [
    ("writer", "/run/liquent/source:rw"),
    ("recovery", "/run/liquent/source:ro"),
])
def test_inspect_rejects_wrong_or_extra_capability_mount(tmp_path, profile, extra):
    client(tmp_path, FakeTransport([]))
    binds = control_mounts(tmp_path)
    if profile == "writer":
        binds += [
            f"{tmp_path / 'source'}:{extra}",
            f"{tmp_path / 'target'}:/run/liquent/target:rw",
        ]
    else:
        binds += [
            f"{tmp_path / 'target'}:/run/liquent/target:ro",
            f"{tmp_path / 'source'}:{extra}",
        ]
    transport = FakeTransport([(200, raw(tmp_path, profile=profile, binds=binds))])
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        client(tmp_path, transport).inspect("a" * 64)


def test_missing_non_directory_and_delimiter_roots_fail_before_create(tmp_path):
    value = client(tmp_path, FakeTransport([]))
    directory = ManifestHandoffSupervisorControlDirectoryId("directory-591")
    invalid = (tmp_path / "missing", Path("relative"), Path("/tmp/a:b"))
    for root in invalid:
        with pytest.raises(ManifestHandoffRegistryUnavailable):
            value._mounts(directory, root, tmp_path / "target", "writer")
