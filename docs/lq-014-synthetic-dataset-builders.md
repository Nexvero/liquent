# LQ-014 — Synthetic Dataset Builders

> Status: **Phase 1 — Spezifikation / Dokumentation.** Keine Implementierung,
> keine Code-Änderung in `src/`, keine Echtdaten. Plant einen kleinen,
> wiederverwendbaren **Test-/Fixture-Baukasten** für synthetische `MarketData`.

## 1. Ausgangslage

- **LQ-010** hat synthetische v0/v1-Vergleichstests eingeführt
  (`tests/test_synthetic_strategy_comparison.py`).
- **LQ-013** hat strukturiertes Comparison-Reporting eingeführt.
- **Verifizierte Duplikation:** Identische Helfer `_bars(mids)` und
  `class _MidSource` existieren **dreifach** —
  `tests/test_strategy.py`, `tests/test_strategy_v1.py`,
  `tests/test_synthetic_strategy_comparison.py`. Ähnliche In-Memory-Source-Shims
  zusätzlich in `tests/test_reporting.py` und `tests/test_backtesting.py`.
- Für weitere technische Tests sind **wiederverwendbare** Dataset-Builder
  sinnvoll, um diese Duplikate zu konsolidieren.

Nur **synthetische** Daten. Keine Echtdaten, keine Download-/API-/Exchange-Quelle.

### Verifizierte Code-Fakten (WICHTIG — korrigieren die Skizze)

- **`MarketData`** (`src/liquent/domain/models.py`) hat genau die Felder
  `timestamp: datetime`, `bid: float`, `ask: float`, `volume: float` — **kein
  `close`, kein OHLC**. Der Referenzpreis ist `mid = (bid + ask) / 2`.
  - Der bestehende `_bars`-Helfer setzt `bid = m - 0.5`, `ask = m + 0.5`
    (→ `mid = m`, aber `bid != ask`). Der CSV-Lader bildet dagegen
    `close -> bid = ask = close` (→ `bid == ask`). Beide ergeben `mid = m`.
  - Die in der ursprünglichen Skizze genannte Formel „bid=ask=mid" ist also
    **eine** gültige Variante; der bestehende In-Memory-Helfer nutzt jedoch
    `bid=m-0.5/ask=m+0.5`. Für byte-grüne Migration bestehender Tests muss der
    Builder das **bestehende** Verhalten reproduzieren (siehe §6/§10).
- **`DataSource`** (`src/liquent/data/sources.py`) ist ein
  `@runtime_checkable Protocol` mit **`market_data() -> Iterable[MarketData]`**
  **und** **`order_book_snapshots() -> Iterable[OrderBookSnapshot]`** — **nicht**
  `load()`. Der `BacktestRunner` ruft `self.source.market_data()` auf und liest
  `metadata`/`history_report()` defensiv via `getattr` (optional).
- Bestehende In-Memory-Tests nutzen **1-Minuten**-Zeitstempel
  (`datetime(2026, 6, 2, 0, i, tzinfo=utc)`), **nicht** 5-Minuten. Das Timeframe
  ist für die reine Strategie-/Runner-Logik irrelevant (keine Rasterprüfung
  in-memory).

## 2. Ziel

Ein kleiner, wiederverwendbarer Baukasten für synthetische `MarketData`:

- deterministische Mid-Serien,
- definierte `bid`/`ask`-Konvention (mid = (bid+ask)/2),
- feste UTC-Zeitstempel,
- Dataset-Metadaten (Name/Beschreibung),
- wiederverwendbare Muster:
  - `sideways_with_micro_long_breakout`,
  - `sideways_with_micro_short_breakout`,
  - `stair_breakout_for_cooldown`,
  - optional `mixed_breakout_sequence`.

Ziel ist **technische Testbarkeit**, **nicht** Marktrealismus.

## 3. Nicht-Ziele

- keine Echtdaten, kein Download, keine API-/Exchange-Anbindung,
- kein Paper-Trading, kein Live-Trading,
- keine Profitabilitätsbewertung, keine Trading-Empfehlung,
- keine Optimierung, keine Parameter-Suche,
- keine Simulation realer Marktbedingungen, kein Orderbook,
- keine Slippage-/Fee-Modellierung im Dataset (Kosten bleiben CostModel/CLI),
- keine Report-Artefakte committen.

## 4. Ablageort

**Variante A — `tests/helpers/synthetic_data.py`.**
- *Pro:* klar testintern, kein Produktivcode, keine öffentliche Runtime-API,
  geringes Risiko.
- *Contra:* nicht aus `src/` nutzbar.

**Variante B — `src/liquent/testing/synthetic_data.py`.**
- *Pro:* wiederverwendbar für spätere interne Tools, klarer Namespace.
- *Contra:* Produktivpaket wächst um Testhelfer; potenzielle API-Verwirrung.

> **Empfehlung: Variante A — `tests/helpers/synthetic_data.py`.** Begründung:
> Bedarf ist aktuell testgetrieben, kein CLI-/Produktiv-Feature, keine neue
> Runtime-API, minimale Auswirkungen. Bei späterem Bedarf eines internen Tools
> kann kontrolliert nach `src/liquent/testing/` extrahiert werden.

