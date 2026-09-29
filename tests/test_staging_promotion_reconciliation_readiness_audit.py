from pathlib import Path

import pytest

from liquent_platform.application.health import Readiness
from liquent_platform.transport import (
    staging_research_index_promotion_reconciliation_readiness_audit as audit_module,
)
from liquent_platform.transport.staging_research_index_promotion_provider_settings import (  # noqa: E501
    StagingResearchIndexPromotionProviderSettings,
)
from liquent_platform.transport.staging_research_index_promotion_reconciliation_process_settings import (  # noqa: E501
    StagingResearchIndexPromotionReconciliationProcessSettings,
)
from liquent_platform.transport.staging_research_index_promotion_reconciliation_readiness_audit import (  # noqa: E501
    StagingResearchIndexPromotionReconciliationReadiness,
    StagingResearchIndexPromotionReconciliationReadinessAuditUnavailable,
    audit_staging_research_index_promotion_reconciliation_readiness,
)


class Engine:
    def __init__(self) -> None:
        self.disposals = 0

    def dispose(self) -> None:
        self.disposals += 1


def install(monkeypatch, readiness):
    calls = []
    engine = Engine()
    process_settings = (
        StagingResearchIndexPromotionReconciliationProcessSettings.from_mapping(
            {
                "provider_settings_file": "/run/liquent/provider.env",
                "database_url": "sqlite://",
            }
        )
    )
    provider_settings = StagingResearchIndexPromotionProviderSettings.from_mapping(
        {"endpoint": "https://provider.example.test/observe/"}
    )
    monkeypatch.setattr(
        audit_module,
        "load_staging_research_index_promotion_reconciliation_process_settings",
        lambda path: calls.append(("process", path)) or process_settings,
    )
    monkeypatch.setattr(
        audit_module,
        "load_staging_research_index_promotion_provider_settings",
        lambda path: calls.append(("provider", path)) or provider_settings,
    )
    monkeypatch.setattr(
        audit_module,
        "build_engine",
        lambda url: calls.append(("build", url)) or engine,
    )

    class Probe:
        def __init__(self, supplied):
            calls.append(("probe", supplied))

        def check(self):
            calls.append(("check",))
            return readiness

    monkeypatch.setattr(audit_module, "DatabaseReadinessProbe", Probe)
    return calls, engine


def test_ready_audit_validates_both_settings_and_disposes_engine(monkeypatch) -> None:
    calls, engine = install(monkeypatch, Readiness(True, "database_ready"))
    path = Path("/run/liquent/reconciliation.env")
    assert (
        audit_staging_research_index_promotion_reconciliation_readiness(path)
        is StagingResearchIndexPromotionReconciliationReadiness.READY
    )
    assert calls[:3] == [
        ("process", path),
        ("provider", Path("/run/liquent/provider.env")),
        ("build", "sqlite://"),
    ]
    assert engine.disposals == 1


@pytest.mark.parametrize(
    "readiness",
    [
        Readiness(False, "database_unavailable"),
        Readiness(False, "schema_revision_mismatch"),
    ],
)
def test_unready_database_fails_closed_and_disposes(monkeypatch, readiness) -> None:
    _calls, engine = install(monkeypatch, readiness)
    with pytest.raises(
        StagingResearchIndexPromotionReconciliationReadinessAuditUnavailable
    ) as caught:
        audit_staging_research_index_promotion_reconciliation_readiness(
            Path("/run/liquent/reconciliation.env")
        )
    assert engine.disposals == 1
    assert caught.value.__cause__ is None and caught.value.__context__ is None


def test_provider_settings_failure_prevents_engine_creation(monkeypatch) -> None:
    calls, _engine = install(monkeypatch, Readiness(True, "database_ready"))

    def unavailable(path):
        calls.append(("provider_failure", path))
        raise RuntimeError("provider endpoint detail")

    monkeypatch.setattr(
        audit_module,
        "load_staging_research_index_promotion_provider_settings",
        unavailable,
    )
    with pytest.raises(
        StagingResearchIndexPromotionReconciliationReadinessAuditUnavailable
    ):
        audit_staging_research_index_promotion_reconciliation_readiness(
            Path("/run/liquent/reconciliation.env")
        )
    assert not any(call[0] == "build" for call in calls)


def test_audit_has_no_reconciliation_or_provider_transport_authority() -> None:
    source = Path(audit_module.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "run_one_staging_research_index_promotion_reconciliation",
        "requests.",
        "httpx.",
        "retry",
        "sleep(",
        "create_all",
        "upgrade_to_head",
    ):
        assert forbidden not in source
