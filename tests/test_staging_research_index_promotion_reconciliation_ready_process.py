from pathlib import Path

import pytest

from liquent_platform.application.health import Readiness
from liquent_platform.transport import (
    staging_research_index_promotion_reconciliation_ready_process as process_module,
)
from liquent_platform.transport.staging_research_index_promotion_reconciliation_process_settings import (  # noqa: E501
    StagingResearchIndexPromotionReconciliationProcessSettings,
)
from liquent_platform.transport.staging_research_index_promotion_reconciliation_ready_process import (  # noqa: E501
    StagingResearchIndexPromotionReconciliationReadyProcessUnavailable,
    run_ready_staging_research_index_promotion_reconciliation_process,
)
from tests.test_staging_research_index_promotion_attempt_journal import _receipt
from tests.test_staging_research_index_promotion_reconciliation import _unknown


class Engine:
    def __init__(self):
        self.disposals = 0

    def dispose(self):
        self.disposals += 1


def install(monkeypatch, readiness, result=None):
    calls = []
    engine = Engine()
    settings = StagingResearchIndexPromotionReconciliationProcessSettings.from_mapping(
        {
            "provider_settings_file": "/run/liquent/provider.env",
            "database_url": "sqlite://",
        }
    )
    monkeypatch.setattr(
        process_module,
        "load_staging_research_index_promotion_reconciliation_process_settings",
        lambda path: calls.append(("load", path)) or settings,
    )
    monkeypatch.setattr(
        process_module, "build_engine", lambda url: calls.append(("build", url)) or engine
    )

    class Probe:
        def __init__(self, supplied):
            calls.append(("probe", supplied))

        def check(self):
            calls.append(("check",))
            return readiness

    monkeypatch.setattr(process_module, "DatabaseReadinessProbe", Probe)
    monkeypatch.setattr(
        process_module,
        "run_one_staging_research_index_promotion_reconciliation",
        lambda path, supplied: calls.append(("run", path, supplied)) or result,
    )
    return calls, engine


def test_ready_database_executes_once_and_disposes(monkeypatch) -> None:
    receipt = _receipt(_unknown().attempt.prepared)
    calls, engine = install(monkeypatch, Readiness(True, "database_ready"), receipt)
    path = Path("/run/liquent/reconciliation.env")
    assert run_ready_staging_research_index_promotion_reconciliation_process(path) is receipt
    assert calls[-1] == ("run", Path("/run/liquent/provider.env"), engine)
    assert engine.disposals == 1


@pytest.mark.parametrize(
    "readiness",
    [Readiness(False, "database_unavailable"), Readiness(False, "schema_revision_mismatch")],
)
def test_unready_database_fails_closed_without_execution(monkeypatch, readiness) -> None:
    calls, engine = install(monkeypatch, readiness)
    with pytest.raises(
        StagingResearchIndexPromotionReconciliationReadyProcessUnavailable
    ) as caught:
        run_ready_staging_research_index_promotion_reconciliation_process(
            Path("/run/liquent/reconciliation.env")
        )
    assert not any(call[0] == "run" for call in calls)
    assert engine.disposals == 1
    assert caught.value.__cause__ is None and caught.value.__context__ is None


def test_malformed_readiness_fails_closed_without_execution(monkeypatch) -> None:
    calls, engine = install(monkeypatch, object())
    with pytest.raises(StagingResearchIndexPromotionReconciliationReadyProcessUnavailable):
        run_ready_staging_research_index_promotion_reconciliation_process(
            Path("/run/liquent/reconciliation.env")
        )
    assert not any(call[0] == "run" for call in calls)
    assert engine.disposals == 1


def test_ready_process_does_not_migrate_bootstrap_or_retry() -> None:
    source = Path(process_module.__file__).read_text()
    for forbidden in ("upgrade_to_head", "create_all", "bootstrap", "retry", "sleep("):
        assert forbidden not in source
