"""Synthetic-only integration of customer research with existing jobs."""

import copy
import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import text

from liquent_platform.application.customer_research import customer_input_binding
from liquent_platform.application.evidence import evidence_document
from liquent_platform.application.local_csv import LocalCsvMidBreakoutV0Resolver
from liquent_platform.application.research import execute_local_research
from liquent_platform.identity.access import UserId
from liquent_platform.identity.research import (
    JobId, ResearchJobAcceptanceId, ResearchJobClaimId, ResearchJobRevisionId,
    ResearchWorkerId, WorkspaceId,
)
from liquent_platform.identity.research_job import ResearchResultArtifactClass
from liquent_platform.operators.research_worker_composition import compose_research_worker
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.customer_research import DatabaseCustomerResearchStore
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.research_artifacts import LocalImmutableResearchArtifactStore


EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "research_pilot"


@pytest.fixture
def inputs():
    return (EXAMPLES / "synthetic.csv").read_bytes(), json.loads((EXAMPLES / "order.json").read_text())


@pytest.fixture
def backend(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path / 'customer.db'}")
    upgrade_to_head(str(engine.url))
    _seed(engine)
    yield engine, DatabaseCustomerResearchStore(engine)
    engine.dispose()


def _seed(engine):
    with engine.begin() as connection:
        for user in (b"u", b"other", b"reader"):
            connection.execute(text("INSERT INTO identity_users VALUES (:u,'active')"), {"u": user})
        for workspace in (b"w", b"other-w"):
            connection.execute(text("INSERT INTO identity_workspaces VALUES (:w,'active')"), {"w": workspace})
        for user, workspace, permission in ((b"u", b"w", "research:write"),
                                              (b"other", b"other-w", "research:write"),
                                              (b"reader", b"w", "research:read")):
            connection.execute(text("INSERT INTO workspace_memberships (user_id,workspace_id,status) VALUES (:u,:w,'active')"),
                               {"u": user, "w": workspace})
            connection.execute(text("INSERT INTO workspace_membership_permissions VALUES (:u,:w,:p)"),
                               {"u": user, "w": workspace, "p": permission})


def _bind(store, inputs, **overrides):
    raw, configuration = inputs
    arguments = dict(owner="u", workspace="w", raw=raw, configuration=configuration,
                     expected_binding=customer_input_binding(raw, configuration),
                     data_rights=True, execution_approved=True)
    arguments.update(overrides)
    return store.bind_request(**arguments)


def _count(engine, table):
    assert table in {"customer_research_requests", "customer_research_feedback", "research_jobs"}
    with engine.connect() as connection:
        return connection.execute(text("SELECT COUNT(*) FROM " + table)).scalar_one()


@pytest.mark.parametrize("overrides", [
    {"data_rights": False}, {"data_rights": 1}, {"execution_approved": False},
    {"execution_approved": "true"}, {"expected_binding": "sha256:" + "0" * 64},
    {"expected_binding": None}, {"expected_binding": "sha256:ä"},
    {"owner": "reader"}, {"workspace": "other-w"},
    {"owner": "other"}, {"owner": ""},
])
def test_invalid_approval_binding_or_customer_authority_stores_nothing(backend, inputs, overrides):
    engine, store = backend
    with pytest.raises(ValueError):
        _bind(store, inputs, **overrides)
    assert _count(engine, "customer_research_requests") == 0
    assert _count(engine, "research_jobs") == 0


def test_invalid_csv_and_incomplete_variants_are_never_stored(backend, inputs):
    engine, store = backend
    raw, configuration = inputs
    for invalid in (b"not,csv\n", raw.replace(b",100,", b",NaN,", 1), b"x" * (5242880 + 1)):
        with pytest.raises(ValueError):
            _bind(store, inputs, raw=invalid, expected_binding=customer_input_binding(invalid, configuration))
    incomplete = copy.deepcopy(configuration)
    incomplete["variants"].pop()
    with pytest.raises(ValueError):
        _bind(store, inputs, configuration=incomplete)
    assert _count(engine, "customer_research_requests") == 0


def test_immutable_retry_and_three_variant_evidence(backend, inputs):
    engine, store = backend
    snapshot = _bind(store, inputs)
    assert snapshot == _bind(store, inputs)
    assert _count(engine, "customer_research_requests") == 1
    assert _count(engine, "research_jobs") == 0  # binding is not job acceptance
    execution = store.resolve(snapshot)
    first = evidence_document(execute_local_research(execution, title=snapshot.title))
    second = evidence_document(execute_local_research(store.resolve(snapshot), title=snapshot.title))
    assert first == second
    assert first["aggregate_performance_available"] is False
    assert first["number_of_trades"] is None
    assert first["starting_equity"] is None
    pilot = first["pilot_result"]
    assert [variant["variant_id"] for variant in pilot["variants"]] == [v["id"] for v in inputs[1]["variants"]]
    assert all(variant["evidence"]["cost_totals"]["total"] >= 0 for variant in pilot["variants"])
    assert "request_owner" not in json.dumps(first)
    assert inputs[0].decode() not in json.dumps(first)


