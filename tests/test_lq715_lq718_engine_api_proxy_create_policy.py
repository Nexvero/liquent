import json
from pathlib import Path

import pytest

from liquent_platform.identity.manifest_handoff_supervisor import ManifestHandoffSupervisorHandleId
from liquent_platform.identity.manifest_handoff_supervisor_engine import ManifestHandoffSupervisorEngineProfile
from liquent_platform.identity.manifest_handoff_supervisor_launch_anchor import ManifestHandoffSupervisorLaunchDocumentDigest
from liquent_platform.identity.manifest_handoff_supervisor_launch_document import ManifestHandoffSupervisorLaunchDocumentExpectation
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlArtifactId, ManifestHandoffSupervisorControlDirectoryId,
    ManifestHandoffSupervisorCreationId, ManifestHandoffSupervisorImageDigest,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_child_launch_anchor import CanonicalManifestHandoffSupervisorChildLaunchAnchorCodec
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_proxy_policy import ClosedManifestHandoffSupervisorCreateRequestPolicy


ROOT = Path("/srv/liquent/supervisor")
SOURCE = Path("/srv/liquent/source")
TARGET = Path("/srv/liquent/target")
IMAGE = "sha256:" + "b" * 64


def policy():
    return ClosedManifestHandoffSupervisorCreateRequestPolicy(
        control_root=ROOT, source_root=SOURCE, target_root=TARGET,
        writer_command="liquent-supervisor-writer-wrapper",
        recovery_command="liquent-supervisor-recovery-wrapper",
        wrapper_uid=10002, wrapper_gid=10003,
    )


def body(profile="writer"):
    expectation = ManifestHandoffSupervisorLaunchDocumentExpectation(
        ManifestHandoffSupervisorControlArtifactId("launch-715"),
        ManifestHandoffSupervisorLaunchDocumentDigest("d" * 64),
        ManifestHandoffSupervisorCreationId("creation-715"),
        ManifestHandoffSupervisorHandleId("handle-715"),
        ManifestHandoffSupervisorControlDirectoryId("directory-715"),
        ManifestHandoffSupervisorImageDigest(IMAGE),
        ManifestHandoffSupervisorEngineProfile(profile),
    )
    labels = {
        "liquent.supervisor.creation": "creation-715", "liquent.supervisor.handle": "handle-715",
        "liquent.supervisor.control": "directory-715", "liquent.supervisor.launch-document": "launch-715",
        "liquent.supervisor.launch-sha256": "d" * 64, "liquent.supervisor.profile": profile,
    }
    control = ROOT / "job-715"
    binds = [
        f"{control / 'control-artifacts'}:/run/liquent/control:rw",
        f"{control / 'launch-binding.json'}:/run/liquent/launch/launch-binding.json:ro",
    ]
    if profile == "writer":
        binds += [f"{SOURCE / 'scope'}:/run/liquent/source:ro", f"{TARGET / 'scope'}:/run/liquent/target:rw"]
    else:
        binds += [f"{TARGET / 'scope'}:/run/liquent/target:ro"]
    value = {
        "Image": IMAGE,
        "Entrypoint": ["liquent-supervisor-writer-wrapper" if profile == "writer" else "liquent-supervisor-recovery-wrapper"] + list(CanonicalManifestHandoffSupervisorChildLaunchAnchorCodec().encode(expectation)),
        "User": "10002:10003", "Labels": labels,
        "HostConfig": {"AutoRemove": False, "Binds": binds, "CapDrop": ["ALL"],
            "NetworkMode": "none", "PidMode": "private", "Privileged": False,
            "ReadonlyRootfs": True, "RestartPolicy": {"MaximumRetryCount": 0, "Name": "no"}},
    }
    return value


@pytest.mark.parametrize("profile", ("writer", "recovery"))
def test_exact_profile_is_authorized_without_io(profile) -> None:
    value = body(profile)
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    result = policy().authorize(encoded)
    assert result.profile == profile
    assert result.source_root is (None if profile == "recovery" else result.source_root)
    assert result.target_root == TARGET / "scope"


@pytest.mark.parametrize("mutation", (
    lambda v: v.update(User="0:0"),
    lambda v: v.update(Image="ubuntu:latest"),
    lambda v: v["Labels"].update(extra="value"),
    lambda v: v["HostConfig"].update(NetworkMode="host"),
    lambda v: v["HostConfig"].update(Privileged=True),
    lambda v: v["HostConfig"].update(Binds=v["HostConfig"]["Binds"] + ["/etc:/host:ro"]),
    lambda v: v["Entrypoint"].__setitem__(0, "sh"),
    lambda v: v["HostConfig"]["Binds"].__setitem__(-1, "/etc:/run/liquent/target:rw"),
))
def test_any_semantic_expansion_fails_detail_free(mutation) -> None:
    value = body()
    mutation(value)
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        policy().authorize(encoded)
    assert str(caught.value) == "manifest_handoff_registry_unavailable"


def test_noncanonical_or_duplicate_json_is_rejected() -> None:
    canonical = json.dumps(body(), sort_keys=True, separators=(",", ":")).encode()
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        policy().authorize(json.dumps(body()).encode())
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        policy().authorize(canonical[:-1] + b',"Image":"sha256:' + b'e' * 64 + b'"}')


def test_policy_has_no_filesystem_or_forwarding_surface() -> None:
    value = policy()
    for name in ("forward", "connect", "listen", "open", "stat", "resolve"):
        assert not hasattr(value, name)
