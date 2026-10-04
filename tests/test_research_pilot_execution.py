"""Integration checks against real existing strategy, risk and cost engines."""

import copy
import json
from pathlib import Path

import pytest

from liquent.research_pilot import execution
from liquent.research_pilot.cli import main
from liquent.research_pilot.customer_report import pilot_to_dict

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "research_pilot"


@pytest.fixture
def config():
    return json.loads((EXAMPLES / "order.json").read_text())


def test_three_actual_variants_repeat_and_costs(config):
    first = execution.execute_pilot(EXAMPLES / "synthetic.csv", config)
    second = execution.execute_pilot(EXAMPLES / "synthetic.csv", config)
    assert pilot_to_dict(first) == pilot_to_dict(second)
    assert config == first.configuration
    assert len({v.input_fingerprint for v in first.variants}) == 3
    for declared, outcome in zip(config["variants"], first.variants):
        assert outcome.status == "succeeded"
        assert outcome.variant_id == declared["id"]
        assert outcome.inputs["strategy_parameters"] == declared["strategy_parameters"]
        assert outcome.inputs["risk"] == declared["risk"]
        assert outcome.summary.number_of_trades > 0
        evidence = outcome.evidence
        trades = evidence["trades"]
        costs = evidence["cost_totals"]
        assert costs["total"] == pytest.approx(costs["fee"] + costs["spread"] + costs["slippage"])
        assert costs["net_pnl"] == pytest.approx(costs["gross_pnl"] - costs["total"])
        equity = declared["risk"]["initial_equity"]
        for trade in trades:
            quantity = trade["quantity"]
            assert quantity <= declared["risk"]["max_position_size"]
            actual = (abs(trade["entry_price"] * quantity) + abs(trade["exit_price"] * quantity))
            expected = actual * (declared["costs"]["fee_rate"] + declared["costs"]["slippage"]) + 2 * quantity * declared["costs"]["spread"]
            assert trade["costs"] == pytest.approx(expected)
            risk = declared["risk"]
            if risk["sizing_mode"] == "absolute":
                size = risk["risk_per_trade"]
            else:
                distance = trade["entry_price"] * declared["strategy_parameters"]["stop_distance_pct"]
                size = equity * risk["risk_per_trade_pct"] / distance
                if risk["max_position_notional"]:
                    size = min(size, risk["max_position_notional"] / trade["entry_price"])
                size = min(size, risk["max_total_exposure"] / trade["entry_price"])
            assert quantity == pytest.approx(min(size, risk["max_position_size"], risk["max_total_exposure"]))
            assert trade["duration_bars"] == 1
            equity += trade["net_pnl"]
        assert "day_realized_loss" in evidence["effective_risk"]["max_daily_loss"] or "ignoriert" in evidence["effective_risk"]["max_daily_loss"]


def test_changed_inputs_change_identity(config):
    first = execution.execute_pilot(EXAMPLES / "synthetic.csv", config)
    changed = copy.deepcopy(config)
    changed["variants"][0]["costs"]["fee_rate"] *= 2
    second = execution.execute_pilot(EXAMPLES / "synthetic.csv", changed)
    assert first.pilot_id != second.pilot_id
    assert first.variants[0].input_fingerprint != second.variants[0].input_fingerprint
    assert first.variants[1].input_fingerprint == second.variants[1].input_fingerprint


@pytest.mark.parametrize("mutation", ["two", "duplicate", "missing", "nan", "strategy", "mode"])
def test_rejects_unagreed_config_before_reading(config, mutation, monkeypatch):
    if mutation == "two":
        config["variants"].pop()
    elif mutation == "duplicate":
        config["variants"][1]["id"] = config["variants"][0]["id"]
    elif mutation == "missing":
        del config["variants"][0]["costs"]["spread"]
    elif mutation == "nan":
        config["variants"][0]["costs"]["slippage"] = float("nan")
    elif mutation == "strategy":
        config["variants"][0]["strategy"] = "search"
    else:
        config["variants"][0]["risk"]["sizing_mode"] = "unknown"
    monkeypatch.setattr(execution, "inspect_dataset", lambda *a: pytest.fail("must reject before reading"))
    with pytest.raises(ValueError):
        execution.execute_pilot(Path("unused"), config)


