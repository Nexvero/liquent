import json
from pathlib import Path

import httpx2
import pytest

from liquent_platform.transport import (
    staging_research_index_promotion_provider_lifecycle as lifecycle_module,
)
from liquent_platform.transport.staging_research_index_promotion_reconciliation_runtime import (  # noqa: E501
    StagingResearchIndexPromotionReconciliationRuntimeUnavailable,
    compose_staging_research_index_promotion_reconciliation_runtime,
)
from tests.test_staging_research_index_promotion_provider_composition import _payload
from tests.test_staging_research_index_promotion_reconciliation import Recorder, _unknown
from tests.test_staging_research_index_promotion_reconciliation_candidate import (
    Unknowns as Index,
)
from tests.test_staging_research_index_promotion_reconciliation_operation import (
    Unknowns,
)


def write_settings(path: Path) -> None:
    path.write_text(
        "LIQUENT_STAGING_PROMOTION_PROVIDER_ENDPOINT="
        "https://provider.example/status/\n"
    )
    path.chmod(0o600)


def install_client(monkeypatch, handler):
    created = []

    def build():
        client = httpx2.Client(
            transport=httpx2.MockTransport(handler), trust_env=False
        )
        created.append(client)
        return client

    monkeypatch.setattr(lifecycle_module, "_create_client", build)
    return created


def test_manual_execution_reconciles_at_most_one_selected_operation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "provider.env"
    write_settings(path)
    unknown = _unknown()
    operation_id = unknown.attempt.prepared.operation_id
    requests = []

    def handler(request):
        requests.append(request)
        return httpx2.Response(
            200,
            headers={"content-type": "application/json"},
            content=iter([json.dumps(_payload(unknown)).encode()]),
        )

    clients = install_client(monkeypatch, handler)
    recorder = Recorder()
    with compose_staging_research_index_promotion_reconciliation_runtime(
        path, Index((operation_id, "promotion-z")), Unknowns(unknown), recorder
    ) as runtime:
        receipt = runtime.execute_one()
        assert receipt is not None and receipt.operation_id == operation_id
        assert len(requests) == 1
        assert len(recorder.calls) == 1
    assert clients[0].is_closed


def test_empty_index_is_neutral_without_provider_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "provider.env"
    write_settings(path)
    requests = []
    install_client(
        monkeypatch,
        lambda request: requests.append(request) or httpx2.Response(500),
    )
    recorder = Recorder()
    runtime = compose_staging_research_index_promotion_reconciliation_runtime(
        path, Index(()), Unknowns(None), recorder
    )
    try:
        assert runtime.execute_one() is None
        assert requests == [] and recorder.calls == []
    finally:
        runtime.close()


def test_runtime_failure_is_detail_free_and_close_is_terminal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "provider.env"
    write_settings(path)
    install_client(monkeypatch, lambda _: httpx2.Response(500))
    runtime = compose_staging_research_index_promotion_reconciliation_runtime(
        path, Index(("not valid",)), Unknowns(None), Recorder()
    )
    with pytest.raises(
        StagingResearchIndexPromotionReconciliationRuntimeUnavailable
    ) as caught:
        runtime.execute_one()
    assert caught.value.__cause__ is None and caught.value.__context__ is None
    runtime.close()
    with pytest.raises(StagingResearchIndexPromotionReconciliationRuntimeUnavailable):
        runtime.execute_one()


def test_runtime_has_no_loop_claim_retry_or_mutation_surface(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "provider.env"
    write_settings(path)
    install_client(monkeypatch, lambda _: httpx2.Response(500))
    runtime = compose_staging_research_index_promotion_reconciliation_runtime(
        path, Index(()), Unknowns(None), Recorder()
    )
    try:
        assert repr(runtime) == "StagingResearchIndexPromotionReconciliationRuntime()"
        for forbidden in ("run", "loop", "claim", "retry", "promote", "schedule"):
            assert not hasattr(runtime, forbidden)
    finally:
        runtime.close()
