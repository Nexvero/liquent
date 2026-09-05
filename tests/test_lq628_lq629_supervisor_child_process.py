from datetime import datetime, timezone

import pytest

from liquent_platform.application.manifest_handoff_supervisor_child_process import (
    OneShotManifestHandoffSupervisorChildProcess,
)
from liquent_platform.identity.manifest_handoff_supervisor import (
    CompletedManifestHandoffRecoveryProcess,
    CompletedManifestHandoffWriterProcess,
    ManifestHandoffRecoveryProcessKind,
    ManifestHandoffWriterProcessKind,
)
from liquent_platform.identity.manifest_handoff_supervisor_capability_executor import (
    ExecutedManifestHandoffRecoveryCapability,
    ExecutedManifestHandoffWriterCapability,
)
from liquent_platform.identity.manifest_handoff_supervisor_correlation import (
    ManifestHandoffSupervisorReleaseId,
)
from liquent_platform.identity.manifest_handoff_supervisor_engine import (
    ManifestHandoffSupervisorEngineProfile,
)
from liquent_platform.identity.manifest_handoff_supervisor_gate_wrapper import (
    AcceptedManifestHandoffSupervisorReleaseToken,
    CompletedManifestHandoffSupervisorGateWrapper,
    ReadyManifestHandoffSupervisorGateWrapper,
    ReleasedManifestHandoffSupervisorGateWrapper,
)
from liquent_platform.identity.manifest_handoff_supervisor_launch_anchor import (
    ManifestHandoffSupervisorLaunchDocumentDigest,
)
from liquent_platform.identity.manifest_handoff_supervisor_launch_document import (
    ManifestHandoffSupervisorLaunchDocumentExpectation,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlArtifactFacts,
    ManifestHandoffSupervisorControlArtifactId,
    ManifestHandoffSupervisorControlArtifactRole,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_artifact import (
    PublishedManifestHandoffSupervisorControlArtifact,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_launch_document import (
    CanonicalManifestHandoffSupervisorLaunchDocumentCodec,
)
from test_lq608_lq609_supervisor_launch_document import launch


NOW = datetime(2026, 8, 28, 12, tzinfo=timezone.utc)
FACTS = ManifestHandoffSupervisorControlArtifactFacts("a" * 64, 1)


def expectation(document):
    encoded = CanonicalManifestHandoffSupervisorLaunchDocumentCodec().encode(document)
    return ManifestHandoffSupervisorLaunchDocumentExpectation(
        document.document_id,
        ManifestHandoffSupervisorLaunchDocumentDigest(encoded.facts.sha256),
        document.creation_id, document.gate.handle_id,
        document.gate.control_directory_id, document.image_digest,
        document.gate.profile,
    )


class Loader:
    def __init__(self, document, events):
        self.document, self.events = document, events

    def load(self, value):
        self.events.append("load")
        return self.document


class Wrapper:
    def __init__(self, events, *, release_after=1):
        self.events, self.release_after, self.checks = events, release_after, 0

    def publish_ready(self, gate):
        self.events.append("ready")
        return ReadyManifestHandoffSupervisorGateWrapper(gate,
            PublishedManifestHandoffSupervisorControlArtifact(
                gate.control_directory_id, gate.ready_artifact_id,
                ManifestHandoffSupervisorControlArtifactRole.WRAPPER_READY, FACTS))

    def await_release(self, ready):
        self.events.append("await")
        self.checks += 1
        if self.checks <= self.release_after:
            return None
        return AcceptedManifestHandoffSupervisorReleaseToken(
            ready, ManifestHandoffSupervisorControlArtifactId("release-token"),
            ManifestHandoffSupervisorReleaseId("release"))

    def publish_consumed(self, token):
        self.events.append("consumed")
        gate = token.ready.binding
        return ReleasedManifestHandoffSupervisorGateWrapper(token,
            PublishedManifestHandoffSupervisorControlArtifact(
                gate.control_directory_id, gate.consumed_artifact_id,
                ManifestHandoffSupervisorControlArtifactRole.RELEASE_CONSUMED, FACTS))

    def publish_terminal(self, request):
        self.events.append("terminal")
        gate = request.gate.token.ready.binding
        return CompletedManifestHandoffSupervisorGateWrapper(request,
            PublishedManifestHandoffSupervisorControlArtifact(
                gate.control_directory_id, gate.terminal_artifact_id,
                ManifestHandoffSupervisorControlArtifactRole.TERMINAL_ENVELOPE, FACTS))


class Executor:
    def __init__(self, events):
        self.events = events

    def execute_writer(self, request):
        self.events.append("execute")
        prepared = request.prepared
        outcome = CompletedManifestHandoffWriterProcess(
            prepared.handle_id, prepared.claim_id, prepared.owner_id,
            ManifestHandoffWriterProcessKind.UNAVAILABLE, NOW)
        return ExecutedManifestHandoffWriterCapability(request, outcome)

    def execute_recovery(self, request):
        self.events.append("execute")
        prepared = request.prepared
        outcome = CompletedManifestHandoffRecoveryProcess(
            prepared.handle_id, prepared.claim_id, prepared.owner_id,
            ManifestHandoffRecoveryProcessKind.OUTCOME_UNKNOWN, NOW)
        return ExecutedManifestHandoffRecoveryCapability(request, outcome)


def process(document, events, wrapper, monotonic):
    return OneShotManifestHandoffSupervisorChildProcess(
        loader=Loader(document, events), gate_wrapper=wrapper,
        executor=Executor(events), clock=lambda: NOW,
        monotonic=lambda: next(monotonic), sleep=lambda seconds: events.append("sleep"),
        maximum_release_wait=10, poll_interval=1,
    )


@pytest.mark.parametrize("profile", list(ManifestHandoffSupervisorEngineProfile))
def test_child_owns_exact_load_ready_release_execute_terminal_order(profile):
    events = []
    document = launch(profile)
    wrapper = Wrapper(events, release_after=1)
    child = process(document, events, wrapper, iter((0.0, 0.0)))
    result = (child.run_writer(expectation(document))
              if profile is ManifestHandoffSupervisorEngineProfile.WRITER
              else child.run_recovery(expectation(document)))
    assert type(result) is CompletedManifestHandoffSupervisorGateWrapper
    assert events == ["load", "ready", "await", "sleep", "await",
                      "consumed", "execute", "terminal"]
    assert repr(child) == "OneShotManifestHandoffSupervisorChildProcess()"


def test_timeout_never_consumes_executes_or_publishes_terminal():
    events = []
    document = launch()
    wrapper = Wrapper(events, release_after=99)
    child = OneShotManifestHandoffSupervisorChildProcess(
        loader=Loader(document, events), gate_wrapper=wrapper,
        executor=Executor(events), clock=lambda: NOW,
        monotonic=iter((0.0, 1.0)).__next__, sleep=lambda seconds: None,
        maximum_release_wait=1, poll_interval=1,
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        child.run_writer(expectation(document))
    assert events == ["load", "ready", "await"]


def test_cross_profile_entrypoint_fails_before_load_or_ready():
    events = []
    document = launch()
    child = process(document, events, Wrapper(events), iter((0.0,)))
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        child.run_recovery(expectation(document))
    assert events == []