def test_invalid_blocks_all_and_cli_documents_reason(config, tmp_path, monkeypatch):
    bad = tmp_path / "invalid.csv"
    bad.write_text("timestamp,open,high,low,close,volume\n2026-01-01T00:00:00Z,100,101,99,NaN,5\n")
    monkeypatch.setattr(execution, "BacktestRunner", lambda **k: pytest.fail("invalid data must block runner"))
    result = execution.execute_pilot(bad, config)
    assert all(v.status == "blocked_data" and v.summary is None for v in result.variants)
    output = tmp_path / "rejected"
    assert main(["--dataset", str(bad), "--config", str(EXAMPLES / "order.json"), "--output", str(output)]) == 2
    assert "endliche Zahl" in (output / "report.md").read_text()


def test_no_signals_is_not_failed(config, tmp_path):
    flat = tmp_path / "flat.csv"
    rows = ["timestamp,open,high,low,close,volume"]
    rows += [f"2026-01-01T00:{minute:02d}:00Z,100,101,99,100,5" for minute in range(0, 60, 5)]
    flat.write_text("\n".join(rows) + "\n")
    result = execution.execute_pilot(flat, config)
    assert all(v.status == "no_signals" and v.summary.number_of_trades == 0 for v in result.variants)
    assert all(v.evidence["cost_totals"]["total"] == 0 for v in result.variants)


def test_all_rejected_signals_are_distinct(config):
    for variant in config["variants"]:
        variant["risk"]["sizing_mode"] = "percent_risk"
        variant["risk"]["risk_per_trade_pct"] = .01
        variant["strategy_parameters"]["stop_distance_pct"] = 1e-20
    result = execution.execute_pilot(EXAMPLES / "synthetic.csv", config)
    assert all(v.status == "succeeded" for v in result.variants)
    assert all(v.summary.number_of_trades == 0 and v.summary.rejected_signals > 0 for v in result.variants)


def test_failed_variant_does_not_fabricate_results(config, monkeypatch):
    original = execution._STRATEGIES["mid-breakout-v0"]
    class FailDuringRun(original):
        def generate_signals(self, *args, **kwargs):
            raise RuntimeError("customer-sensitive content")
    monkeypatch.setitem(execution._STRATEGIES, "mid-breakout-v0", FailDuringRun)
    result = execution.execute_pilot(EXAMPLES / "synthetic.csv", config)
    assert result.variants[0].status == "failed"
    assert result.variants[0].summary is None
    assert "customer-sensitive" not in result.variants[0].error
    assert all(v.status == "succeeded" for v in result.variants[1:])


def test_oversized_numeric_setting_has_clear_rejection(config):
    config["variants"][0]["risk"]["initial_equity"] = 10 ** 400
    with pytest.raises(ValueError, match="endliche positive Zahl"):
        execution.validate_configuration(config)


def test_finite_zero_costs_despite_overflowing_notional_sum(config):
    for variant in config["variants"]:
        risk = variant["risk"]
        risk.update(sizing_mode="absolute", initial_equity=1e308, max_position_size=1e306,
                    max_total_exposure=1e306, risk_per_trade=1e306, max_daily_drawdown=0)
        variant["costs"] = {"fee_rate": 0, "spread": 0, "slippage": 0}
    result = execution.execute_pilot(EXAMPLES / "synthetic.csv", config)
    for outcome in result.variants:
        assert outcome.status == "succeeded"
        assert all(outcome.evidence["cost_totals"][key] == 0 for key in ("fee", "spread", "slippage", "total"))


def test_cli_private_delivery_and_no_overwrite(tmp_path):
    output = tmp_path / "delivery"
    args = ["--dataset", str(EXAMPLES / "synthetic.csv"), "--config", str(EXAMPLES / "order.json"), "--output", str(output)]
    assert main(args) == 0
    assert {p.name for p in output.iterdir()} == {"report.md", "evidence.json", "agreed-config.json"}
    assert output.stat().st_mode & 0o777 == 0o700
    assert all(p.stat().st_mode & 0o777 == 0o600 for p in output.iterdir())
    original = (output / "evidence.json").read_bytes()
    assert main(args) == 1
    assert (output / "evidence.json").read_bytes() == original
    json.loads(original, parse_constant=lambda x: pytest.fail(x))


@pytest.mark.parametrize("content", ['{"schema":1,"schema":2}', '{"schema":NaN}', '{broken'])
def test_cli_rejects_bad_json_without_output(tmp_path, content):
    path = tmp_path / "order.json"
    path.write_text(content)
    output = tmp_path / "never-created"
    assert main(["--dataset", "unused", "--config", str(path), "--output", str(output)]) == 1
    assert not output.exists()
