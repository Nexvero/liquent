"""Closed direct terminal artifact observations for the parent."""

from dataclasses import dataclass, field

from .manifest_handoff_supervisor_control_artifact import (
    ManifestHandoffSupervisorTerminalEnvelopeDocument,
    PublishedManifestHandoffSupervisorControlArtifact,
)
from .manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlArtifactRole,
    RecordedManifestHandoffSupervisorControlArtifact,
)


@dataclass(frozen=True, slots=True)
class ObservedManifestHandoffSupervisorTerminalArtifact:
    document: ManifestHandoffSupervisorTerminalEnvelopeDocument = field(repr=False)
    publication: PublishedManifestHandoffSupervisorControlArtifact = field(repr=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.document) is ManifestHandoffSupervisorTerminalEnvelopeDocument,
            type(self.publication) is PublishedManifestHandoffSupervisorControlArtifact,
            self.publication.artifact_id == self.document.artifact_id,
            self.publication.role is ManifestHandoffSupervisorControlArtifactRole.TERMINAL_ENVELOPE,
        )):
            raise ValueError("manifest handoff supervisor terminal observation is invalid")


@dataclass(frozen=True, slots=True)
class RecordedManifestHandoffSupervisorTerminalArtifact:
    observation: ObservedManifestHandoffSupervisorTerminalArtifact = field(repr=False)
    record: RecordedManifestHandoffSupervisorControlArtifact = field(repr=False)

    def __post_init__(self) -> None:
        document, publication = self.observation.document, self.observation.publication
        if not all((
            type(self.record) is RecordedManifestHandoffSupervisorControlArtifact,
            self.record.artifact_id == document.artifact_id,
            self.record.handle_id == document.handle_id,
            self.record.role is ManifestHandoffSupervisorControlArtifactRole.TERMINAL_ENVELOPE,
            self.record.correlation_id == document.correlation_id,
            self.record.facts == publication.facts,
        )):
            raise ValueError("manifest handoff supervisor terminal record is invalid")