@pytest.mark.parametrize("change", ["workspace", "ref", "owner", "binding", "configuration", "title", "experiment"])
def test_snapshot_tampering_and_cross_workspace_resolution_fail(backend, inputs, change):
    _, store = backend
    snapshot = _bind(store, inputs)
    if change == "workspace":
        bad = replace(snapshot, workspace_id=WorkspaceId("other-w"))
    elif change == "ref":
        bad = replace(snapshot, dataset_ref="../../secret.csv")
    elif change == "title":
        bad = replace(snapshot, title="tampered")
    elif change == "experiment":
        bad = replace(snapshot, experiment_id="tampered")
    else:
        parameters = dict(snapshot.strategy_parameters)
        parameters[{"owner": "request_owner", "binding": "input_binding",
                    "configuration": "configuration_json"}[change]] = "other"
        bad = replace(snapshot, strategy_parameters=tuple(sorted(parameters.items())))
    with pytest.raises(ValueError):
        store.resolve(bad)


def test_revoked_permission_and_tampered_private_csv_fail(backend, inputs):
    engine, store = backend
    snapshot = _bind(store, inputs)
    with engine.begin() as connection:
        connection.execute(text("UPDATE customer_research_requests SET dataset_csv=:raw"), {"raw": b"changed"})
    with pytest.raises(ValueError):
        store.resolve(snapshot)
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM workspace_membership_permissions WHERE user_id=:u"), {"u": b"u"})
    with pytest.raises(ValueError):
        store.resolve(snapshot)


def test_configuration_utf8_size_limit_before_storage_and_resolution(backend, inputs):
    engine, store = backend
    raw, configuration = inputs
    huge = copy.deepcopy(configuration)
    huge["variants"][0]["hypothesis"] = "ä" * (64 * 1024 // 2)
    with pytest.raises(ValueError, match="64 KiB"):
        _bind(store, inputs, configuration=huge,
              expected_binding=customer_input_binding(raw, huge))
    assert _count(engine, "customer_research_requests") == 0
    snapshot = _bind(store, inputs)
    parameters = dict(snapshot.strategy_parameters)
    parameters["configuration_json"] = "ä" * (64 * 1024 // 2 + 1)
    with pytest.raises(ValueError, match="64 KiB"):
        store.resolve(replace(snapshot, strategy_parameters=tuple(sorted(parameters.items()))))
    with engine.begin() as connection:
        connection.execute(text("UPDATE customer_research_requests SET configuration_json=:value"),
                           {"value": parameters["configuration_json"]})
    with pytest.raises(ValueError, match="64 KiB"):
        store.resolve(snapshot)
FEEDBACK = {"goal": "Synthetic inspection", "main_obstacle": "Synthetic test only",
            "usefulness": 3, "would_use_again": "unsure", "comment": "No participant or purchase claim"}


def test_feedback_optional_separate_namespaces_and_read_authority(backend):
    engine, store = backend
    jobs_before = _count(engine, "research_jobs")
    requests_before = _count(engine, "customer_research_requests")
    store.save_feedback("reader", "w", FEEDBACK, synthetic=True)
    store.save_feedback("reader", "w", FEEDBACK, synthetic=False)
    with engine.connect() as connection:
        rows = connection.execute(text("SELECT synthetic,evidence_type FROM customer_research_feedback ORDER BY synthetic")).all()
    assert rows == [(False, "self_report_not_purchase"), (True, "self_report_not_purchase")]
    assert _count(engine, "research_jobs") == jobs_before
    assert _count(engine, "customer_research_requests") == requests_before
    with pytest.raises(ValueError):
        store.save_feedback("other", "w", FEEDBACK, synthetic=True)
    with pytest.raises(ValueError):
        store.save_feedback("reader", "w", FEEDBACK, synthetic="true")
    with pytest.raises(ValueError):
        store.save_feedback("reader", "w", {**FEEDBACK, "usefulness": 6}, synthetic=True)
    assert _count(engine, "customer_research_feedback") == 2


def test_existing_persistent_worker_executes_bound_customer_job_and_download(backend, inputs, tmp_path):
    engine, store = backend
    snapshot = _bind(store, inputs)
    root = tmp_path / "artifacts"
    root.mkdir(mode=0o700)
    artifacts = LocalImmutableResearchArtifactStore(root)
    revisions = iter(ResearchJobRevisionId(f"r{i}") for i in range(10))
    composition = compose_research_worker(
        engine=engine, resolver=LocalCsvMidBreakoutV0Resolver(EXAMPLES, customer_store=store),
        artifacts=artifacts, generate_job_id=lambda: JobId("synthetic-job"),
        generate_revision_id=lambda: next(revisions), generate_claim_id=lambda: ResearchJobClaimId("claim"),
        lease_duration=timedelta(seconds=60), clock=lambda: datetime(2026, 10, 4, tzinfo=timezone.utc))
    accepted = composition.jobs.store.accept_job(
        ResearchJobAcceptanceId("synthetic-acceptance"), UserId("u"), snapshot,
        ResearchResultArtifactClass.BACKTEST_RESULT_V1)
    assert accepted is not None
    processed = composition.processor.process(ResearchWorkerId("synthetic-worker"))
    assert processed.kind.value == "succeeded"
    content = artifacts.get(processed.completed.artifact)
    assert len(json.loads(content)["pilot_result"]["variants"]) == 3
    assert composition.jobs.store.get_evidence(UserId("other"), accepted.job_id) is None


@pytest.mark.postgres_integration
def test_postgresql_customer_binding_feedback_and_existing_worker(postgres_engine, inputs, tmp_path):
    """Real PostgreSQL path; never substitutes SQLite if unavailable."""
    _seed(postgres_engine)
    backend = postgres_engine, DatabaseCustomerResearchStore(postgres_engine)
    test_immutable_retry_and_three_variant_evidence(backend, inputs)
    test_feedback_optional_separate_namespaces_and_read_authority(backend)
    test_existing_persistent_worker_executes_bound_customer_job_and_download(backend, inputs, tmp_path)
