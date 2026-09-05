import os
from pathlib import Path

import pytest

from liquent_platform.identity.manifest_handoff_supervisor_launch_document import (
    PublishManifestHandoffSupervisorLaunchDocument,
)
from liquent_platform.identity.manifest_handoff_supervisor_launch_identity import (
    ManifestHandoffSupervisorLaunchIdentityPolicy,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.local_docker_engine_http_client import (
    LocalDockerEngineHttpClient,
)
from liquent_platform.transport.manifest_handoff_supervisor_launch_document import (
    CanonicalManifestHandoffSupervisorLaunchDocumentCodec,
)
from liquent_platform.transport.manifest_handoff_supervisor_launch_file import (
    AtomicLocalManifestHandoffSupervisorLaunchDocuments,
)
from test_lq612_lq613_supervisor_launch_file import document


def policy():
    return ManifestHandoffSupervisorLaunchIdentityPolicy(
        os.geteuid(), os.getegid(), os.geteuid() + 1, os.getegid()
    )


@pytest.mark.parametrize("values", [
    (0, 20, 1000, 20),
    (501, 0, 1000, 0),
    (501, 20, 0, 20),
    (501, 20, 501, 20),
    (501, 20, 1000, 21),
    (True, 20, 1000, 20),
    (501, 20, 2_147_483_648, 20),
])
def test_policy_rejects_root_boolean_range_owner_and_group_mismatch(values):
    with pytest.raises(ValueError):
        ManifestHandoffSupervisorLaunchIdentityPolicy(*values)


def test_policy_has_closed_numeric_docker_user_and_repr():
    value = policy()
    assert value.docker_user == f"{os.geteuid() + 1}:{os.getegid()}"
    assert str(os.geteuid()) not in repr(value)
    assert str(os.getegid()) not in repr(value)


def reader_store(tmp_path):
    root, directory = tmp_path / "control", tmp_path / "control" / "job"
    root.mkdir(mode=0o700)
    directory.mkdir(mode=0o700)
    codec = CanonicalManifestHandoffSupervisorLaunchDocumentCodec()
    store = AtomicLocalManifestHandoffSupervisorLaunchDocuments(
        root,
        resolve_directory=lambda value: directory if value.value == "directory-612" else None,
        codec=codec,
        identity_policy=policy(),
    )
    return store, codec, directory


def test_reader_bound_publish_is_atomic_owner_group_and_0640(tmp_path):
    store, codec, directory = reader_store(tmp_path)
    encoded = codec.encode(document())
    result = store.publish(PublishManifestHandoffSupervisorLaunchDocument(encoded))
    path = directory / "launch-binding.json"
    facts = path.stat()
    assert result.facts == encoded.facts
    assert facts.st_uid == os.geteuid()
    assert facts.st_gid == os.getegid()
    assert facts.st_mode & 0o777 == 0o640
    assert facts.st_nlink == 1
    assert store.read(document().gate.control_directory_id) == document()


def test_reader_bound_identical_retry_is_stable(tmp_path):
    store, codec, directory = reader_store(tmp_path)
    request = PublishManifestHandoffSupervisorLaunchDocument(codec.encode(document()))
    first = store.publish(request)
    before = (directory / "launch-binding.json").stat()
    second = store.publish(request)
    after = (directory / "launch-binding.json").stat()
    assert first == second
    assert (before.st_ino, before.st_mtime_ns) == (after.st_ino, after.st_mtime_ns)


def test_reader_bound_store_rejects_wrong_owner_policy(tmp_path):
    root = tmp_path / "control"
    root.mkdir(mode=0o700)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        AtomicLocalManifestHandoffSupervisorLaunchDocuments(
            root, resolve_directory=lambda value: None,
            codec=CanonicalManifestHandoffSupervisorLaunchDocumentCodec(),
            identity_policy=ManifestHandoffSupervisorLaunchIdentityPolicy(
                os.geteuid() + 1, os.getegid(), os.geteuid() + 2, os.getegid()
            ),
        )


class NoIoTransport:
    def request(self, *args, **kwargs):
        raise AssertionError("unexpected I/O")

    def close(self):
        return None


def test_docker_client_materializes_exact_policy_user_without_io(tmp_path):
    (tmp_path / "control-artifacts").mkdir(mode=0o700)
    (tmp_path / "source").mkdir()
    (tmp_path / "target").mkdir()
    launch = tmp_path / "launch-binding.json"
    launch.write_bytes(b"launch")
    launch.chmod(0o640)
    value = LocalDockerEngineHttpClient(
        Path("/private/run/docker.sock"),
        control_directory_resolver=lambda directory_id: tmp_path,
        writer_command=("/writer",), recovery_command=("/recovery",),
        identity_policy=policy(),
        transport_factory=lambda path, timeout: NoIoTransport(),
    )
    specification = {
        "image": "sha256:" + "a" * 64,
        "labels": {
            "liquent.supervisor.creation": "creation",
            "liquent.supervisor.handle": "handle",
            "liquent.supervisor.control": "directory",
            "liquent.supervisor.launch-document": "launch",
            "liquent.supervisor.launch-sha256": "e" * 64,
            "liquent.supervisor.profile": "writer",
        },
        "profile": "writer", "network_mode": "none", "restart_policy": "no",
        "auto_remove": False, "readonly_rootfs": True, "cap_drop": ("ALL",),
        "privileged": False, "pid_mode": "private",
        "source_root": tmp_path / "source", "target_root": tmp_path / "target",
    }
    assert value._create_specification(specification)["User"] == policy().docker_user


def test_docker_client_rejects_user_string_mixed_with_policy():
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        LocalDockerEngineHttpClient(
            Path("/private/run/docker.sock"),
            control_directory_resolver=lambda directory_id: None,
            writer_command=("/writer",), recovery_command=("/recovery",),
            user="1000:1000", identity_policy=policy(),
            transport_factory=lambda path, timeout: NoIoTransport(),
        )
