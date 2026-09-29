from io import StringIO
import json
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
from tests.test_staging_research_index_promotion_attempt_journal import NOW, _attempt
from tests.test_staging_research_index_promotion_provider_composition import _payload


def _write_private(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8")
    path.chmod(0o600)


def _prepare(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, committed: bool):
    database = tmp_path / "reconciliation.db"
    database_url = f"sqlite+pysqlite:///{database}"
    engine = build_engine(database_url)
    upgrade_to_head(str(engine.url))
    prepared = _attempt(operation="promotion-lq2753-private")
    journal = DatabaseStagingResearchIndexPromotionAttemptJournal(engine)
    journal.record_prepared(prepared, observed_at=NOW)
    started = journal.mark_write_started(prepared, observed_at=NOW)
    unknown = journal.record_unknown(started, observed_at=NOW)
    engine.dispose()

    provider = tmp_path / "provider.env"
    process = tmp_path / "process.env"
    _write_private(
        provider,
        "LIQUENT_STAGING_PROMOTION_PROVIDER_ENDPOINT="
        "https://provider.example/status/\n",
    )
    _write_private(
        process,
        "LIQUENT_STAGING_PROMOTION_RECONCILIATION_PROVIDER_SETTINGS_FILE="
        f"{provider}\n"
        "LIQUENT_STAGING_PROMOTION_RECONCILIATION_DATABASE_URL="
        f"{database_url}\n",
    )
    requests = []

    def handler(request):
        requests.append(request)
        payload = (
            _payload(unknown)
            if committed
            else {"operation_id": prepared.operation_id, "status": "pending"}
        )
        return httpx2.Response(
            200 if committed else 202,
            headers={"content-type": "application/json"},
            content=iter([json.dumps(payload).encode()]),
        )

    monkeypatch.setattr(
        lifecycle_module,
        "_create_client",
        lambda: httpx2.Client(
            transport=httpx2.MockTransport(handler), trust_env=False
        ),
    )
    return process, database_url, prepared.operation_id, requests


def _run(command, path: Path) -> tuple[int, str, str]:
    stdout, stderr = StringIO(), StringIO()
    code = command.run((str(path),), stdout=stdout, stderr=stderr)
    return code, stdout.getvalue(), stderr.getvalue()


def test_committed_provider_outcome_transitions_pending_to_idle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    process, database_url, operation_id, requests = _prepare(
        tmp_path, monkeypatch, committed=True
    )
    before = _run(candidate_cli, process)
    reconciled = _run(reconciliation_cli, process)
    after = _run(candidate_cli, process)

    assert before == (0, "pending\n", "")
    assert reconciled == (0, "reconciled\n", "")
    assert after == (0, "idle\n", "")
    assert len(requests) == 1
    output = "".join(
        value for result in (before, reconciled, after) for value in result[1:]
    )
    assert operation_id not in output

    engine = build_engine(database_url)
    try:
        assert (
            DatabaseStagingResearchIndexPromotionUnknownIndex(
                engine
            ).list_unknown_operation_ids()
            == ()
        )
    finally:
        engine.dispose()


def test_pending_provider_outcome_preserves_candidate_despite_idle_process_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    process, database_url, operation_id, requests = _prepare(
        tmp_path, monkeypatch, committed=False
    )
    before = _run(candidate_cli, process)
    not_reconciled = _run(reconciliation_cli, process)
    after = _run(candidate_cli, process)

    assert before == (0, "pending\n", "")
    assert not_reconciled == (0, "idle\n", "")
    assert after == (0, "pending\n", "")
    assert len(requests) == 1
    output = "".join(
        value
        for result in (before, not_reconciled, after)
        for value in result[1:]
    )
    assert operation_id not in output

    engine = build_engine(database_url)
    try:
        assert DatabaseStagingResearchIndexPromotionUnknownIndex(
            engine
        ).list_unknown_operation_ids() == (operation_id,)
    finally:
        engine.dispose()


def test_runbook_defines_idle_as_no_durable_reconciliation_not_candidate_absence() -> None:
    root = Path(__file__).parents[1]
    runbook = (root / "operations/runbooks/staging-promotion.md").read_text(
        encoding="utf-8"
    )
    start = runbook.index("liquent-staging-promotion-reconcile /ABSOLUTE/PROCESS_SETTINGS")
    end = runbook.index("## Required evidence", start)
    section = runbook[start:end]
    assert "no durable reconciliation was recorded" in section
    assert "does not prove that no eligible candidate exists" in section
    assert "no eligible unknown attempt was present" not in section


def test_completion_document_records_both_closed_state_transitions() -> None:
    root = Path(__file__).parents[1]
    document = (
        root
        / "docs/lq-2753-staging-promotion-reconciliation-operator-boundary-acceptance.md"
    ).read_text(encoding="utf-8")
    for phrase in (
        "`pending` → `reconciled` → `idle`",
        "`pending` → `idle` → `pending`",
        "exactly one provider request",
        "no new production code",
        "does not grant retry authority",
    ):
        assert phrase in document
