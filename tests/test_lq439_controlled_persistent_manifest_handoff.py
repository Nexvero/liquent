from datetime import datetime, timezone
from pathlib import Path

import pytest

from liquent_platform.application.manifest_handoff import (
    ControlledPersistentManifestHandoff,
    ManifestHandoffCompositionUnavailable,
)
from liquent_platform.identity.access import UserId
from liquent_platform.identity.manifest_handoff import (
    AppendedManifestHandoffObservation,
    ManifestHandoffAttemptId,
    ManifestHandoffCompositionConflict,
    ManifestHandoffCompositionKind,
    ManifestHandoffCompositionRequest,
    ManifestHandoffFacts,
    ManifestHandoffName,
    ManifestHandoffObservationConflict,
    ManifestHandoffObservationId,
    ManifestHandoffObservationKind,
    ManifestHandoffRegistryScopeId,
    ManifestHandoffReservationConflict,
    ManifestHandoffReservationId,
    ManifestHandoffScopeBinding,
    ReservedManifestHandoffAttempt,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tools.private_manifest_handoff import (
    ManifestHandoffResult,
    ManifestHandoffUnknown,
)
from tools.private_manifest_handoff_reconcile import ManifestReconciliationResult


NOW = datetime(2026, 8, 24, 18, tzinfo=timezone.utc)
SCOPE = ManifestHandoffRegistryScopeId("scope-439")
ACTOR = UserId("actor-439")
ATTEMPT = ManifestHandoffAttemptId("attempt-439")
NAME = ManifestHandoffName("handoff-439")
REQUEST = ManifestHandoffCompositionRequest(
    ManifestHandoffReservationId("reservation-439"), ACTOR, SCOPE, NAME
)
BINDING = ManifestHandoffScopeBinding(
    SCOPE, Path("/controlled/source"), Path("/private/target")
)
RESERVED = ReservedManifestHandoffAttempt(
    REQUEST.reservation_id, ATTEMPT, SCOPE, ACTOR, NAME, NOW
)
FACTS = ManifestHandoffFacts("d" * 64, 3)


class BindingLookup:
    def __init__(self, value=BINDING):
        self.value = value
        self.calls = []

    def get_binding(self, scope_id):
        self.calls.append(scope_id)
        return self.value


class Reservations:
    def __init__(self, value=RESERVED):
        self.value = value
        self.calls = []

    def reserve_attempt(self, *arguments):
        self.calls.append(arguments)
        return self.value


class Observations:
    def __init__(self):
        self.calls = []
        self.fail_started_once = False
        self.started_value = "append"
        self.sequence = 1

    def _record(self, kind, observation_id, attempt_id, facts=None):
        self.calls.append((kind, observation_id, attempt_id, facts))
        if kind is ManifestHandoffObservationKind.WRITER_STARTED:
            if self.fail_started_once:
                self.fail_started_once = False
                raise ManifestHandoffRegistryUnavailable
            if self.started_value != "append":
                return self.started_value
        self.sequence += 1
        return AppendedManifestHandoffObservation(
            observation_id, attempt_id, self.sequence, kind, NOW, facts
        )

    def record_writer_started(self, *args):
        return self._record(ManifestHandoffObservationKind.WRITER_STARTED, *args)

    def record_writer_handed_off(self, *args):
        return self._record(ManifestHandoffObservationKind.WRITER_HANDED_OFF, *args)

    def record_writer_outcome_unknown(self, *args):
        return self._record(ManifestHandoffObservationKind.WRITER_OUTCOME_UNKNOWN, *args)

    def record_manifest_absent(self, *args):
        return self._record(ManifestHandoffObservationKind.MANIFEST_ABSENT, *args)

    def record_manifest_temporary_only(self, *args):
        return self._record(ManifestHandoffObservationKind.MANIFEST_TEMPORARY_ONLY, *args)

    def record_manifest_handed_off(self, *args):
        return self._record(ManifestHandoffObservationKind.MANIFEST_HANDED_OFF, *args)

    def record_manifest_handed_off_pending_cleanup(self, *args):
        return self._record(
            ManifestHandoffObservationKind.MANIFEST_HANDED_OFF_PENDING_CLEANUP, *args
        )

    def record_manifest_handoff_conflict(self, *args):
        return self._record(ManifestHandoffObservationKind.MANIFEST_HANDOFF_CONFLICT, *args)


def subject(*, bindings=None, reservations=None, observations=None, writer=None, reconciler=None):
    ids = iter(
        ManifestHandoffObservationId(value)
        for value in ("start-439", "writer-439", "reconcile-439")
    )
    return ControlledPersistentManifestHandoff(
        bindings=bindings or BindingLookup(),
        reservations=reservations or Reservations(),
        writer_observations=observations or Observations(),
        reconciliation_observations=observations or Observations(),
        writer=writer or (
            lambda *_: ManifestHandoffResult(
                "manifest_handed_off", "handoff-439.json", "d" * 64, 3
            )
        ),
        reconciler=reconciler or (
            lambda *_: ManifestReconciliationResult("manifest_absent")
        ),
        generate_observation_id=lambda: next(ids),
    )


def test_missing_binding_is_neutral_before_reservation_or_writer() -> None:
    bindings = BindingLookup(None)
    reservations = Reservations()
    writer_calls = []
    result = subject(
        bindings=bindings,
        reservations=reservations,
        writer=lambda *args: writer_calls.append(args),
    ).handoff(REQUEST)

    assert result is None
    assert bindings.calls == [SCOPE]
    assert reservations.calls == []
    assert writer_calls == []


def test_confirmed_start_opens_exactly_one_bound_writer_and_records_success() -> None:
    observations = Observations()
    writer_calls = []

    def writer(*arguments):
        writer_calls.append(arguments)
        return ManifestHandoffResult(
            "manifest_handed_off", "handoff-439.json", "d" * 64, 3
        )

    result = subject(observations=observations, writer=writer).handoff(REQUEST)

    assert result.kind is ManifestHandoffCompositionKind.MANIFEST_HANDED_OFF
    assert result.filename == "handoff-439.json" and result.facts == FACTS
    assert writer_calls == [(BINDING.source_root, BINDING.target_root, NAME.value)]
    assert [call[0] for call in observations.calls] == [
        ManifestHandoffObservationKind.WRITER_STARTED,
        ManifestHandoffObservationKind.WRITER_HANDED_OFF,
    ]


def test_uncertain_start_retries_same_id_and_neutral_start_never_calls_writer() -> None:
    observations = Observations()
    observations.fail_started_once = True
    writer_calls = []
    subject(observations=observations, writer=lambda *a: writer_calls.append(a) or ManifestHandoffResult("source_not_stable")).handoff(REQUEST)
    assert observations.calls[0][1] == observations.calls[1][1]
    assert len(writer_calls) == 1

    denied = Observations()
    denied.started_value = None
    writer_calls.clear()
    assert subject(observations=denied, writer=lambda *a: writer_calls.append(a)).handoff(REQUEST) is None
    assert writer_calls == []


def test_reservation_and_observation_conflicts_are_detail_free() -> None:
    result = subject(
        reservations=Reservations(ManifestHandoffReservationConflict())
    ).handoff(REQUEST)
    assert type(result) is ManifestHandoffCompositionConflict

    observations = Observations()
    observations.started_value = ManifestHandoffObservationConflict()
    result = subject(observations=observations).handoff(REQUEST)
    assert type(result) is ManifestHandoffCompositionConflict


def test_unknown_writer_is_recorded_before_fresh_reconciliation() -> None:
    observations = Observations()
    events = []

    def writer(*_):
        events.append("writer")
        raise ManifestHandoffUnknown

    def reconcile(*arguments):
        events.append(("reconcile", arguments))
        return ManifestReconciliationResult(
            "manifest_handed_off", "handoff-439.json", "d" * 64, 3
        )

    result = subject(
        observations=observations, writer=writer, reconciler=reconcile
    ).handoff(REQUEST)
    assert result.kind is ManifestHandoffCompositionKind.MANIFEST_HANDED_OFF
    assert events == ["writer", ("reconcile", (BINDING.target_root, NAME.value))]
    assert [call[0] for call in observations.calls] == [
        ManifestHandoffObservationKind.WRITER_STARTED,
        ManifestHandoffObservationKind.WRITER_OUTCOME_UNKNOWN,
        ManifestHandoffObservationKind.MANIFEST_HANDED_OFF,
    ]


@pytest.mark.parametrize(
    "reconciled, expected_kind",
    (
        (ManifestReconciliationResult("manifest_absent"), ManifestHandoffObservationKind.MANIFEST_ABSENT),
        (ManifestReconciliationResult("manifest_handoff_conflict"), ManifestHandoffObservationKind.MANIFEST_HANDOFF_CONFLICT),
        (ManifestReconciliationResult("manifest_temporary_only", manifest_sha256="d" * 64, file_count=3, temporary_present=True), ManifestHandoffObservationKind.MANIFEST_TEMPORARY_ONLY),
    ),
)
def test_non_success_writer_routes_fresh_reconciliation(reconciled, expected_kind) -> None:
    observations = Observations()
    result = subject(
        observations=observations,
        writer=lambda *_: ManifestHandoffResult("target_not_absent"),
        reconciler=lambda *_: reconciled,
    ).handoff(REQUEST)
    assert result.kind is ManifestHandoffCompositionKind.RECONCILIATION_REQUIRED
    assert observations.calls[-1][0] is expected_kind


def test_malformed_direct_success_and_repeated_registry_uncertainty_fail_closed() -> None:
    with pytest.raises(ManifestHandoffCompositionUnavailable):
        subject(
            writer=lambda *_: ManifestHandoffResult(
                "manifest_handed_off", "wrong.json", "d" * 64, 3
            )
        ).handoff(REQUEST)

    class AlwaysUnavailable(Observations):
        def record_writer_started(self, *args):
            self.calls.append((ManifestHandoffObservationKind.WRITER_STARTED, *args, None))
            raise ManifestHandoffRegistryUnavailable

    calls = []
    observations = AlwaysUnavailable()
    with pytest.raises(ManifestHandoffCompositionUnavailable):
        subject(observations=observations, writer=lambda *a: calls.append(a)).handoff(REQUEST)
    assert len(observations.calls) == 2 and observations.calls[0][1] == observations.calls[1][1]
    assert calls == []


def test_inconsistent_reconciliation_temporary_flag_is_not_persisted() -> None:
    observations = Observations()
    with pytest.raises(ManifestHandoffCompositionUnavailable):
        subject(
            observations=observations,
            writer=lambda *_: ManifestHandoffResult("source_not_stable"),
            reconciler=lambda *_: ManifestReconciliationResult(
                "manifest_temporary_only",
                manifest_sha256="d" * 64,
                file_count=3,
                temporary_present=False,
            ),
        ).handoff(REQUEST)
    assert [call[0] for call in observations.calls] == [
        ManifestHandoffObservationKind.WRITER_STARTED
    ]


def test_roadmap_records_composer_and_next_slice() -> None:
    roadmap = (Path(__file__).parents[1] / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-439 controlled persistent manifest handoff composer:" in roadmap
    assert "`docs/lq-439-controlled-persistent-manifest-handoff-composer.md`" in roadmap
    assert "nächster Slice LQ-440" in roadmap
