"""Guided input keeps the existing ephemeral preview contract; synthetic only."""

from copy import deepcopy
import json

from test_customer_research_http import ROOT, payload, setup  # noqa: F401


def test_explicit_common_settings_copy_binds_actual_changed_inputs(setup):
    client, store, control = setup
    configuration = json.loads((ROOT / 'order.json').read_text())
    original = deepcopy(configuration)
    raw = payload()['csv_base64']
    before = client.post('/v1/research/request-preview', json={
        'csv_base64': raw, 'configuration': configuration}).json()
    for variant in configuration['variants'][1:]:
        variant['risk'] = deepcopy(configuration['variants'][0]['risk'])
        variant['costs'] = deepcopy(configuration['variants'][0]['costs'])
    response = client.post('/v1/research/request-preview', json={
        'csv_base64': raw, 'configuration': configuration})
    assert response.status_code == 200
    after = response.json()
    assert after['binding_fingerprint'] != before['binding_fingerprint']
    assert after['variant_ids'] == [v['id'] for v in original['variants']]
    assert after['order_created'] is after['simulation_started'] is False
    for copied, prior in zip(configuration['variants'], original['variants']):
        assert copied['strategy_parameters'] == prior['strategy_parameters']
        assert copied['strategy'] == prior['strategy']
        assert copied['seed'] == prior['seed']
        assert copied['hypothesis'] == prior['hypothesis']
    assert store.requests == store.feedback == control.calls == []


def test_preparation_does_not_repair_invalid_data_or_start_order(setup):
    client, store, control = setup
    configuration = json.loads((ROOT / 'order.json').read_text())
    invalid = {'csv_base64': 'YmFkLGNzdiAK', 'configuration': configuration}
    assert client.post('/v1/research/request-preview', json=invalid).status_code == 422
    assert store.requests == store.feedback == control.calls == []
