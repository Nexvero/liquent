"""Provider-neutral orchestration of one bounded publication work unit."""

from __future__ import annotations

from liquent_platform.identity.ports import (
    ReleasePublicationAttemptPreflight,
    ReleasePublicationCurrentOutcomeFinalizer,
    ReleasePublicationImmutableCreate,
    ReleasePublicationRetryAttemptPreflight,
    ReleasePublicationRetryImmutableCreate,
    ReleasePublicationWorkStateLookup,
)
from liquent_platform.identity.release_publication import (
    FinalizedReleasePublication,
    FinalizedReleasePublicationRecovery,
    PreparedReleasePublicationAttempt,
    ReleasePublicationFinalStatus,
    ReleasePublicationReconciliationKind,
    ReleasePublicationWorkRequest,
    ReleasePublicationWorkResult,
    ReleasePublicationWorkResultKind,
    ReleasePublicationWorkState,
    ReleasePublicationWorkStateKind,
    ReleasePublicationWritePendingReconciliation,
)


class ReleasePublicationWorkUnavailable(Exception):
    code = "release_publication_work_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class ProcessReleasePublicationWork:
    """Advance one system-of-record-bound execution with at most one create."""

    __slots__ = (
        "_states", "_attempt_one", "_create_one", "_attempt_two",
        "_create_two", "_finalize",
    )

    def __init__(
        self,
        *,
        states: ReleasePublicationWorkStateLookup,
        attempt_one: ReleasePublicationAttemptPreflight,
        create_one: ReleasePublicationImmutableCreate,
        attempt_two: ReleasePublicationRetryAttemptPreflight,
        create_two: ReleasePublicationRetryImmutableCreate,
        finalizer: ReleasePublicationCurrentOutcomeFinalizer,
    ) -> None:
        self._states = states
        self._attempt_one = attempt_one
        self._create_one = create_one
        self._attempt_two = attempt_two
        self._create_two = create_two
        self._finalize = finalizer

    def __repr__(self) -> str:
        return "ProcessReleasePublicationWork()"

    def process(
        self, request: ReleasePublicationWorkRequest
    ) -> ReleasePublicationWorkResult:
        try:
            if type(request) is not ReleasePublicationWorkRequest:
                raise ReleasePublicationWorkUnavailable
            state = self._states.get_work_state(request)
            if state is None:
                return self._initial(request)
            if type(state) is not ReleasePublicationWorkState:
                raise ReleasePublicationWorkUnavailable
            return self._current(request, state)
        except ReleasePublicationWorkUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise ReleasePublicationWorkUnavailable

    def _initial(self, request):
        prepared = self._attempt_one.prepare_attempt(
            request.execution_id,
            request.handoff_id,
            request.publisher_authority_id,
            request.channel_id,
            request.expected_channel_revision,
        )
        if prepared is None:
            return self._result(ReleasePublicationWorkResultKind.NOT_ACTIONABLE)
        self._prepared(prepared, 1)
        return self._create_and_finalize(prepared, 1)

    def _current(self, request, state):
        if state.kind is ReleasePublicationWorkStateKind.NOT_ACTIONABLE:
            return self._result(ReleasePublicationWorkResultKind.NOT_ACTIONABLE)
        if state.kind is ReleasePublicationWorkStateKind.TERMINAL:
            return self._result(state.terminal_result)
        attempt_id = state.attempt_id
        if attempt_id is None:
            raise ReleasePublicationWorkUnavailable
        if state.kind is ReleasePublicationWorkStateKind.ATTEMPT_ONE_PREPARED:
            prepared = PreparedReleasePublicationAttempt(
                request.execution_id, attempt_id, request.handoff_id, 1
            )
            return self._create_and_finalize(prepared, 1)
        if state.kind is ReleasePublicationWorkStateKind.ATTEMPT_ONE_UNKNOWN:
            return self._finalize_current(request.execution_id, attempt_id, 1)
        if state.kind is ReleasePublicationWorkStateKind.ATTEMPT_ONE_ABSENCE_RECOVERED:
            prepared = self._attempt_two.prepare_retry_attempt(
                request.execution_id, attempt_id
            )
            if prepared is None:
                return self._result(ReleasePublicationWorkResultKind.NOT_ACTIONABLE)
            self._prepared(prepared, 2)
            return self._create_and_finalize(prepared, 2)
        if state.kind is ReleasePublicationWorkStateKind.ATTEMPT_TWO_PREPARED:
            prepared = PreparedReleasePublicationAttempt(
                request.execution_id, attempt_id, request.handoff_id, 2
            )
            return self._create_and_finalize(prepared, 2)
        if state.kind is ReleasePublicationWorkStateKind.ATTEMPT_TWO_UNKNOWN:
            return self._finalize_current(request.execution_id, attempt_id, 2)
        raise ReleasePublicationWorkUnavailable

    def _create_and_finalize(self, prepared, attempt_number):
        pending = (
            self._create_one.create_publication(
                prepared.execution_id, prepared.attempt_id
            )
            if attempt_number == 1
            else self._create_two.create_retry_publication(
                prepared.execution_id, prepared.attempt_id
            )
        )
        if pending is None:
            return self._result(ReleasePublicationWorkResultKind.NOT_ACTIONABLE)
        if type(pending) is not ReleasePublicationWritePendingReconciliation:
            raise ReleasePublicationWorkUnavailable
        if (
            pending.execution_id != prepared.execution_id
            or pending.attempt_id != prepared.attempt_id
            or pending.handoff_id != prepared.handoff_id
        ):
            raise ReleasePublicationWorkUnavailable
        return self._finalize_current(
            prepared.execution_id, prepared.attempt_id, attempt_number
        )

    def _finalize_current(self, execution_id, attempt_id, attempt_number):
        finalized = self._finalize.finalize_current_outcome(execution_id, attempt_id)
        if finalized is None:
            return self._result(
                ReleasePublicationWorkResultKind.PENDING_RECONCILIATION
            )
        if type(finalized) is FinalizedReleasePublication:
            kind = (
                ReleasePublicationWorkResultKind.PUBLISHED
                if finalized.status is ReleasePublicationFinalStatus.PUBLISHED
                else ReleasePublicationWorkResultKind.PUBLISHED_REASSESSMENT_REQUIRED
            )
            return self._result(kind)
        if type(finalized) is FinalizedReleasePublicationRecovery:
            if finalized.kind is ReleasePublicationReconciliationKind.CONFLICT:
                return self._result(
                    ReleasePublicationWorkResultKind.PUBLICATION_CONFLICT
                )
            return self._result(
                ReleasePublicationWorkResultKind.NOT_ACTIONABLE
                if attempt_number == 1 and finalized.retry_eligible
                else ReleasePublicationWorkResultKind.NOT_PUBLISHED
            )
        raise ReleasePublicationWorkUnavailable

    @staticmethod
    def _prepared(value, number):
        if (
            type(value) is not PreparedReleasePublicationAttempt
            or value.attempt_number != number
        ):
            raise ReleasePublicationWorkUnavailable

    @staticmethod
    def _result(kind):
        if type(kind) is not ReleasePublicationWorkResultKind:
            raise ReleasePublicationWorkUnavailable
        return ReleasePublicationWorkResult(kind)
