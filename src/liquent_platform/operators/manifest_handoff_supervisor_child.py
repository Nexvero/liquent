"""Fixed writer and recovery entrypoints for one supervisor child."""

from datetime import datetime, timezone
import os
from pathlib import Path
import stat
import sys
import time

from liquent_platform.application.manifest_handoff_supervisor_child_capabilities import (
    LocalManifestHandoffSupervisorChildCapabilityExecutor,
)
from liquent_platform.application.manifest_handoff_supervisor_child_process import (
    OneShotManifestHandoffSupervisorChildProcess,
)
from liquent_platform.capabilities.private_manifest_handoff import handoff_manifest
from liquent_platform.capabilities.private_manifest_handoff_reconcile import (
    reconcile_manifest_handoff,
)
from liquent_platform.identity.manifest_handoff_supervisor_engine import (
    ManifestHandoffSupervisorEngineProfile,
)
from liquent_platform.identity.manifest_handoff_supervisor_gate_wrapper import (
    CompletedManifestHandoffSupervisorGateWrapper,
    ManifestHandoffSupervisorGateWrapperConflict,
)
from liquent_platform.identity.manifest_handoff_supervisor_launch_identity import (
    ManifestHandoffSupervisorLaunchIdentityPolicy,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_child_launch_anchor import (
    CanonicalManifestHandoffSupervisorChildLaunchAnchorCodec,
)
from liquent_platform.transport.manifest_handoff_supervisor_control_artifacts import (
    CanonicalManifestHandoffSupervisorControlArtifactCodec,
    DirectAtomicLocalManifestHandoffSupervisorControlArtifacts,
)
from liquent_platform.transport.manifest_handoff_supervisor_gate_wrapper import (
    FileManifestHandoffSupervisorGateWrapper,
)
from liquent_platform.transport.manifest_handoff_supervisor_launch_document import (
    CanonicalManifestHandoffSupervisorLaunchDocumentCodec,
)
from liquent_platform.transport.manifest_handoff_supervisor_launch_loader import (
    ReadOnlyManifestHandoffSupervisorLaunchDocumentLoader,
)


_LAUNCH_ROOT = Path("/run/liquent/launch")
_CONTROL = Path("/run/liquent/control")
_SOURCE = Path("/run/liquent/source")
_TARGET = Path("/run/liquent/target")
_MAXIMUM_RELEASE_WAIT = 300.0
_POLL_INTERVAL = 0.25


def _run(profile, arguments, *, launch_root=_LAUNCH_ROOT, control=_CONTROL,
         source=_SOURCE, target=_TARGET, identity_policy=None,
         writer=handoff_manifest, reconciler=reconcile_manifest_handoff,
         clock=lambda: datetime.now(timezone.utc), monotonic=time.monotonic,
         sleep=time.sleep):
    if type(arguments) is not tuple:
        raise ManifestHandoffRegistryUnavailable
    expectation = CanonicalManifestHandoffSupervisorChildLaunchAnchorCodec().decode(
        arguments
    )
    if expectation.profile is not profile:
        raise ManifestHandoffRegistryUnavailable
    policy = identity_policy or _identity_policy(launch_root)
    launch_loader = ReadOnlyManifestHandoffSupervisorLaunchDocumentLoader(
        launch_root, codec=CanonicalManifestHandoffSupervisorLaunchDocumentCodec(),
        identity_policy=policy,
    )
    artifacts = DirectAtomicLocalManifestHandoffSupervisorControlArtifacts(
        control, control_directory_id=expectation.control_directory_id,
        codec=CanonicalManifestHandoffSupervisorControlArtifactCodec(),
    )
    gate = FileManifestHandoffSupervisorGateWrapper(
        codec=CanonicalManifestHandoffSupervisorControlArtifactCodec(),
        publisher=artifacts, reader=artifacts,
    )
    executor = LocalManifestHandoffSupervisorChildCapabilityExecutor(
        source_root=source, target_root=target, writer=writer,
        reconciler=reconciler, clock=clock,
    )
    child = OneShotManifestHandoffSupervisorChildProcess(
        loader=launch_loader, gate_wrapper=gate, executor=executor,
        clock=clock, monotonic=monotonic, sleep=sleep,
        maximum_release_wait=_MAXIMUM_RELEASE_WAIT,
        poll_interval=_POLL_INTERVAL,
    )
    result = (
        child.run_writer(expectation)
        if profile is ManifestHandoffSupervisorEngineProfile.WRITER
        else child.run_recovery(expectation)
    )
    if type(result) is CompletedManifestHandoffSupervisorGateWrapper:
        return 0
    if type(result) is ManifestHandoffSupervisorGateWrapperConflict:
        return 3
    raise ManifestHandoffRegistryUnavailable


def _identity_policy(launch_root):
    try:
        facts = os.lstat(launch_root / "launch-binding.json")
        if not stat.S_ISREG(facts.st_mode):
            raise ManifestHandoffRegistryUnavailable
        return ManifestHandoffSupervisorLaunchIdentityPolicy(
            facts.st_uid, facts.st_gid, os.geteuid(), os.getegid()
        )
    except ManifestHandoffRegistryUnavailable:
        raise
    except Exception:
        raise ManifestHandoffRegistryUnavailable from None


def _main(profile, argv=None) -> int:
    try:
        return _run(profile, tuple(sys.argv[1:] if argv is None else argv))
    except ManifestHandoffRegistryUnavailable:
        return 1
    except Exception:
        return 1


def writer_main(argv=None) -> int:
    return _main(ManifestHandoffSupervisorEngineProfile.WRITER, argv)


def recovery_main(argv=None) -> int:
    return _main(ManifestHandoffSupervisorEngineProfile.RECOVERY, argv)