Hinweis Phase 2: `tests/helpers/__init__.py` anlegen (leer), damit
`from tests.helpers.synthetic_data import …` bzw. ein Import über `conftest`/
`sys.path` funktioniert. Genauen Importweg in Phase 2 festlegen (pytest rootdir;
ggf. `tests/helpers/` als Package).

## 5. Vorgeschlagene API

```python
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence
from liquent.domain.models import MarketData

_DEFAULT_START = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)

@dataclass(frozen=True)
class SyntheticDataset:
    name: str
    description: str
    mids: tuple[float, ...]
    market_data: tuple[MarketData, ...]

def make_mid_series_dataset(
    name: str,
    mids: Sequence[float],
    *,
    start: datetime | None = None,        # Default _DEFAULT_START
    interval_minutes: int = 5,            # siehe Kompat-Hinweis §6/§10
    description: str = "",
    half_spread: float = 0.5,             # bid=mid-half_spread, ask=mid+half_spread
) -> SyntheticDataset: ...

def build_sideways_with_micro_long_breakout() -> SyntheticDataset: ...
def build_sideways_with_micro_short_breakout() -> SyntheticDataset: ...
def build_stair_breakout_for_cooldown() -> SyntheticDataset: ...
# optional:
def build_mixed_breakout_sequence() -> SyntheticDataset: ...
```

Regeln:
- `start` deterministisch (Default `2026-01-01T00:00:00+00:00`), `interval_minutes`
  deterministisch, **kein** Zufall, **keine** I/O, **keine** Netzwerkpfade.
- `bid`/`ask` über `half_spread` (Default `0.5`, reproduziert das bestehende
  `bid=m-0.5/ask=m+0.5`); `half_spread=0.0` liefert die CSV-Konvention
  `bid=ask=mid`.
- Die Builder kapseln die bekannten LQ-010-Serien:
  - `sideways_with_micro_long_breakout`: `[100.0]*12 + [100.05, 100.0, 100.0, 102.0, 100.0]`,
  - `sideways_with_micro_short_breakout`: `[100.0]*12 + [99.95, 100.0, 100.0, 98.0, 100.0]`,
  - `stair_breakout_for_cooldown`: `[100.0]*12 + [101.0, 102.0, 103.0, 104.0, 105.0, 106.0]`.

## 6. Datenmodell-Kompatibilität

- **`MarketData`-Felder:** `timestamp, bid, ask, volume` (kein `close`). Der
  Builder setzt `volume` deterministisch (z. B. `1.0`).
- **Runner-Zugriff:** `BacktestRunner.run()` liest `self.source.market_data()`;
  `metadata`/`history_report()` werden defensiv via `getattr` gelesen (für reine
  In-Memory-Quellen nicht nötig).
- **Source-Schnittstelle:** Das `DataSource`-Protocol verlangt **`market_data()`
  und `order_book_snapshots()`**. Der Helfer stellt daher eine In-Memory-Quelle
  bereit, die **beide** Methoden implementiert (nicht `load()`):

```python
class InMemoryMarketDataSource:
    def __init__(self, data: Sequence[MarketData]) -> None: ...
    def market_data(self) -> list[MarketData]: ...          # Kopie der Daten
    def order_book_snapshots(self) -> list: ...             # []
```

  Optional kann sie `metadata` (eine `DataSourceMetadata`) tragen, ist dafür
  aber nicht erforderlich. Sie ersetzt das dreifach duplizierte `_MidSource`.

> **Kompat-Hinweis (verifiziert):** Bestehende Tests verwenden 1-Minuten-Stamps
> ab `2026-06-02T00:00` und `half_spread=0.5`. Um Migrationen **byte-grün** zu
> halten, müssen umgestellte Tests dieselben Werte übergeben
> (`start=datetime(2026,6,2,0,0,tz=utc)`, `interval_minutes=1`, `half_spread=0.5`)
> **oder** ihre Assertions auf Zeitstempel/Stops werden entsprechend angepasst.
> Der API-Default `interval_minutes=5` ist für **neue** Tests gedacht (siehe
> Entscheidungspunkt §10.6).

## 7. Bestehende Tests als Refactoring-Kandidaten

Nur dort umstellen, wo es klaren Mehrwert bringt:

- **`tests/test_synthetic_strategy_comparison.py`** — primärer Kandidat
  (`_bars` + `_MidSource` + Serien lassen sich vollständig auf den Helfer
  stützen).
- optional **`tests/test_strategy_v1.py`** — nur falls direkte Duplikate
  offensichtlich (`_bars`, `_MidSource`), ohne Lesbarkeit zu verschlechtern.
- **Keine** flächendeckende Umstellung aller Tests; `test_strategy.py`,
  `test_reporting.py`, `test_backtesting.py` bleiben unangetastet, solange kein
  klarer Mehrwert.

> Empfehlung Phase 2: Helfer anlegen + `test_synthetic_strategy_comparison.py`
> migrieren; optional 1–2 offensichtliche Duplikate in `test_strategy_v1.py`.
> Kein großes Test-Refactoring.

