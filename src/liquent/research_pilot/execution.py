"""Exactly three agreed simulations over one validated immutable snapshot."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import platform
import re
from dataclasses import asdict, fields
from pathlib import Path

from liquent.backtesting.reporting import summarize_backtest_result
from liquent.backtesting.runner import BacktestRunner, CostModel
from liquent.data.sources import DataSourceMetadata
from liquent.risk.engine import RiskEngine, RiskLimits
from liquent.strategy import MidBreakoutStrategy, MidBreakoutStrategyV1

from .contracts import CONFIG_SCHEMA, PilotResult, VariantResult
from .data_quality import inspect_dataset

_STRATEGY_FIELDS = {
    "mid-breakout-v0": {"lookback_bars", "stop_distance_pct", "min_strength", "allow_short"},
    "mid-breakout-v1": {"lookback_bars", "stop_distance_pct", "min_strength", "allow_short",
                        "breakout_threshold_pct", "cooldown_bars", "max_signals_per_day"},
}
_STRATEGIES = {"mid-breakout-v0": MidBreakoutStrategy, "mid-breakout-v1": MidBreakoutStrategyV1}
_RISK_FIELDS = {field.name for field in fields(RiskLimits)} | {"initial_equity"}


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def fingerprint(value: object) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode()).hexdigest()


def _keys(value: object, expected: set[str], name: str) -> dict:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{name}: genau diese Felder sind erforderlich: {', '.join(sorted(expected))}")
    return value


def _number(value: object, name: str, *, positive: bool = False) -> None:
    try:
        finite = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite or value < 0 or (positive and value == 0):
        raise ValueError(f"{name}: endliche {'positive' if positive else 'nicht negative'} Zahl erforderlich")


def validate_configuration(configuration: object) -> dict:
    config = copy.deepcopy(configuration)
    _keys(config, {"schema", "order", "dataset", "variants"}, "Auftrag")
    if config["schema"] != CONFIG_SCHEMA:
        raise ValueError("Unbekanntes Pilot-Auftragsformat")
    order = _keys(config["order"], {"reference", "title", "instrument", "price_unit", "data_origin", "assumptions"}, "order")
    for key, value in order.items():
        if not isinstance(value, str) or not value.strip() or len(value) > 2000:
            raise ValueError(f"order.{key}: nicht leerer Text bis 2000 Zeichen erforderlich")
    if order["data_origin"] not in ("synthetic", "customer_provided"):
        raise ValueError("data_origin muss synthetic oder customer_provided sein")
    dataset = _keys(config["dataset"], {"timeframe"}, "dataset")
    if dataset["timeframe"] not in ("1m", "5m", "15m", "1h"):
        raise ValueError("Zeitintervall muss ausdrücklich 1m, 5m, 15m oder 1h sein")
    variants = config["variants"]
    if not isinstance(variants, list) or len(variants) != 3:
        raise ValueError("Genau drei ausdrücklich konfigurierte Varianten sind erforderlich")
    ids: set[str] = set()
    for variant in variants:
        _keys(variant, {"id", "strategy", "strategy_parameters", "risk", "costs", "seed", "hypothesis"}, "Variante")
        identifier = variant["id"]
        if not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", identifier) or identifier in ids:
            raise ValueError("Varianten-IDs müssen eindeutig sein (1–64 Buchstaben, Zahlen, _ oder -)")
        ids.add(identifier)
        if type(variant["seed"]) is not int or not isinstance(variant["hypothesis"], str) or not variant["hypothesis"].strip():
            raise ValueError("seed muss ganzzahlig und hypothesis ein nicht leerer Text sein")
        strategy = variant["strategy"]
        if not isinstance(strategy, str) or strategy not in _STRATEGIES:
            raise ValueError("Nur vorhandene mid-breakout-v0/v1-Strategien sind zugelassen")
        parameters = _keys(variant["strategy_parameters"], _STRATEGY_FIELDS[strategy], "strategy_parameters")
        for key, value in parameters.items():
            if key == "allow_short":
                if type(value) is not bool:
                    raise ValueError("allow_short muss boolesch sein")
            elif key in ("lookback_bars", "cooldown_bars", "max_signals_per_day"):
                if key == "max_signals_per_day" and value is None:
                    continue
                if type(value) is not int:
                    raise ValueError(f"{key} muss ganzzahlig sein")
            else:
                _number(value, key)
        _STRATEGIES[strategy](**parameters)  # use existing strategy validation
        risk = _keys(variant["risk"], _RISK_FIELDS, "risk")
        if risk["sizing_mode"] not in ("absolute", "percent_risk"):
            raise ValueError("sizing_mode muss absolute oder percent_risk sein")
        for key, value in risk.items():
            if key == "sizing_mode":
                continue
            _number(value, key, positive=key in ("initial_equity", "max_position_size", "max_total_exposure"))
            if key == "max_losing_streak" and type(value) is not int:
                raise ValueError("max_losing_streak muss ganzzahlig sein")
        if risk["risk_per_trade_pct"] > 1:
            raise ValueError("risk_per_trade_pct darf höchstens 1 sein (1 = 100 %)")
        if risk["sizing_mode"] == "absolute" and risk["risk_per_trade"] <= 0:
            raise ValueError("absolute erfordert positives risk_per_trade")
        if risk["sizing_mode"] == "percent_risk" and (risk["risk_per_trade_pct"] <= 0 or risk["max_daily_drawdown"] <= 0):
            raise ValueError("percent_risk erfordert positives risk_per_trade_pct und max_daily_drawdown")
        for key, value in _keys(variant["costs"], {"fee_rate", "spread", "slippage"}, "costs").items():
            _number(value, key)
    canonical_json(config)
    return config


def implementation_fingerprint() -> str:
    root = Path(__file__).resolve().parents[1]
    paths = sorted(path for directory in ("research_pilot", "backtesting", "risk", "strategy", "data", "domain")
                   for path in (root / directory).glob("*.py"))
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.relative_to(root).as_posix().encode() + b"\0" + path.read_bytes() + b"\0")
    return "sha256:" + digest.hexdigest()


class _SnapshotSource:
    def __init__(self, inspection, timeframe: str):
        self._inspection = inspection
        self.metadata = DataSourceMetadata(timeframe=timeframe, source_path=inspection.report["dataset_fingerprint"])

    def market_data(self):
        return self._inspection.bars

    def order_book_snapshots(self):
        raise NotImplementedError("OHLCV enthält keine Orderbuchdaten")


def effective_risk(risk: dict) -> dict[str, str]:
    percent = risk["sizing_mode"] == "percent_risk"
    return {
        "sizing_mode": risk["sizing_mode"],
        "initial_equity": "Startkapital in vereinbarten Simulationseinheiten",
        "max_position_size": "Wirksame Obergrenze pro Trade in Stück/Einheiten",
        "max_total_exposure": ("Wirksame Notional-Kappe: Größe × Referenzpreis; Exposure im Runner 0"
                               if percent else "Wirksame Stückgrößenkappe; Exposure im Runner 0"),
        "risk_per_trade": "In diesem Modus ignoriert" if percent else "Absolute Ausgangsgröße, kein Geldrisiko oder Verlustlimit",
        "risk_per_trade_pct": "Equity-Anteil / Stop-Distanz vor Kappen; keine Stop-Ausführung" if percent else "In diesem Modus ignoriert",
        "max_position_notional": "Notional-Kappe, bei 0 deaktiviert" if percent else "In diesem Modus ignoriert",
        "max_daily_drawdown": "Kumulativer Drawdown-Stopp; kein Tagesreset" + ("; bei 0 deaktiviert" if not percent else ""),
        "max_daily_loss": "Kein wirksamer Verlustschutz: day_realized_loss bleibt 0" if percent else "In diesem Modus ignoriert",
        "max_losing_streak": "Pause bei Verlustserie, bei 0 deaktiviert" if percent else "In diesem Modus ignoriert",
    }


def execute_pilot(dataset: Path, configuration: object) -> PilotResult:
    config = validate_configuration(configuration)
    inspection = inspect_dataset(dataset, config["dataset"]["timeframe"])
    runtime = {"python": platform.python_version(), "implementation_fingerprint": implementation_fingerprint(),
               "code_scope": "liquent/{research_pilot,backtesting,risk,strategy,data,domain}/*.py"}
    pilot_id = fingerprint({"configuration": config, "dataset": inspection.report["dataset_fingerprint"], "runtime": runtime})
    outcomes = []
    for variant in config["variants"]:
        inputs = copy.deepcopy(variant)
        inputs.update(dataset_fingerprint=inspection.report["dataset_fingerprint"], timeframe=config["dataset"]["timeframe"])
        input_id = fingerprint({"inputs": inputs, "runtime": runtime})
        if not inspection.valid:
            outcomes.append(VariantResult(variant["id"], input_id, "blocked_data", inputs, None, None,
                                          "Nicht ausgeführt: Datenprüfung abgewiesen"))
            continue
        try:
            risk = dict(variant["risk"])
            initial_equity = risk.pop("initial_equity")
            result = BacktestRunner(
                source=_SnapshotSource(inspection, inputs["timeframe"]),
                risk_engine=RiskEngine(RiskLimits(**risk)), cost_model=CostModel(**variant["costs"]),
                strategy=_STRATEGIES[variant["strategy"]](**variant["strategy_parameters"]),
                seed=variant["seed"], initial_equity=initial_equity, hypothese=variant["hypothesis"],
            ).run()
            # Infinite profit_factor is a defined engine metric, not a failed run.
            numbers = [result.starting_equity, result.ending_equity, *result.equity_curve,
                       *(value for trade in result.trades for value in (trade.entry_price, trade.exit_price, trade.quantity,
                          trade.gross_pnl, trade.net_pnl, trade.costs, trade.r_multiple))]
            if not all(math.isfinite(value) for value in numbers):
                raise ValueError("nonfinite simulation output")
            if any(not math.isfinite(value) for key, value in result.metrics.items() if key != "profit_factor"):
                raise ValueError("nonfinite metric output")
            cost = variant["costs"]
            # Compute each side before aggregation: the notional sum can overflow
            # while the actual fees remain finite (e.g. all rates are zero).
            costs = {"fee": sum(abs(price * trade.quantity) * cost["fee_rate"]
                                 for trade in result.trades for price in (trade.entry_price, trade.exit_price)),
                     "spread": sum(abs(trade.quantity) * cost["spread"]
                                   for trade in result.trades for _ in range(2)),
                     "slippage": sum(abs(price * trade.quantity) * cost["slippage"]
                                      for trade in result.trades for price in (trade.entry_price, trade.exit_price)),
                     "total": sum(trade.costs for trade in result.trades),
                     "gross_pnl": sum(trade.gross_pnl for trade in result.trades), "net_pnl": sum(trade.net_pnl for trade in result.trades)}
            if not all(math.isfinite(value) for value in costs.values()):
                raise ValueError("nonfinite cost totals")
            summary = summarize_backtest_result(result, title=variant["id"],
                strategy_metadata={"family": "breakout", "key": variant["strategy"], "name": result.parameters["strategy"],
                                   "params": variant["strategy_parameters"]}, cost_metadata=cost)
            notes = {key: "Nicht endlicher Modellwert; im JSON null, keine belastbare Schätzung" for key, value in result.metrics.items() if not math.isfinite(value)}
            if result.number_of_trades == 0:
                notes["no_trades"] = "Keine Trades: Kennzahl-Defaults des Runners sind keine Leistungsnachweise"
            evidence = {"effective_risk": effective_risk(variant["risk"]), "runner_parameters": result.parameters,
                        "trades": [asdict(trade) for trade in result.trades], "equity_curve": list(result.equity_curve),
                        "cost_totals": costs, "metric_notes": notes}
            outcomes.append(VariantResult(variant["id"], input_id, "no_signals" if result.parameters["signals_total"] == 0 else "succeeded",
                                          inputs, summary, evidence))
        except Exception as exc:
            # No customer data, paths, or arbitrary exception message in deliverables.
            outcomes.append(VariantResult(variant["id"], input_id, "failed", inputs, None, None,
                                          f"Simulation fehlgeschlagen ({type(exc).__name__}); technische Ursachenprüfung erforderlich"))
    return PilotResult(pilot_id, config["order"], inspection.report, tuple(outcomes), runtime, config)
