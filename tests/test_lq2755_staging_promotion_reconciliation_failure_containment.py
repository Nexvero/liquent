from pathlib import Path

import httpx2
import pytest

from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.staging_research_index_promotion_attempt_journal import (  # noqa: E501
    DatabaseStagingResearchIndexPromotionAttemptJournal,
)
from liquent_platform.persistence.staging_research_index_promotion_unknown_index import (  # noqa: E501
    DatabaseStagingResearchIndexPromotionUnknownIndex,
)
from liquent_platform.transport import (
    staging_research_index_promotion_provider_lifecycle as lifecycle_module,
)
from liquent_platform.transport import (
    staging_research_index_promotion_reconciliation_candidate_audit_cli as candidate_cli,
)
from liquent_platform.transport import (
    staging_research_index_promotion_reconciliation_cli as reconciliation_cli,
)
from liquent_platform.transport import (
    staging_research_index_promotion_reconciliation_readiness_audit_cli as readiness_cli,
)
from liquent_platform.transport import (
    staging_research_index_promotion_reconciliation_settings_installation_cli as installation_cli,
)
from tests.test_lq2754_staging_promotion_reconciliation_operator_rehearsal import (
    _run,
    _write_private,
)
from tests.test_staging_research_index_promotion_attempt_journal import NOW, _attempt


def _prepare(tmp_path: Path):
    source_directory = tmp_path / "source"
    target_directory = tmp_path / "installed"
    source_directory.mkdir(mode=0o700)
    target_directory.mkdir(mode=0o700)
    provider_target = target_directory / "provider.env"
    process_target = target_directory / "process.env"

    database = tmp_path / "reconciliation.db"
    database_url = f"sqlite+pysqlite:///{database}"
    engine = build_engine(database_url)
    upgrade_to_head(str(engine.url))
    prepared = _attempt(operation="promotion-lq2755-private")
    journal = DatabaseStagingResearchIndexPromotionAttemptJournal(engine)
    journal.record_prepared(prepared, observed_at=NOW)
    started = journal.mark_write_started(prepared, observed_at=NOW)
    journal.record_unknown(started, observed_at=NOW)
    engine.dispose()

    provider_source = _write_private(
        source_directory / "provider.env",
        "LIQUENT_STAGING_PROMOTION_PROVIDER_ENDPOINT="
        "https://provider.example/status/\n",
    )
    process_source = _write_private(
        source_directory / "process.env",
        "LIQUENT_STAGING_PROMOTION_RECONCILIATION_PROVIDER_SETTINGS_FILE="
        f"{provider_target}\n"
        "LIQUENT_STAGING_PROMOTION_RECONCILIATION_DATABASE_URL="
        f"{database_url}\n",
    )
    installed = _run(
        installation_cli,
        provider_source,
        provider_target,
        process_source,
        process_target,
    )
    assert installed == (0, "installed\n", "")
    return process_target, database_url, prepared.operation_id


@pytest.mark.parametrize(
    "status,content_type,body,private_detail",
    [
        (
            503,
            "application/json",
            b'{"detail":"provider-password-private"}',
            "provider-password-private",
        ),
        (
            200,
            "application/json",
            b'{"operation_id":"malformed-private"',
            "malformed-private",
        ),
    ],
)
def test_provider_failure_is_detail_free_and_preserves_the_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    content_type: str,
    body: bytes,
    private_detail: str,
) -> None:
    process, database_url, operation_id = _prepare(tmp_path)
    requests = []

    def handler(request):
        requests.append(request)
        return httpx2.Response(
            status,
            headers={"content-type": content_type},
            content=iter([body]),
        )

    monkeypatch.setattr(
        lifecycle_module,
        "_create_client",
        lambda: httpx2.Client(
            transport=httpx2.MockTransport(handler), trust_env=False
        ),
    )

    ready = _run(readiness_cli, process)
    before = _run(candidate_cli, process)
    unavailable = _run(reconciliation_cli, process)
    after = _run(candidate_cli, process)

    assert ready == (0, "ready\n", "")
    assert before == (0, "pending\n", "")
    assert unavailable == (1, "", "unavailable\n")
    assert after == (0, "pending\n", "")
    assert len(requests) == 1
    presentation = "".join(
        value
        for result in (ready, before, unavailable, after)
        for value in result[1:]
    )
    assert operation_id not in presentation
    assert private_detail not in presentation

    engine = build_engine(database_url)
    try:
        assert DatabaseStagingResearchIndexPromotionUnknownIndex(
            engine
        ).list_unknown_operation_ids() == (operation_id,)
    finally:
        engine.dispose()


def test_completion_document_records_closed_failure_containment() -> None:
    root = Path(__file__).parents[1]
    document = (
        root
        / "docs/lq-2755-staging-promotion-reconciliation-failure-containment.md"
    ).read_text(encoding="utf-8")
    for phrase in (
        "`ready` → `pending` → `unavailable` → `pending`",
        "exactly one provider request",
        "malformed provider response",
        "provider HTTP failure",
        "no durable reconciliation",
        "no automatic retry authority",
    ):
        assert phrase in document
