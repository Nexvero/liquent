"""Existing authenticated customer routes, synthetic files only."""
import base64
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from liquent_platform.transport.http.customer_research import register_customer_research
from liquent_platform.identity.access import CurrentWorkspaceContext, MembershipStatus, Permission, UserId, WorkspaceMembership
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import ResolvedBrowserSession, SessionPrincipal
from liquent_platform.jobs.lifecycle import ResearchJobStatus
from liquent_platform.application.authenticate_session import AuthenticationRequired
from liquent_platform.persistence.customer_research import CustomerResearchUnavailable

ROOT = Path(__file__).resolve().parents[1] / 'examples/research_pilot'


class Sessions:
    def get_session(self, identifier):
        if identifier != 'session':
            return None
        return ResolvedBrowserSession(SessionPrincipal(UserId('synthetic-user')), 'csrf')


class Memberships:
    def __init__(self, write):
        self.write = write

    def get_membership(self, user, workspace):
        return WorkspaceMembership(user, workspace, MembershipStatus.ACTIVE,
            frozenset({Permission.RESEARCH_READ, Permission.RESEARCH_WRITE} if self.write else {Permission.RESEARCH_READ}))


class Contexts:
    def resolve_current_workspace(self, user):
        return CurrentWorkspaceContext(user, WorkspaceId('synthetic-workspace'))


class Store:
    def __init__(self):
        self.requests, self.feedback = [], []

    def bind_request(self, *args):
        self.requests.append(args)
        return SimpleNamespace(experiment_id='synthetic-experiment')

    def save_feedback(self, *args):
        self.feedback.append(args)


class Control:
    def __init__(self):
        self.calls = []

    def accept(self, *args):
        self.calls.append(args)
        return SimpleNamespace(job_id='synthetic-job', status=ResearchJobStatus.QUEUED)

    def get(self, *args):
        return SimpleNamespace(status=ResearchJobStatus.SUCCEEDED)


@pytest.fixture
def setup():
    store, control = Store(), Control()
    app = FastAPI()
    register_customer_research(app, sessions=Sessions(), memberships=Memberships(True), contexts=Contexts(), store=store, control=control)
    client = TestClient(app)
    client.cookies.set('liquent_session', 'session')
    client.headers['X-CSRF-Token'] = 'csrf'
    return client, store, control


def payload():
    return {'csv_base64': base64.b64encode((ROOT / 'synthetic.csv').read_bytes()).decode(), 'timeframe': '1m'}


def test_check_and_preview_never_store_or_create_job(setup):
    client, store, control = setup
    result = client.post('/v1/research/data-check', json=payload())
    assert result.status_code == 200
    assert result.json()['simulation_started'] is False
    assert result.json()['facts']['rows'] == 12
    preview = client.post('/v1/research/request-preview', json={
        'csv_base64': payload()['csv_base64'], 'configuration': json.loads((ROOT / 'order.json').read_text())})
    assert preview.status_code == 200
    assert preview.json()['order_created'] is False
    assert len(preview.json()['variant_ids']) == 3
    assert store.requests == store.feedback == control.calls == []
    assert result.headers['cache-control'] == 'no-store'


def test_invalid_data_has_understandable_reason_and_no_job(setup):
    client, store, control = setup
    response = client.post('/v1/research/data-check', json={**payload(), 'csv_base64': base64.b64encode(b'bad,csv\n').decode()})
    assert response.status_code == 200
    assert response.json()['status'] == 'blocked'
    assert response.json()['data_quality']['issues']
    assert store.requests == control.calls == []


@pytest.mark.parametrize('path', ['data-check', 'request-preview', 'customer-jobs', 'customer-feedback'])
def test_no_session_or_csrf_cannot_reach_storage(setup, path):
    client, store, control = setup
    client.headers.pop('X-CSRF-Token')
    assert client.post('/v1/research/' + path, json={}).status_code == 403
    client.cookies.clear()
    assert client.post('/v1/research/' + path, json={}).status_code == 401
    assert store.requests == store.feedback == control.calls == []