## 8. Tests für Phase 2 (Helfer selbst)

1. `make_mid_series_dataset` erzeugt deterministische Zeitstempel
   (`start` + `i * interval_minutes`).
2. `mid == (bid + ask) / 2` für jeden Bar (und `half_spread=0.0` → `bid == ask`).
3. `len(market_data) == len(mids)`.
4. `SyntheticDataset` ist immutable (frozen) / wird nicht mutiert.
5. `InMemoryMarketDataSource.market_data()` gibt die Daten stabil (als Kopie)
   zurück; `order_book_snapshots()` liefert `[]`.
6. `sideways_with_micro_long_breakout` hat die erwartete Länge/Struktur.
7. `stair_breakout_for_cooldown` enthält die Folge-Breakouts (streng steigend).
8. Statischer Scan: keine Netzwerk-/Live-/Paper-/Download-Pfade.

Zusätzlich:
9. Bestehende synthetische Strategie-Vergleichstests bleiben grün (Migration).
10. Comparison-Reporting-Tests bleiben grün.
11. Gesamte pytest-Suite bleibt grün.

## 9. Kompatibilität

- Keine Änderung an Produktionscode (bei Variante A; `tests/helpers/`).
- Keine Änderung an Strategien, Runner, RiskEngine, CLI.
- Keine Reportdateien, keine Artefakte unter `reports/`/`data/raw/`.
- Nur Tests/Fixtures; additive Helfer; bestehende Tests bleiben grün (Migration
  ist byte-äquivalent, wenn die bestehenden Stamp-/Spread-Werte übergeben werden).

## 10. Offene Entscheidungspunkte

1. **Helper testintern lassen?** → *Empfehlung: ja* (Variante A).
2. **Dataclass verwenden?** → *Empfehlung: ja* (`SyntheticDataset`, frozen),
   solange übersichtlich.
3. **`InMemoryMarketDataSource` Teil des Helpers?** → *Empfehlung: ja* — Runner-
   Tests brauchen eine `DataSource` (mit `market_data()` **und**
   `order_book_snapshots()`).
4. **Später nach `src/liquent/testing/`?** → *Empfehlung: nur bei Bedarf.*
5. **Random/Seed unterstützen?** → *Empfehlung: nein* — keine Randoms in Phase 2.
6. **(Verifiziert) Default `interval_minutes` / `start` / `half_spread`:** Die
   API-Defaults (`start=2026-01-01`, `interval_minutes=5`, `half_spread=0.5`)
   gelten für **neue** Tests. Die Migration von
   `test_synthetic_strategy_comparison.py` muss `start=2026-06-02`,
   `interval_minutes=1`, `half_spread=0.5` übergeben, um byte-grün zu bleiben
   (oder die betroffenen Zeitstempel-Assertions anpassen). Entscheidung in
   Phase 2.

---

## Phase 2 Implementation Status

Umgesetzt (Variante A, testintern, keine `src/`-Änderung):

- **`tests/helpers/synthetic_data.py`** implementiert (+ `tests/helpers/__init__.py`).
- **`SyntheticDataset`** (frozen dataclass: name/description/mids/market_data).
- **`make_mid_series_dataset(...)`** mit Validierung (`interval_minutes>0`,
  `half_spread>=0`, `mids` nicht leer, `bid>0`); deterministische UTC-Stamps
  (`start + i*interval_minutes`, Default-Start `2026-01-01`); `bid=mid-half_spread`,
  `ask=mid+half_spread`.
- **`InMemoryMarketDataSource`** mit `market_data()` **und**
  `order_book_snapshots()` (Protocol-konform); `metadata`/`history_report` nur
  bei expliziter Übergabe gesetzt (sonst überspringt der Runner sie defensiv).
- **Builder:** `build_sideways_with_micro_long_breakout`,
  `build_sideways_with_micro_short_breakout`, `build_stair_breakout_for_cooldown`
  (kapseln die LQ-010-Serien).
- **Import-Plumbing:** `pyproject.toml` `[tool.pytest.ini_options].pythonpath`
  um `"tests"` ergänzt (`["src", "tests"]`), damit `from helpers.synthetic_data
  import …` greift. Keine `src/`-Änderung, keine Auswirkung auf das gebaute
  Paket (`packages.find where=["src"]`).
- **Migration:** `tests/test_synthetic_strategy_comparison.py` **und**
  `tests/test_strategy_v1.py` von lokalem `_bars`/`_MidSource` auf den Helfer
  umgestellt (`start=2026-06-02`, `interval_minutes=1`, `half_spread=0.5` →
  byte-grün, identische Signalzahlen).
- **Tests:** `tests/test_synthetic_data_helpers.py` (14). Bestehende Tests grün.
- **pytest: 321 passed** (lokale `.venv`).

`src/`, CLI, Runner, RiskEngine, Strategien unverändert. Kein Push.

Keine Echtdaten, keine Profitabilitätsaussage.

---

*Research-/Backtesting-Kontext. Keine Live-/Paper-Trading-Funktion, keine
Exchange-Anbindung, keine Profitabilitätsaussage, keine Handelsempfehlung.*
