from pathlib import Path

import pytest

from liquent_platform.transport import (
    staging_research_index_promotion_reconciliation_process as process_module,
)
from liquent_platform.transport.staging_research_index_promotion_reconciliation_process import (  # noqa: E501
    StagingResearchIndexPromotionReconciliationProcessUnavailable,
    run_staging_research_index_promotion_reconciliation_process,
)
from liquent_platform.transport.staging_research_index_promotion_reconciliation_process_settings import (  # noqa: E501
    StagingResearchIndexPromotionReconciliationProcessSettings,
)
from tests.test_staging_research_index_promotion_attempt_journal import _receipt
from tests.test_staging_research_index_promotion_reconciliation import _unknown


class Engine:
    def __init__(self, dispose_error=None):
        self.dispose_error = dispose_error
        self.disposals = 0

    def dispose(self):
        self.disposals += 1
        if self.dispose_error is not None:
            raise self.dispose_error


def install(monkeypatch, *, result=None, run_error=None):
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
        process_module,
        "build_engine",
        lambda url: calls.append(("build", url)) or engine,
    )

    def run(path, supplied_engine):
        calls.append(("run", path, supplied_engine))
        if run_error is not None:
            raise run_error
        return result

    monkeypatch.setattr(
        process_module, "run_one_staging_research_index_promotion_reconciliation", run
    )
    return calls, engine


def test_process_loads_builds_executes_once_and_disposes(monkeypatch) -> None:
    receipt = _receipt(_unknown().attempt.prepared)
    calls, engine = install(monkeypatch, result=receipt)
    path = Path("/run/liquent/reconciliation.env")
    assert run_staging_research_index_promotion_reconciliation_process(path) is receipt
    assert calls == [
        ("load", path),
        ("build", "sqlite://"),
        ("run", Path("/run/liquent/provider.env"), engine),
    ]
    assert engine.disposals == 1


def test_neutral_absence_disposes_engine(monkeypatch) -> None:
    _, engine = install(monkeypatch, result=None)
    assert run_staging_research_index_promotion_reconciliation_process(
        Path("/run/liquent/reconciliation.env")
    ) is None
    assert engine.disposals == 1


def test_execution_failure_is_detail_free_and_disposes_engine(monkeypatch) -> None:
    _, engine = install(monkeypatch, run_error=RuntimeError("database detail"))
    with pytest.raises(StagingResearchIndexPromotionReconciliationProcessUnavailable) as caught:
        run_staging_research_index_promotion_reconciliation_process(
            Path("/run/liquent/reconciliation.env")
        )
    assert engine.disposals == 1
    assert caught.value.__cause__ is None and caught.value.__context__ is None
    assert "database detail" not in str(caught.value)


def test_settings_failure_never_builds_or_runs(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(
        process_module,
        "load_staging_research_index_promotion_reconciliation_process_settings",
        lambda _: (_ for _ in ()).throw(RuntimeError("settings detail")),
    )
    monkeypatch.setattr(process_module, "build_engine", lambda _: calls.append("build"))
    with pytest.raises(StagingResearchIndexPromotionReconciliationProcessUnavailable):
        run_staging_research_index_promotion_reconciliation_process(
            Path("/run/liquent/reconciliation.env")
        )
    assert calls == []


def test_process_has_no_migration_bootstrap_loop_or_retry_surface() -> None:
    source = Path(process_module.__file__).read_text()
    for forbidden in (
        "upgrade_to_head",
        "create_all",
        "bootstrap",
        "while True",
        "sleep(",
        "retry",
    ):
        assert forbidden not in source
