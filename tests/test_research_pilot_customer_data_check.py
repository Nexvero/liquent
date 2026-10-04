"""Data readiness uses unchanged synthetic CSVs without an execution path."""
import json
import stat
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from liquent.research_pilot import customer_data_check, execution
from liquent.research_pilot.customer_data_check import check_customer_data

EXAMPLES = Path(__file__).resolve().parents[1] / 'examples' / 'research_pilot'


@pytest.fixture(autouse=True)
def forbid_simulation(monkeypatch):
    monkeypatch.setattr(execution.BacktestRunner, 'run', lambda *_: pytest.fail('data check simulated'))
    monkeypatch.setattr(execution, 'execute_pilot', lambda *_: pytest.fail('data check executed pilot'))
    # The integrated route is separately tested to call neither the private
    # input store nor the existing queue. No retired portal dependency here.


def csv_hours(count):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = ['timestamp,open,high,low,close,volume']
    for index in range(count):
        rows.append(f'{(start + timedelta(hours=index)).isoformat()},100,101,99,100,10')
    return ('\n'.join(rows) + '\n').encode()


def test_short_synthetic_data_is_limited_and_unmodified():
    raw = (EXAMPLES / 'synthetic.csv').read_bytes()
    before = bytes(raw)
    result = check_customer_data(raw, '5m')
    assert result['schema'] == 'liquent.data-readiness.v1'
    assert result['status'] == 'limited' and result['simulation_started'] is False
    assert result['facts']['rows'] == 12 and result['facts']['short_history'] is True
    assert result['facts']['gap_count'] == 0
    assert result['data_quality']['history']['required_days'] == 30
    assert raw == before
    assert type(result['next_steps']) is list and all(type(step) is str for step in result['next_steps'])
    assert all(type(result[name]) is str and result[name] for name in ('headline', 'meaning'))


def test_existing_hourly_minimum_is_180_days_not_30():
    assert check_customer_data(csv_hours(720), '1h')['status'] == 'limited'
    raw = csv_hours(4320)
    assert len(raw) < 5 * 1024 * 1024
    result = check_customer_data(raw, '1h')
    assert result['status'] == 'usable' and result['simulation_started'] is False
    assert result['facts']['short_history'] is False
    assert result['facts']['rows'] == 4320
    assert result['data_quality']['history']['required_days'] == 180
    assert result['facts']['period_start'] == '2026-01-01T00:00:00+00:00'
    assert result['facts']['period_end'] is not None


@pytest.mark.parametrize('raw', [b'SENSITIVE SECRET CUSTOMER CELL', b'\xffSENSITIVE',
    b'timestamp,open,high,low,close,volume\nPRIVATE-CELL,100,101,99,100,10\n'])
def test_invalid_values_block_without_leaking_customer_cells(raw):
    result = check_customer_data(raw, '5m')
    assert result['status'] == 'blocked' and result['simulation_started'] is False
    assert result['data_quality']['issues']
    assert result['facts']['short_history'] is None
    output = json.dumps(result)
    assert 'SENSITIVE' not in output and 'SECRET' not in output and 'PRIVATE-CELL' not in output
    assert result['facts']['period_start'] is None


def test_gap_is_blocked_and_reported_without_repair():
    raw = csv_hours(3).replace(b'2026-01-01T01:00:00+00:00,100,101,99,100,10\n', b'')
    result = check_customer_data(raw, '1h')
    assert result['status'] == 'blocked'
    assert result['facts']['gap_count'] == 1 and result['facts']['rows'] == 2
    assert result['data_quality']['history']['actual_bars'] == 2


@pytest.mark.parametrize('raw,timeframe,limit', [
    (None, '5m', 100), ('text', '5m', 100), (bytearray(b'data'), '5m', 100),
    (b'', '5m', 100), (b'xxx', '5m', 2), (b'xxx', '5m', True),
    (b'xxx', '5m', 0), (b'xxx', '5m', -1), (b'xxx', '5m', '100'),
    (b'xxx', None, 100), (b'xxx', [], 100), (b'xxx', '2m', 100),
])
def test_invalid_inputs_fail_before_inspection(raw, timeframe, limit, monkeypatch):
    monkeypatch.setattr(customer_data_check, 'inspect_dataset', lambda *_: pytest.fail('invalid input inspected'))
    with pytest.raises(ValueError): check_customer_data(raw, timeframe, limit)


def test_exact_size_limit_is_accepted():
    raw = (EXAMPLES / 'synthetic.csv').read_bytes()
    assert check_customer_data(raw, '5m', len(raw))['status'] == 'limited'


@pytest.mark.parametrize('timeframe,minutes', [('1m', 1), ('5m', 5), ('15m', 15), ('1h', 60)])
def test_all_supported_explicit_intervals(timeframe, minutes):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = ['timestamp,open,high,low,close,volume']
    rows.extend(f'{(start + timedelta(minutes=minutes * index)).isoformat()},100,101,99,100,10'
                for index in range(3))
    result = check_customer_data(('\n'.join(rows) + '\n').encode(), timeframe)
    assert result['status'] == 'limited'
    assert result['facts']['timeframe'] == timeframe and result['facts']['gap_count'] == 0


@pytest.mark.parametrize('raise_during_inspection', [False, True])
def test_private_unchanged_temporary_snapshot_is_always_removed(monkeypatch, raise_during_inspection):
    raw = (EXAMPLES / 'synthetic.csv').read_bytes()
    original = customer_data_check.inspect_dataset
    seen = []
    def inspect(path, timeframe):
        seen.append(path)
        assert path.read_bytes() == raw
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
        if raise_during_inspection: raise OSError('PRIVATE-PATH-FAILURE')
        return original(path, timeframe)
    monkeypatch.setattr(customer_data_check, 'inspect_dataset', inspect)
    if raise_during_inspection:
        with pytest.raises(ValueError) as error: check_customer_data(raw, '5m')
        assert 'PRIVATE' not in str(error.value)
    else:
        assert check_customer_data(raw, '5m')['status'] == 'limited'
    assert len(seen) == 1 and not seen[0].exists() and not seen[0].parent.exists()
