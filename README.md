# Liquent — understand liquidity

Modulares Repo-Skeleton (Task **LQ-008**). Dieses Repository enthält **nur**
Struktur, Schnittstellen, Platzhalter und Tests. Es gibt **keine** produktive
Handelslogik und **keine** Live-Ausführung.

> Leitprinzip: Liquent **misst und erklärt** Liquidität. Es trifft keine
> Aussage über garantierte Profitabilität.

## Status

- Modus: **Analyse** (`LIQUENT_MODE=analysis`).
- Phasenfolge (verbindlich, siehe ADR-003): **Backtesting → Paper-Trading →** weitere Schritte.
- Risk-First (ADR-002): Jedes Signal durchläuft zwingend die Risk Engine.

## Architektur

Modularer Aufbau gemäß **ADR-001**. Jede Kerndomäne ist ein eigenständiges
Modul mit klar definierten Schnittstellen; das Domänenmodell ist die
gemeinsame Sprache.

```text
src/liquent/
  domain/        Entitäten (Domain_Model.md)
  data/          Anbindung von Datenquellen (Data_Source_Inventory.md)
  risk/          Risk Engine — Pflichtkomponente, Risk-First (ADR-002)
  backtesting/   Reproduzierbare Läufe + Kostenmodell (ADR-003)
  bot/           Paper-Trading — ausschließlich Simulation
  ui/            Dashboard MVP — Anzeige, keine Order-Funktion
```

### Datenfluss (aus dem Domänenmodell)

```text
MarketData + OrderBookSnapshot
        │
        ▼
  LiquidityMetric  ──►  Signal  ──►  RiskDecision  ──►  Position
                                     (Risk-First,        (nur bei
                                      ADR-002)            approved=True)
```

## Tech-Stack-Vorschlag

- **Sprache:** Python (>= 3.10), Standard-`dataclasses` für die Domäne.
- **Tests:** `pytest`.
- **Repo-Form:** Single Repo mit modularen Paketen unter `src/liquent/`.
  Begründung: ein Modell-/Domänenmodul wird von allen Modulen geteilt, eine
  Single-Repo-Variante hält die gemeinsame Sprache an einem Ort und vermeidet
  Schnittstellen-Drift (ADR-001). Eine spätere Aufteilung in ein Monorepo mit
  `apps/` und `packages/` (vgl. LQ-008-Vorschlag) bleibt möglich.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Konfiguration

Siehe [`.env.example`](.env.example) — enthält ausschließlich
Platzhalter-Schlüsselnamen, keine Werte. Echte Zugangsdaten gehören niemals
ins Repository.

## Sicherheit

- Keine produktive Ausführung, keine echten API-Keys, keine versteckten
  Automatisierungen (kein Scheduler/Cron), keine Netzwerk-Calls zu echten Börsen.
- Risk Engine, Backtesting und Paper-Trading bleiben Pflichtphasen.

## Bezug zum Obsidian-Vault

Fachliche Quelle der Wahrheit ist der Obsidian-Vault `liquent/`. Relevante Specs:

- Domänenmodell — `liquent/04_Architecture/Domain_Model.md`
- Glossar — `liquent/01_Strategy/Glossar_Liquidity.md`
- Datenquellen — `liquent/03_Data/Data_Source_Inventory.md`
- Risk Engine — `liquent/05_Risk/Risk_Engine_Spec.md`
- Backtesting — `liquent/06_Backtesting/Backtesting_Framework_Spec.md`
- Paper-Trading — `liquent/07_Bot/Paper_Trading_Spec.md`
- Dashboard MVP — `liquent/08_UI/Dashboard_MVP_Spec.md`
- ADR-001 / ADR-002 / ADR-003 — `liquent/10_Decisions/`
- Task — `liquent/11_Tasks/LQ-008_Repo_Skeleton.md`
