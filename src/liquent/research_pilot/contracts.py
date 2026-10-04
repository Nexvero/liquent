"""Shared pilot boundary; engine semantics and existing reports stay unchanged."""

from dataclasses import dataclass
from typing import Any

from liquent.backtesting.reporting import BacktestExperimentSummary
from liquent.domain.models import MarketData

CONFIG_SCHEMA = "liquent.research-pilot.config.v1"
RESULT_SCHEMA = "liquent.research-pilot.result.v1"


@dataclass(frozen=True)
class DataInspection:
    report: dict[str, Any]
    bars: tuple[MarketData, ...]

    @property
    def valid(self) -> bool:
        return self.report["status"] == "valid"


@dataclass(frozen=True)
class VariantResult:
    variant_id: str
    input_fingerprint: str
    status: str  # succeeded, no_signals, failed, blocked_data
    inputs: dict[str, Any]
    summary: BacktestExperimentSummary | None
    evidence: dict[str, Any] | None
    error: str | None = None


@dataclass(frozen=True)
class PilotResult:
    pilot_id: str
    order: dict[str, Any]
    data_quality: dict[str, Any]
    variants: tuple[VariantResult, ...]
    runtime: dict[str, Any]
    configuration: dict[str, Any]


MODEL_LIMITS = (
    "max_total_exposure ist im absoluten Modus eine Stückgrenze, im prozentualen Modus eine Notional-Grenze.",
    "direction_mode ist ein historisches Runner-Label; tatsächlich erlaubt allow_short die Short-Signale.",
    "Ein Trade wird nach einem Datenbalken geschlossen (Close-to-Close).",
    "stop_price dient nur der Positionsgrößenberechnung und löst keinen Stop-Ausstieg aus.",
    "OHLCV-Breakouts verwenden den Schlusskurs als Mittelkurs-Proxy (bid = ask = close).",
    "Das R-Multiple ist derzeit net_pnl / quantity, kein stopbasiertes Rendite-Risiko-Verhältnis.",
    "Der Drawdown-Stopp verwendet den kumulativen Peak-to-Equity-Rückgang ohne Tagesreset.",
    "day_realized_loss bleibt im Runner 0; max_daily_loss ist daher kein wirksamer Verlustschutz.",
    "current_exposure bleibt 0 zwischen Trades; es werden keine überlappenden Positionen modelliert.",
    "Keine Brokeranbindung, Live-Trades, Parametersuche oder Auswahl einer besten Strategie.",
    "Die Ergebnisse beschreiben eine Simulation, keine Handelsempfehlung oder Gewinnzusage.",
)
