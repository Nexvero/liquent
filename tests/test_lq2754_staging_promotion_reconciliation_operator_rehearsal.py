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
from liquent_platform.transport import (
    staging_research_index_promotion_reconciliation_readiness_audit_cli as readiness_cli,
)
from liquent_platform.transport import (
    staging_research_index_promotion_reconciliation_settings_installation_cli as installation_cli,
)
from tests.test_staging_research_index_promotion_attempt_journal import NOW, _attempt
from tests.test_staging_research_index_promotion_provider_composition import _payload


def _write_private(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o600)
    return path


def _run(command, *arguments: Path) -> tuple[int, str, str]:
    stdout, stderr = StringIO(), StringIO()
    code = command.run(
        tuple(str(argument) for argument in arguments),
        stdout=stdout,
        stderr=stderr,
    )
    return code, stdout.getvalue(), stderr.getvalue()


def test_installed_operator_chain_reconciles_one_exact_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
    prepared = _attempt(operation="promotion-lq2754-private")
    journal = DatabaseStagingResearchIndexPromotionAttemptJournal(engine)
    journal.record_prepared(prepared, observed_at=NOW)
    started = journal.mark_write_started(prepared, observed_at=NOW)
    unknown = journal.record_unknown(started, observed_at=NOW)
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
    present = _run(
        installation_cli,
        provider_source,
        provider_target,
        process_source,
        process_target,
    )

    assert installed == (0, "installed\n", "")
    assert ready == (0, "ready\n", "")
    assert pending == (0, "pending\n", "")
    assert reconciled == (0, "reconciled\n", "")
    assert idle == (0, "idle\n", "")
    assert present == (3, "", "present\n")
    assert len(requests) == 1

    presentation = "".join(
        value
        for result in (installed, ready, pending, reconciled, idle, present)
        for value in result[1:]
    )
    for secret in (
        str(provider_source),
        str(provider_target),
        str(process_source),
        str(process_target),
        database_url,
        prepared.operation_id,
    ):
        assert secret not in presentation

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


def test_completion_document_records_the_closed_operator_rehearsal() -> None:
    root = Path(__file__).parents[1]
    document = (
        root
        / "docs/lq-2754-staging-promotion-reconciliation-operator-rehearsal.md"
    ).read_text(encoding="utf-8")
    for phrase in (
        "`installed` → `ready` → `pending` → `reconciled` → `idle`",
        "exactly one provider request",
        "no new production code",
        "does not grant reconciliation authority",
        "does not grant promotion or deployment authority",
    ):
        assert phrase in document
