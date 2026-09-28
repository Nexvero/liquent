from datetime import datetime, timezone
import inspect
from pathlib import Path

import pytest

from liquent_platform.identity.manifest_handoff import (
    AppendedManifestHandoffObservation,
    ManifestHandoffAttemptId,
    ManifestHandoffFacts,
    ManifestHandoffObservationConflict,
    ManifestHandoffObservationId,
    ManifestHandoffObservationKind,
)
from liquent_platform.identity.ports import (
    ControlledManifestHandoffCleanupObservationAppend,
    ControlledManifestHandoffReconciliationObservationAppend,
    ControlledManifestHandoffWriterObservationAppend,
)


NOW = datetime(2026, 8, 24, 15, tzinfo=timezone.utc)
OBSERVATION = ManifestHandoffObservationId("observation-434")
ATTEMPT = ManifestHandoffAttemptId("attempt-434")
FACTS = ManifestHandoffFacts("a" * 64, 3)


def test_manifest_facts_are_closed_validated_and_repr_safe() -> None:
    assert FACTS.file_count == 3
    assert "a" * 64 not in repr(FACTS)
    for digest, count in (("A" * 64, 1), ("a" * 63, 1), ("a" * 64, 0), ("a" * 64, True)):
        with pytest.raises(ValueError):
            ManifestHandoffFacts(digest, count)


@pytest.mark.parametrize("kind", [
    ManifestHandoffObservationKind.WRITER_HANDED_OFF,
    ManifestHandoffObservationKind.MANIFEST_TEMPORARY_ONLY,
    ManifestHandoffObservationKind.MANIFEST_HANDED_OFF,
    ManifestHandoffObservationKind.MANIFEST_HANDED_OFF_PENDING_CLEANUP,
    ManifestHandoffObservationKind.CLEANUP_COMPLETED,
])
def test_factual_outcomes_require_facts(kind) -> None:
    value = AppendedManifestHandoffObservation(
        OBSERVATION, ATTEMPT, 2, kind, NOW, FACTS
    )
    assert value.facts == FACTS
    assert "observation-434" not in repr(value)
    assert "attempt-434" not in repr(value)
    with pytest.raises(ValueError):
        AppendedManifestHandoffObservation(OBSERVATION, ATTEMPT, 2, kind, NOW)


@pytest.mark.parametrize("kind", [
    ManifestHandoffObservationKind.WRITER_STARTED,
    ManifestHandoffObservationKind.WRITER_OUTCOME_UNKNOWN,
    ManifestHandoffObservationKind.MANIFEST_ABSENT,
    ManifestHandoffObservationKind.MANIFEST_HANDOFF_CONFLICT,
    ManifestHandoffObservationKind.CLEANUP_OUTCOME_UNKNOWN,
])
def test_non_factual_outcomes_reject_facts(kind) -> None:
    assert AppendedManifestHandoffObservation(
        OBSERVATION, ATTEMPT, 2, kind, NOW
    ).facts is None
    with pytest.raises(ValueError):
        AppendedManifestHandoffObservation(OBSERVATION, ATTEMPT, 2, kind, NOW, FACTS)


def test_append_sequence_time_and_conflict_are_closed() -> None:
    with pytest.raises(ValueError):
        AppendedManifestHandoffObservation(
            OBSERVATION, ATTEMPT, 1,
            ManifestHandoffObservationKind.WRITER_STARTED, NOW,
        )
    with pytest.raises(ValueError):
        AppendedManifestHandoffObservation(
            OBSERVATION, ATTEMPT, 2,
            ManifestHandoffObservationKind.WRITER_STARTED, NOW.replace(tzinfo=None),
        )
    with pytest.raises(ValueError):
        AppendedManifestHandoffObservation(
            OBSERVATION, ATTEMPT, 2,
            ManifestHandoffObservationKind.RESERVED, NOW,
        )
    assert repr(ManifestHandoffObservationConflict()) == "ManifestHandoffObservationConflict()"


def test_ports_have_source_specific_methods_without_generic_kind_or_sequence() -> None:
    expected = {
        ControlledManifestHandoffWriterObservationAppend: {
            "record_writer_started", "record_writer_handed_off",
            "record_writer_outcome_unknown",
        },
        ControlledManifestHandoffReconciliationObservationAppend: {
            "record_manifest_absent", "record_manifest_temporary_only",
            "record_manifest_handed_off",
            "record_manifest_handed_off_pending_cleanup",
            "record_manifest_handoff_conflict",
        },
        ControlledManifestHandoffCleanupObservationAppend: {
            "record_cleanup_completed", "record_cleanup_outcome_unknown",
        },
    }
    for protocol, methods in expected.items():
        assert methods <= set(protocol.__dict__)
        for name in methods:
            parameters = inspect.signature(getattr(protocol, name)).parameters
            assert "kind" not in parameters
            assert "sequence_number" not in parameters
            assert "observed_at" not in parameters
            assert set(parameters) <= {"self", "observation_id", "attempt_id", "facts"}


def test_roadmap_links_types_and_ports_without_adapter_or_migration() -> None:
    root = Path(__file__).parents[1]
    roadmap = (root / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-434 manifest handoff observation types and closed ports:" in roadmap
    assert "`docs/lq-434-manifest-handoff-observation-types-and-closed-ports.md`" in roadmap
    assert "nächster Slice LQ-435" in roadmap
