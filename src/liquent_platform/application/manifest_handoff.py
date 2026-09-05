"""Controlled persistent composition for one private manifest handoff."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from liquent_platform.identity.manifest_handoff import (
    AppendedManifestHandoffObservation,
    ManifestHandoffCompositionConflict,
    ManifestHandoffCompositionKind,
    ManifestHandoffCompositionRequest,
    ManifestHandoffCompositionResult,
    ManifestHandoffFacts,
    ManifestHandoffObservationConflict,
    ManifestHandoffObservationId,
    ManifestHandoffObservationKind,
    ManifestHandoffReservationConflict,
    ReservedManifestHandoffAttempt,
)
from liquent_platform.identity.ports import (
    AuthorizedManifestHandoffAttemptReservation,
    ControlledManifestHandoffReconciliationObservationAppend,
    ControlledManifestHandoffWriterObservationAppend,
    ManifestHandoffScopeBindingLookup,
)
from liquent_platform.persistence.identity_errors import (
    ManifestHandoffRegistryUnavailable,
)
from liquent_platform.capabilities.private_manifest_handoff import (
    ManifestHandoffResult,
    ManifestHandoffUnavailable,
    ManifestHandoffUnknown,
)
from liquent_platform.capabilities.private_manifest_handoff_reconcile import (
    ManifestReconciliationResult,
    ManifestReconciliationUnavailable,
)


class ManifestHandoffCompositionUnavailable(Exception):
    code = "manifest_handoff_composition_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class ControlledPersistentManifestHandoff:
    """Reserve, durably start, execute once, and preserve the direct outcome."""

    __slots__ = (
        "_bindings",
        "_reservations",
        "_writer_observations",
        "_reconciliation_observations",
        "_writer",
        "_reconciler",
        "_observation_id",
    )

    def __init__(
        self,
        *,
        bindings: ManifestHandoffScopeBindingLookup,
        reservations: AuthorizedManifestHandoffAttemptReservation,
        writer_observations: ControlledManifestHandoffWriterObservationAppend,
        reconciliation_observations: ControlledManifestHandoffReconciliationObservationAppend,
        writer: Callable[[Path, Path, str], ManifestHandoffResult],
        reconciler: Callable[[Path, str], ManifestReconciliationResult],
        generate_observation_id: Callable[[], ManifestHandoffObservationId],
    ) -> None:
        self._bindings = bindings
        self._reservations = reservations
        self._writer_observations = writer_observations
        self._reconciliation_observations = reconciliation_observations
        self._writer = writer
        self._reconciler = reconciler
        self._observation_id = generate_observation_id

    def __repr__(self) -> str:
        return "ControlledPersistentManifestHandoff()"

    def handoff(
        self, request: ManifestHandoffCompositionRequest
    ) -> ManifestHandoffCompositionResult | ManifestHandoffCompositionConflict | None:
        try:
            if type(request) is not ManifestHandoffCompositionRequest:
                raise ManifestHandoffCompositionUnavailable
            binding = self._bindings.get_binding(request.scope_id)
            if binding is None:
                return None
            if binding.scope_id != request.scope_id:
                raise ManifestHandoffCompositionUnavailable
            reserved = self._reservations.reserve_attempt(
                request.reservation_id,
                request.actor_user_id,
                request.scope_id,
                request.handoff_name,
            )
            if reserved is None:
                return None
            if type(reserved) is ManifestHandoffReservationConflict:
                return ManifestHandoffCompositionConflict()
            if type(reserved) is not ReservedManifestHandoffAttempt:
                raise ManifestHandoffCompositionUnavailable
            if (
                reserved.reservation_id != request.reservation_id
                or reserved.scope_id != request.scope_id
                or reserved.actor_user_id != request.actor_user_id
                or reserved.handoff_name != request.handoff_name
            ):
                raise ManifestHandoffCompositionUnavailable

            started = self._append(
                self._writer_observations.record_writer_started,
                reserved.attempt_id,
                ManifestHandoffObservationKind.WRITER_STARTED,
            )
            if started is None:
                return None
            if type(started) is ManifestHandoffObservationConflict:
                return ManifestHandoffCompositionConflict()

            return self._run_writer(binding, reserved)
        except ManifestHandoffCompositionUnavailable:
            raise
        except Exception:
            raise ManifestHandoffCompositionUnavailable from None

    def _run_writer(self, binding, reserved):
        reconcile = False
        try:
            result = self._writer(
                binding.source_root,
                binding.target_root,
                reserved.handoff_name.value,
            )
        except ManifestHandoffUnknown:
            recorded = self._append(
                self._writer_observations.record_writer_outcome_unknown,
                reserved.attempt_id,
                ManifestHandoffObservationKind.WRITER_OUTCOME_UNKNOWN,
            )
            conflict = self._outcome_append(recorded)
            if conflict is not None:
                return conflict
            reconcile = True
        except ManifestHandoffUnavailable:
            reconcile = True
        else:
            if type(result) is not ManifestHandoffResult:
                raise ManifestHandoffCompositionUnavailable
            if result.outcome == "manifest_handed_off":
                expected = reserved.handoff_name.value + ".json"
                if result.filename != expected:
                    raise ManifestHandoffCompositionUnavailable
                try:
                    facts = ManifestHandoffFacts(
                        result.manifest_sha256, result.file_count
                    )
                except (TypeError, ValueError):
                    raise ManifestHandoffCompositionUnavailable from None
                recorded = self._append(
                    self._writer_observations.record_writer_handed_off,
                    reserved.attempt_id,
                    ManifestHandoffObservationKind.WRITER_HANDED_OFF,
                    facts,
                )
                conflict = self._outcome_append(recorded)
                if conflict is not None:
                    return conflict
                return ManifestHandoffCompositionResult(
                    reserved.attempt_id,
                    ManifestHandoffCompositionKind.MANIFEST_HANDED_OFF,
                    expected,
                    facts,
                )
            if result.outcome not in {"target_not_absent", "source_not_stable"}:
                raise ManifestHandoffCompositionUnavailable
            if any(
                value is not None
                for value in (result.filename, result.manifest_sha256, result.file_count)
            ):
                raise ManifestHandoffCompositionUnavailable
            reconcile = True
        if not reconcile:
            raise ManifestHandoffCompositionUnavailable
        return self._reconcile(binding, reserved)

    def _reconcile(self, binding, reserved):
        try:
            result = self._reconciler(
                binding.target_root, reserved.handoff_name.value
            )
        except ManifestReconciliationUnavailable:
            raise ManifestHandoffCompositionUnavailable from None
        if type(result) is not ManifestReconciliationResult:
            raise ManifestHandoffCompositionUnavailable

        outcome = result.outcome
        temporary_expected = outcome in {
            "manifest_temporary_only",
            "manifest_handed_off_pending_cleanup",
        }
        if type(result.temporary_present) is not bool or (
            result.temporary_present is not temporary_expected
        ):
            raise ManifestHandoffCompositionUnavailable
        facts = None
        factual = {
            "manifest_temporary_only",
            "manifest_handed_off",
            "manifest_handed_off_pending_cleanup",
        }
        if outcome in factual:
            try:
                facts = ManifestHandoffFacts(
                    result.manifest_sha256, result.file_count
                )
            except (TypeError, ValueError):
                raise ManifestHandoffCompositionUnavailable from None
        elif result.manifest_sha256 is not None or result.file_count is not None:
            raise ManifestHandoffCompositionUnavailable

        expected = reserved.handoff_name.value + ".json"
        if outcome in {"manifest_handed_off", "manifest_handed_off_pending_cleanup"}:
            if result.filename != expected:
                raise ManifestHandoffCompositionUnavailable
        elif result.filename is not None:
            raise ManifestHandoffCompositionUnavailable

        methods = {
            "manifest_absent": self._reconciliation_observations.record_manifest_absent,
            "manifest_temporary_only": self._reconciliation_observations.record_manifest_temporary_only,
            "manifest_handed_off": self._reconciliation_observations.record_manifest_handed_off,
            "manifest_handed_off_pending_cleanup": self._reconciliation_observations.record_manifest_handed_off_pending_cleanup,
            "manifest_handoff_conflict": self._reconciliation_observations.record_manifest_handoff_conflict,
        }
        kinds = {
            value.value: value
            for value in (
                ManifestHandoffObservationKind.MANIFEST_ABSENT,
                ManifestHandoffObservationKind.MANIFEST_TEMPORARY_ONLY,
                ManifestHandoffObservationKind.MANIFEST_HANDED_OFF,
                ManifestHandoffObservationKind.MANIFEST_HANDED_OFF_PENDING_CLEANUP,
                ManifestHandoffObservationKind.MANIFEST_HANDOFF_CONFLICT,
            )
        }
        if outcome not in methods:
            raise ManifestHandoffCompositionUnavailable
        recorded = self._append(
            methods[outcome], reserved.attempt_id, kinds[outcome], facts
        )
        conflict = self._outcome_append(recorded)
        if conflict is not None:
            return conflict
        if outcome in {"manifest_handed_off", "manifest_handed_off_pending_cleanup"}:
            return ManifestHandoffCompositionResult(
                reserved.attempt_id,
                ManifestHandoffCompositionKind.MANIFEST_HANDED_OFF,
                expected,
                facts,
            )
        return ManifestHandoffCompositionResult(
            reserved.attempt_id,
            ManifestHandoffCompositionKind.RECONCILIATION_REQUIRED,
        )

    def _append(self, method, attempt_id, kind, facts=None):
        observation_id = self._new_observation_id()
        arguments = (observation_id, attempt_id)
        if facts is not None:
            arguments += (facts,)
        for index in range(2):
            try:
                result = method(*arguments)
                break
            except ManifestHandoffRegistryUnavailable:
                if index:
                    raise ManifestHandoffCompositionUnavailable from None
        if type(result) is ManifestHandoffObservationConflict or result is None:
            return result
        if (
            type(result) is not AppendedManifestHandoffObservation
            or result.observation_id != observation_id
            or result.attempt_id != attempt_id
            or result.kind is not kind
            or result.facts != facts
        ):
            raise ManifestHandoffCompositionUnavailable
        return result

    def _new_observation_id(self) -> ManifestHandoffObservationId:
        try:
            value = self._observation_id()
        except Exception:
            raise ManifestHandoffCompositionUnavailable from None
        if type(value) is not ManifestHandoffObservationId:
            raise ManifestHandoffCompositionUnavailable
        return value

    @staticmethod
    def _outcome_append(result):
        if result is None:
            raise ManifestHandoffCompositionUnavailable
        if type(result) is ManifestHandoffObservationConflict:
            return ManifestHandoffCompositionConflict()
        return None
