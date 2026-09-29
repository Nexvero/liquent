import json
from pathlib import Path

import httpx2
import pytest
from sqlalchemy import Engine

from liquent_platform.persistence.database import build_engine
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
from tests.test_staging_research_index_promotion_provider_composition import _payload


pytestmark = pytest.mark.postgres_integration


def test_postgresql_operator_chain_reconciles_one_exact_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    postgres_engine: Engine,
    postgres_url: str,
) -> None:
    source_directory = tmp_path / "source"
    target_directory = tmp_path / "installed"
    source_directory.mkdir(mode=0o700)
    target_directory.mkdir(mode=0o700)
    provider_target = target_directory / "provider.env"
    process_target = target_directory / "process.env"

    prepared = _attempt(operation="promotion-lq2759-private")
    journal = DatabaseStagingResearchIndexPromotionAttemptJournal(postgres_engine)
    journal.record_prepared(prepared, observed_at=NOW)
    started = journal.mark_write_started(prepared, observed_at=NOW)
    unknown = journal.record_unknown(started, observed_at=NOW)

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
        f"{postgres_url}\n",
    )

    requests = []

    def handler(request):
        requests.append(request)
        return httpx2.Response(
            200,
            headers={"content-type": "application/json"},
            content=iter([json.dumps(_payload(unknown)).encode()]),
        )

    monkeypatch.setattr(
        lifecycle_module,
        "_create_client",
        lambda: httpx2.Client(
            transport=httpx2.MockTransport(handler), trust_env=False
        ),
    )

    installed = _run(
        installation_cli,
        provider_source,
        provider_target,
        process_source,
        process_target,
    )
    ready = _run(readiness_cli, process_target)
    pending = _run(candidate_cli, process_target)
    reconciled = _run(reconciliation_cli, process_target)
    idle = _run(candidate_cli, process_target)

    assert installed == (0, "installed\n", "")
    assert ready == (0, "ready\n", "")
    assert pending == (0, "pending\n", "")
    assert reconciled == (0, "reconciled\n", "")
    assert idle == (0, "idle\n", "")
    assert len(requests) == 1

    presentation = "".join(
        value
        for result in (installed, ready, pending, reconciled, idle)
        for value in result[1:]
    )
    for private_detail in (
        str(provider_source),
        str(provider_target),
        str(process_source),
        str(process_target),
        postgres_url,
        prepared.operation_id,
    ):
        assert private_detail not in presentation

    observer = build_engine(postgres_url)
    try:
        assert (
            DatabaseStagingResearchIndexPromotionUnknownIndex(
                observer
            ).list_unknown_operation_ids()
            == ()
        )
    finally:
        observer.dispose()


def test_completion_document_records_closed_postgresql_acceptance() -> None:
    root = Path(__file__).parents[1]
    document = (
        root
        / "docs/lq-2759-staging-promotion-reconciliation-postgresql-acceptance.md"
    ).read_text(encoding="utf-8")
    for phrase in (
        "real PostgreSQL database",
        "`installed` → `ready` → `pending` → `reconciled` → `idle`",
        "exactly one provider request",
        "independent database engine",
        "no new production code",
        "does not grant promotion or deployment authority",
    ):
        assert phrase in document
