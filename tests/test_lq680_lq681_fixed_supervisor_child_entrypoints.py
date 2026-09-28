import os
from pathlib import Path

import pytest

from liquent_platform.capabilities.private_manifest_handoff import ManifestHandoffResult
from liquent_platform.capabilities.private_manifest_handoff_reconcile import (
    ManifestReconciliationResult,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_artifact import (
    ManifestHandoffSupervisorReleaseTokenDocument,
    PublishManifestHandoffSupervisorControlArtifact,
)
from liquent_platform.identity.manifest_handoff_supervisor_correlation import (
    ManifestHandoffSupervisorReleaseId,
)
from liquent_platform.identity.manifest_handoff_supervisor_engine import (
    ManifestHandoffSupervisorEngineProfile,
)
from liquent_platform.identity.manifest_handoff_supervisor_launch_identity import (
    ManifestHandoffSupervisorLaunchIdentityPolicy,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlArtifactId,
)
from liquent_platform.operators.manifest_handoff_supervisor_child import (
    _run,
    recovery_main,
    writer_main,
)
from liquent_platform.transport.manifest_handoff_supervisor_child_launch_anchor import (
    CanonicalManifestHandoffSupervisorChildLaunchAnchorCodec,
)
from liquent_platform.transport.manifest_handoff_supervisor_control_artifacts import (
    CanonicalManifestHandoffSupervisorControlArtifactCodec,
    DirectAtomicLocalManifestHandoffSupervisorControlArtifacts,
)
from liquent_platform.transport.manifest_handoff_supervisor_launch_document import (
    CanonicalManifestHandoffSupervisorLaunchDocumentCodec,
)
from test_lq628_lq629_supervisor_child_process import NOW, expectation
from test_lq608_lq609_supervisor_launch_document import launch


def setup_process(tmp_path: Path, profile):
    launch_root, control = tmp_path / "launch", tmp_path / "control"
    source, target = tmp_path / "source", tmp_path / "target"
    for path in (launch_root, control, source, target):
        path.mkdir(mode=0o700)
    document = launch(profile)
    encoded = CanonicalManifestHandoffSupervisorLaunchDocumentCodec().encode(document)
    launch_file = launch_root / "launch-binding.json"
    launch_file.write_bytes(encoded.content.value)
    launch_file.chmod(0o640)
    expected = expectation(document)
    adapter = DirectAtomicLocalManifestHandoffSupervisorControlArtifacts(
        control, control_directory_id=expected.control_directory_id,
        codec=CanonicalManifestHandoffSupervisorControlArtifactCodec(),
    )
    token = ManifestHandoffSupervisorReleaseTokenDocument(
        ManifestHandoffSupervisorControlArtifactId("release-token-680"),
        expected.handle_id, ManifestHandoffSupervisorReleaseId("release-680"),
    )
    adapter.publish(PublishManifestHandoffSupervisorControlArtifact(
        expected.control_directory_id,
        CanonicalManifestHandoffSupervisorControlArtifactCodec().encode(token),
    ))
    policy = ManifestHandoffSupervisorLaunchIdentityPolicy(
        os.geteuid(), os.getegid(), os.geteuid() + 1, os.getegid()
    )
    arguments = CanonicalManifestHandoffSupervisorChildLaunchAnchorCodec().encode(
        expected
    )
    return launch_root, control, source, target, policy, arguments


@pytest.mark.parametrize("profile", list(ManifestHandoffSupervisorEngineProfile))
def test_fixed_composition_runs_exact_profile_to_terminal(tmp_path, profile):
    launch_root, control, source, target, policy, arguments = setup_process(
        tmp_path, profile
    )
    events = []

    def writer(source_root, target_root, name):
        events.append(("writer", source_root, target_root, name))
        return ManifestHandoffResult("target_not_absent")

    def reconciler(target_root, name):
        events.append(("recovery", target_root, name))
        return ManifestReconciliationResult("manifest_absent")

    result = _run(
        profile, arguments, launch_root=launch_root, control=control,
        source=source, target=target, identity_policy=policy,
        writer=writer, reconciler=reconciler, clock=lambda: NOW,
        monotonic=lambda: 0.0, sleep=lambda seconds: None,
    )
    assert result == 0
    if profile is ManifestHandoffSupervisorEngineProfile.WRITER:
        assert events == [("writer", source, target, "handoff-608")]
    else:
        assert events == [("recovery", target, "handoff-608")]
    assert {path.name for path in control.iterdir()} == {
        "release-token.json", "wrapper-ready.json", "release-consumed.json",
        "terminal-envelope.json",
    }


def test_cross_profile_and_malformed_commands_fail_without_output(tmp_path, capsys):
    _, _, _, _, _, arguments = setup_process(
        tmp_path, ManifestHandoffSupervisorEngineProfile.WRITER
    )
    assert recovery_main(arguments) == 1
    assert writer_main(("--free-command", "true")) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""


def test_project_registers_only_two_fixed_wrapper_commands():
    project = (Path(__file__).parents[1] / "pyproject.toml").read_text(
        encoding="utf-8"
    )
    assert project.count("liquent-supervisor-writer-wrapper =") == 1
    assert project.count("liquent-supervisor-recovery-wrapper =") == 1
    assert "manifest_handoff_supervisor_child:writer_main" in project
    assert "manifest_handoff_supervisor_child:recovery_main" in project
