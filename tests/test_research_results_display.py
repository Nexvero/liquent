from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine

from liquent_platform.identity.research import WorkspaceId
from liquent_platform.jobs.lifecycle import ResearchJobStatus
from liquent_platform.persistence.identity_errors import ResearchJobStoreUnavailable
from liquent_platform.transport.http.research_results import result_document
from test_workspace_research_job_index_http import _client, Index, Memberships, USER, WORKSPACE


SUMMARY = {
    "title": "Synthetic test", "strategy_name": "Mid-breakout",
    "starting_equity": 1000.0, "ending_equity": 1025.5,
    "number_of_trades": 2, "approved_signals": 2, "rejected_signals": 1,
    "metrics": {"win_rate": 0.5, "max_drawdown": 10, "profit_factor": None},
    "risk_notes": ["Synthetic prices only"],
    "private_token": "never-render-me",
}


def test_summary_uses_real_values_and_describes_simulation():
    document = result_document("job-1", "succeeded", SUMMARY)
    for text in ("1.000,00", "1.025,50", "50,00 %", "10,00", "Synthetic test",
                 "Mid-breakout", "Simulierte Trades", "keine Live-Trades", "nicht die Profitabilität"):
        assert text in document
    assert "never-render-me" not in document
    assert "Nicht verfügbar" in document


def test_untrusted_summary_is_escaped_and_missing_values_not_invented():
    document = result_document('<script>bad</script>', "succeeded", {
        "title": '<img src=x onerror=alert(1)>', "risk_notes": ['<script>bad</script>'],
        "ending_equity": float("inf"), "starting_equity": True,
        "metrics": {"win_rate": float("nan")},
    })
    assert '<script>' not in document
    assert '<img src=x' not in document
    assert '&lt;img' in document
    assert 'Nicht verfügbar' in document


@pytest.mark.parametrize("state", ["queued", "running", "failed", "succeeded"])
def test_missing_evidence_never_claims_metrics(state):
    document = result_document("job-1", state, None)
    assert "Startkapital" not in document
    assert "Auswertung" in document


@pytest.fixture
def persistent_client(monkeypatch):
    import liquent_platform.transport.http.app as app_module
    from fastapi.testclient import TestClient
    from test_workspace_research_job_index_http import Sessions, Contexts, NOW
    from liquent_platform.application.internal_destination import ValidatedInternalDestination
    from datetime import timedelta

    class Store:
        def __init__(self, *args, **kwargs):
            self.calls = []
            self.job = SimpleNamespace(workspace_id=WORKSPACE, status=ResearchJobStatus.SUCCEEDED)
            self.evidence = SUMMARY
            self.fail = False

        def get_job(self, actor, identifier):
            self.calls.append(("job", actor, identifier))
            if self.fail:
                raise ResearchJobStoreUnavailable
            return self.job

        def get_evidence(self, actor, identifier):
            self.calls.append(("evidence", actor, identifier))
            if self.evidence == "unavailable":
                raise ResearchJobStoreUnavailable
            return self.evidence

    monkeypatch.setattr(app_module, "DatabaseResearchJobs", Store)
    engine = create_engine("sqlite://")
    sessions, contexts, memberships = Sessions(), Contexts(), Memberships()
    app = app_module.create_app(
        database_engine=engine,
        oidc_callback_transactions=object(), oidc_callback_verifier=object(),
        oidc_callback_identities=object(), oidc_callback_admissions=object(),
        oidc_callback_sessions=object(), oidc_callback_material=object(),
        oidc_login_clock=lambda: NOW, oidc_session_lifetime=timedelta(hours=1),
        oidc_callback_rejection=ValidatedInternalDestination("/login/rejected"),
        oidc_callback_unavailable=ValidatedInternalDestination("/login/unavailable"),
        logout_sessions=sessions, logout_revocations=object(),
        landing_workspace_contexts=contexts, research_sessions=sessions,
        research_memberships=memberships,
    )
    client = TestClient(app)
    client.cookies.set("liquent_session", "opaque-session")
    yield client, app.state.persistent_research_jobs, memberships
    client.close()
    engine.dispose()


def test_persistent_result_authorizes_and_sets_private_headers(persistent_client):
    client, store, _ = persistent_client
    response = client.get("/research/jobs/job-1")
    assert response.status_code == 200
    assert "1.025,50" in response.text
    assert store.calls[0][1] == USER
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_permission_revocation_blocks_results_without_reading_store(persistent_client):
    client, store, memberships = persistent_client
    memberships.allowed = False
    response = client.get("/research/jobs/job-1")
    assert response.status_code == 404 and response.content == b""
    assert store.calls == []


def test_other_workspace_and_missing_job_are_neutral(persistent_client):
    client, store, _ = persistent_client
    store.job = SimpleNamespace(workspace_id=WorkspaceId("other"), status=ResearchJobStatus.SUCCEEDED)
    assert client.get("/research/jobs/job-1").content == b""
    assert len(store.calls) == 1
    store.job = None
    assert client.get("/research/jobs/missing").status_code == 404


def test_store_failure_has_no_partial_result(persistent_client):
    client, store, _ = persistent_client
    store.fail = True
    response = client.get("/research/jobs/job-1", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login/unavailable"
    assert response.content == b""


def test_evidence_failure_has_no_partial_result(persistent_client):
    client, store, _ = persistent_client
    store.evidence = "unavailable"
    response = client.get("/research/jobs/job-1", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login/unavailable"
    assert response.content == b""


def test_anonymous_and_query_and_write_methods_do_not_read_results(persistent_client):
    client, store, _ = persistent_client
    client.cookies.clear()
    assert client.get("/research/jobs/job-1", follow_redirects=False).headers["location"] == "/login"
    assert client.get("/research/jobs/job-1?download=1").status_code == 400
    assert client.post("/research/jobs/job-1").status_code == 405
    assert store.calls == []


def test_index_links_to_result_without_exposing_api_or_private_fields():
    from liquent_platform.identity.research import JobId
    from liquent_platform.identity.research_job import ResearchJobIndexItem
    from test_workspace_research_job_index_http import NOW
    item = ResearchJobIndexItem(JobId("job-1"), ResearchJobStatus.SUCCEEDED, NOW, NOW)
    response = _client(Index((item,))).get("/research")
    assert '<a href="/research/jobs/job-1">Ergebnis ansehen</a>' in response.text
    assert '/v1/research/jobs/' not in response.text
    assert 'private-csrf' not in response.text


def test_in_memory_results_use_the_same_summary_projection():
    from dataclasses import replace
    from test_research_read_api import _job, NoSignalRunner
    client = _client(Index())
    job = _job()
    job.snapshot = replace(job.snapshot, workspace_id=WORKSPACE)
    job.execute(NoSignalRunner())
    client.app.state.research_jobs.add(job)
    response = client.get("/research/jobs/job-1")
    assert response.status_code == 200
    assert "No-signal evidence" in response.text
    assert "1.000,00" in response.text


def test_pending_persistent_job_does_not_read_evidence(persistent_client):
    client, store, _ = persistent_client
    store.job.status = ResearchJobStatus.RUNNING
    response = client.get("/research/jobs/job-1")
    assert response.status_code == 200
    assert "Wird ausgeführt" in response.text
    assert "Startkapital" not in response.text
    assert len(store.calls) == 1
