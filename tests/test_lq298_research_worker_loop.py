from collections import deque

import pytest

from liquent_platform.application.process_research_job import (
    ResearchJobProcessingUnavailable, ResearchWorkResult, ResearchWorkResultKind,
)
from liquent_platform.identity.research import ResearchWorkerId
from liquent_platform.operators.research_worker_loop import (
    ResearchWorkerLoop, ResearchWorkerLoopPolicy,
)


POLICY = ResearchWorkerLoopPolicy(2.0, 1.0, 4.0, 0.25)


class Processor:
    def __init__(self, outcomes): self.outcomes, self.active, self.max_active, self.calls = deque(outcomes), 0, 0, 0
    def process(self, worker_id):
        assert worker_id == ResearchWorkerId("worker")
        self.calls += 1
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            outcome = self.outcomes.popleft()
            if isinstance(outcome, Exception): raise outcome
            return outcome
        finally:
            self.active -= 1


class Harness:
    def __init__(self): self.stopped, self.waits = False, []
    def stop_requested(self): return self.stopped
    def wait(self, seconds):
        self.waits.append(seconds)
        if len(self.waits) >= 3: self.stopped = True
        return self.stopped


def _loop(processor, jitter=lambda maximum: 0.0):
    return ResearchWorkerLoop(processor, ResearchWorkerId("worker"), POLICY, jitter=jitter)


def test_idle_wait_is_bounded_interruptible_and_never_busy_loops():
    processor = Processor([ResearchWorkResult(ResearchWorkResultKind.IDLE)] * 3)
    harness = Harness()
    result = _loop(processor).run(stop_requested=harness.stop_requested, wait=harness.wait)
    assert processor.calls == 3 and processor.max_active == 1
    assert harness.waits == [2.0, 2.0, 2.0]
    assert result.succeeded == result.failed == 0


def test_technical_backoff_doubles_caps_and_resets_after_healthy_result():
    outcomes = [
        ResearchJobProcessingUnavailable(), ResearchJobProcessingUnavailable(),
        ResearchJobProcessingUnavailable(), ResearchWorkResult(ResearchWorkResultKind.IDLE),
        ResearchJobProcessingUnavailable(), ResearchWorkResult(ResearchWorkResultKind.IDLE),
    ]
    processor = Processor(outcomes)
    waits, stopped = [], False
    def wait(seconds):
        nonlocal stopped
        waits.append(seconds)
        if len(waits) == 6: stopped = True
        return stopped
    result = _loop(processor).run(stop_requested=lambda: stopped, wait=wait)
    assert waits == [1.0, 2.0, 4.0, 2.0, 1.0, 2.0]
    assert result.technical_unavailability == 4
    assert processor.max_active == 1


def test_success_failure_and_claim_loss_are_counted_without_detail():
    processor = Processor([
        ResearchWorkResult(ResearchWorkResultKind.SUCCEEDED, object()),
        ResearchWorkResult(ResearchWorkResultKind.FAILED, object()),
        ResearchWorkResult(ResearchWorkResultKind.CLAIM_LOST),
    ])
    stopped = False
    def wait(_):
        nonlocal stopped
        stopped = True
        return True
    result = _loop(processor).run(stop_requested=lambda: stopped, wait=wait)
    assert (result.succeeded, result.failed, result.claims_lost) == (1, 1, 1)
    assert processor.max_active == 1


def test_stop_before_run_claims_nothing_and_wait_stop_claims_no_more():
    processor = Processor([])
    result = _loop(processor).run(stop_requested=lambda: True, wait=lambda _: False)
    assert processor.calls == 0
    assert result.technical_unavailability == 0


@pytest.mark.parametrize("jitter", [-0.1, 0.3, "bad", float("nan")])
def test_invalid_jitter_fails_closed(jitter):
    processor = Processor([ResearchWorkResult(ResearchWorkResultKind.IDLE)])
    with pytest.raises(ValueError, match="jitter is outside policy"):
        _loop(processor, jitter=lambda _: jitter).run(
            stop_requested=lambda: False, wait=lambda _: True
        )


@pytest.mark.parametrize("values", [
    (0, 1, 2, 0), (1, 0, 2, 0), (1, 2, 1, 0), (1, 1, 2, -1),
    (1, 1, float("inf"), 0),
])
def test_policy_rejects_unbounded_or_invalid_waits(values):
    with pytest.raises(ValueError):
        ResearchWorkerLoopPolicy(*values)
