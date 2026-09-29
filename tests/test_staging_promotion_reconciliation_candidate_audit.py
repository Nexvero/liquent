from pathlib import Path

import pytest

from liquent_platform.application.health import Readiness
from liquent_platform.transport import (
    staging_research_index_promotion_reconciliation_candidate_audit as audit_module,
)
from liquent_platform.transport.staging_research_index_promotion_provider_settings import (  # noqa: E501
    StagingResearchIndexPromotionProviderSettings,
)
from liquent_platform.transport.staging_research_index_promotion_reconciliation_candidate_audit import (  # noqa: E501
    StagingResearchIndexPromotionReconciliationCandidateAudit,
    StagingResearchIndexPromotionReconciliationCandidateAuditUnavailable,
    audit_staging_research_index_promotion_reconciliation_candidate,
)
from liquent_platform.transport.staging_research_index_promotion_reconciliation_process_settings import (  # noqa: E501
    StagingResearchIndexPromotionReconciliationProcessSettings,
)


class Engine:
    def __init__(self) -> None:
        self.disposals = 0

    def dispose(self) -> None:
        self.disposals += 1


def install(monkeypatch, *, readiness=Readiness(True, "database_ready"), candidate=None):
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

    class Index:
        def __init__(self, supplied):
            calls.append(("index", supplied))

    monkeypatch.setattr(audit_module, "DatabaseReadinessProbe", Probe)
    monkeypatch.setattr(
        audit_module, "DatabaseStagingResearchIndexPromotionUnknownIndex", Index
    )
    monkeypatch.setattr(
        audit_module,
        "select_staging_research_index_promotion_reconciliation_candidate",
        lambda index: calls.append(("select", index)) or candidate,
    )
    return calls, engine


@pytest.mark.parametrize(
    ("candidate", "expected"),
    [
        ("promotion-private", StagingResearchIndexPromotionReconciliationCandidateAudit.PENDING),
        (None, StagingResearchIndexPromotionReconciliationCandidateAudit.IDLE),
    ],
)
def test_audit_reports_only_candidate_presence_and_disposes(
    monkeypatch, candidate, expected
) -> None:
    calls, engine = install(monkeypatch, candidate=candidate)
    path = Path("/run/liquent/reconciliation.env")
    assert (
        audit_staging_research_index_promotion_reconciliation_candidate(path)
        is expected
    )
    assert calls[:3] == [
        ("process", path),
        ("provider", Path("/run/liquent/provider.env")),
        ("build", "sqlite://"),
    ]
    assert len([call for call in calls if call[0] == "check"]) == 1
    assert len([call for call in calls if call[0] == "select"]) == 1
    assert engine.disposals == 1


def test_unready_database_prevents_index_read_and_disposes(monkeypatch) -> None:
    calls, engine = install(
        monkeypatch, readiness=Readiness(False, "schema_revision_mismatch")
    )
    with pytest.raises(
        StagingResearchIndexPromotionReconciliationCandidateAuditUnavailable
    ) as caught:
        audit_staging_research_index_promotion_reconciliation_candidate(
            Path("/run/liquent/reconciliation.env")
        )
    assert not any(call[0] in {"index", "select"} for call in calls)
    assert engine.disposals == 1
    assert caught.value.__cause__ is None and caught.value.__context__ is None


def test_selection_failure_is_detail_free_and_disposes(monkeypatch) -> None:
    _calls, engine = install(monkeypatch)

    def unavailable(_index):
        raise RuntimeError("private operation identity")

    monkeypatch.setattr(
        audit_module,
        "select_staging_research_index_promotion_reconciliation_candidate",
        unavailable,
    )
    with pytest.raises(
        StagingResearchIndexPromotionReconciliationCandidateAuditUnavailable
    ) as caught:
        audit_staging_research_index_promotion_reconciliation_candidate(
            Path("/run/liquent/reconciliation.env")
        )
    assert "private operation identity" not in str(caught.value)
    assert caught.value.__cause__ is None and caught.value.__context__ is None
    assert engine.disposals == 1


def test_audit_has_no_reconciliation_provider_transport_or_mutation_authority() -> None:
    source = Path(audit_module.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "run_one_staging_research_index_promotion_reconciliation",
        "requests.",
        "httpx.",
        "record_",
        "mark_",
        "retry",
        "sleep(",
        "create_all",
        "upgrade_to_head",
    ):
        assert forbidden not in source