def test_feedback_independent_and_explicit_synthetic_classification(setup):
    client, store, control = setup
    value = {'goal':'Synthetic test', 'main_obstacle':'Synthetic only', 'usefulness':3, 'would_use_again':'unsure', 'comment':''}
    response = client.post('/v1/research/customer-feedback', json={'feedback':value, 'synthetic':True})
    assert response.status_code == 200
    assert response.json()['execution_approved'] is False
    assert store.feedback == [('synthetic-user', 'synthetic-workspace', value, True)]
    assert store.requests == control.calls == []


@pytest.mark.parametrize('cookie', [None, ''])
@pytest.mark.parametrize('path', ['customer-context', 'data-check', 'request-preview', 'customer-jobs', 'customer-feedback'])
def test_missing_session_never_queries_session_store(cookie, path):
    class StrictSessions:
        def get_session(self, identifier):
            raise AssertionError('Missing sessions must be rejected before querying storage')

    app, store, control = FastAPI(), Store(), Control()
    register_customer_research(app, sessions=StrictSessions(), memberships=Memberships(True),
                              contexts=Contexts(), store=store, control=control)
    client = TestClient(app)
    if cookie is not None:
        client.cookies.set('liquent_session', cookie)
    response = client.get('/v1/research/' + path) if path == 'customer-context' else client.post('/v1/research/' + path, json={})
    assert response.status_code == 401
    assert response.json() == {'detail': 'authentication_required'}
    assert store.requests == store.feedback == control.calls == []


def test_read_only_customer_can_check_not_execute():
    app, store, control = FastAPI(), Store(), Control()
    register_customer_research(app, sessions=Sessions(), memberships=Memberships(False), contexts=Contexts(), store=store, control=control)
    client = TestClient(app, cookies={'liquent_session':'session'}, headers={'X-CSRF-Token':'csrf'})
    assert client.get('/v1/research/customer-context').json()['can_write'] is False
    assert client.post('/v1/research/data-check', json=payload()).status_code == 200
    assert client.post('/v1/research/customer-jobs', json={}).status_code == 403
    assert store.requests == control.calls == []


def test_database_failure_is_detail_free(setup):
    client, store, _ = setup
    def unavailable(*args):
        raise CustomerResearchUnavailable()
    store.save_feedback = unavailable
    response = client.post('/v1/research/customer-feedback', json={'feedback':{}, 'synthetic':True})
    assert response.status_code == 503
    assert 'sql' not in response.text.lower()


def test_duplicate_fields_and_unknown_query_rejected(setup):
    client, _, _ = setup
    assert client.post('/v1/research/data-check', content='{"timeframe":"1m","timeframe":"5m","csv_base64":"QQ=="}', headers={'Content-Type':'application/json'}).status_code == 422
    assert client.get('/v1/research/customer-context?workspace=other').status_code == 400


def test_explicit_submit_binds_identity_and_retry_key(setup):
    client, store, control = setup
    config = json.loads((ROOT / 'order.json').read_text())
    inputs = {'csv_base64':payload()['csv_base64'], 'configuration':config}
    binding = client.post('/v1/research/request-preview', json=inputs).json()['binding_fingerprint']
    request = {**inputs, 'binding_fingerprint':binding, 'data_rights':True, 'execution_approved':True}
    for _ in range(2):
        response = client.post('/v1/research/customer-jobs', json=request)
        assert response.status_code == 202
        assert response.json()['status'] == 'succeeded'
    assert store.requests[0][:2] == ('synthetic-user', 'synthetic-workspace')
    assert control.calls[0][2] == control.calls[1][2]


def test_deep_configuration_rejected_not_server_error(setup):
    client, _, _ = setup
    config = json.loads((ROOT / 'order.json').read_text())
    config['order']['assumptions'] = json.loads('[' * 600 + '0' + ']' * 600)
    assert client.post('/v1/research/request-preview', json={'csv_base64':payload()['csv_base64'], 'configuration':config}).status_code == 422
