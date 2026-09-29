from pathlib import Path

import httpx2
import pytest

from liquent_platform.persistence.database import build_engine
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
from tests.test_lq2754_staging_promotion_reconciliation_operator_rehearsal import (
    _run,
)
from tests.test_lq2755_staging_promotion_reconciliation_failure_containment import (
    _prepare,
)


def test_database_failure_stops_before_provider_and_preserves_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process, database_url, operation_id = _prepare(tmp_path)
    database = Path(database_url.removeprefix("sqlite+pysqlite:///"))
    preserved_database = database.with_name(f"{database.name}.preserved")
    database.rename(preserved_database)
    database.mkdir()
    requests = []

    def handler(request):
        requests.append(request)
        raise AssertionError("provider access must remain unreachable")

    monkeypatch.setattr(
        lifecycle_module,
        "_create_client",
        lambda: httpx2.Client(
            transport=httpx2.MockTransport(handler), trust_env=False
        ),
    )

    readiness = _run(readiness_cli, process)
    candidate = _run(candidate_cli, process)
    reconciliation = _run(reconciliation_cli, process)

    assert readiness == (1, "", "unavailable\n")
    assert candidate == (1, "", "unavailable\n")
    assert reconciliation == (1, "", "unavailable\n")
    assert requests == []

    presentation = "".join(
        value
        for result in (readiness, candidate, reconciliation)
        for value in result[1:]
    )
    for private_detail in (str(database), database_url, operation_id):
        assert private_detail not in presentation

    preserved_url = f"sqlite+pysqlite:///{preserved_database}"
    engine = build_engine(preserved_url)
    try:
        assert DatabaseStagingResearchIndexPromotionUnknownIndex(
            engine
        ).list_unknown_operation_ids() == (operation_id,)
    finally:
        engine.dispose()


def test_completion_document_records_closed_database_failure_containment() -> None:
    root = Path(__file__).parents[1]
    document = (
        root
        / "docs/lq-2757-staging-promotion-reconciliation-database-failure-containment.md"
    ).read_text(encoding="utf-8")
    for phrase in (
        "database failure",
        "no provider request",
        "no durable reconciliation",
        "candidate remains pending",
        "no repair or retry authority",
    ):
        assert phrase in document
