# Liquent Data Directory

## Purpose

- Lokale historische Marktdaten für reproduzierbare Backtests.
- Keine Live-Daten.
- Keine API-Keys.
- Keine Zugangsdaten.
- Keine Trading-Ausführung.

## v1 Scope

- Asset-Klasse: Crypto OHLCV.
- Spot bevorzugt.
- Perpetuals nur strukturell kompatibel, ohne Funding/OI in v1.
- Instrumente v1:
  - BTCUSDT
  - ETHUSDT
- Timeframes v1:
  - 5m
  - 1h

## CSV Schema v1

Pflichtspalten:

```text
timestamp,open,high,low,close,volume
```

Regeln:

- `timestamp`: ISO-8601 UTC.
- `open`, `high`, `low`, `close`, `volume`: float.
- Daten streng aufsteigend sortiert.
- Keine doppelten Zeitstempel.
- Keine negativen Preise.
- Keine negative Volume.
- `high >= low`.
- `open` und `close` müssen zwischen `low` und `high` liegen.

## File Naming

Empfohlene Struktur für echte lokale Daten, die **nicht** getrackt werden:

```text
data/raw/crypto/<exchange>/<SYMBOL>/<timeframe>/<SYMBOL>_<timeframe>_<START>_<END>.csv
```

Beispiel:

```text
data/raw/crypto/binance/BTCUSDT/5m/BTCUSDT_5m_2026-05-01_2026-05-31.csv
```

## Minimum History

- 5m: mindestens 30 Tage empfohlen.
- 1h: mindestens 180 Tage empfohlen.

## Gap Policy

v1-Entscheidung:

- Gap-Erkennung wird in einer späteren Phase ergänzt.
- Default-Policy geplant: `reject`.
- Keine automatische Interpolation.
- Keine automatische Auffüllung fehlender Bars.

## Not in v1

Nicht Teil von v1:

- Live-Daten.
- Exchange APIs.
- API-Keys.
- Paper-Trading.
- Live-Trading.
- On-chain-Daten.
- Funding Rate.
- Open Interest.
- Liquidationsdaten.
- Orderbook-/Tickdaten.
- News/Makro-Daten.

## Git Policy

- `data/raw/` wird nicht getrackt.
- `data/processed/` wird nicht getrackt.
- Nur `data/README.md` und die `.gitkeep`-Platzhalter werden getrackt.
- Echte Daten dürfen nicht committed werden.

## Source / License Note

Jede lokal verwendete CSV-Datei muss außerhalb von Git dokumentierbar sein mit:

- Quelle.
- Exportdatum.
- Instrument.
- Timeframe.
- Zeitraum.
- Lizenz/Nutzungsbedingungen, soweit bekannt.

## Current Loader

Aktueller Loader:

```text
src/liquent/data/sources.py
HistoricalFileSource
```

Aktuelles Mapping:

```text
close -> bid = ask = close
```

Hinweis:
OHLC wird in v1 validiert, aber nicht vollständig im Domain-Modell gespeichert.
Echte OHLC-Speicherung ist v2.
