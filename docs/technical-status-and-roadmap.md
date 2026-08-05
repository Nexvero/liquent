# Liquent — Technical Status and Roadmap

> Konsolidierte, rein **technische** Status- und Roadmap-Übersicht (LQ-017
> Phase 1). Keine Implementierung, keine Echtdaten, **keine
> Profitabilitätsbewertung**, keine Trading-Empfehlung.

## 1. Aktueller Stand (verifiziert)

- **Letzter Commit:** `9976fe4` — *security: time-box Python vulnerability exception*.
- **Teststand:** **861 passed** (lokale `.venv`, `python -m pytest`).
- **Branch:** `architecture/lq-053-platform-boundaries`, aktuell 7 Commits vor
  und 0 Commits hinter `origin/main`; Pull Request `#1` ist offen.
- **Working Tree:** sauber; Branch und GitHub-Remote sind synchron.
- **Doku-Inventar:** historische Research-Spezifikationen plus fortlaufende
  Plattform-Entscheidungen und Betriebsverträge bis LQ-067.

## 2. Abgeschlossene Foundations / Schritte

| ID | Thema | Kurzbeschreibung (technisch) |
|---|---|---|
| LQ-003 | Data Foundation | `HistoricalFileSource`, OHLCV-Validierung, Gap-/History-Reports |
| LQ-004 | Risk Foundation | `RiskEngine`, `percent_risk`-Sizing (Pflicht-`stop_price`, fail-safe) |
| LQ-005 | Backtesting Foundation | `BacktestRunner` (Close-to-Close, deterministisch), Metrics, Reporting |
| LQ-006 | MidBreakoutStrategy v0 | erste regelbasierte Mid-/Close-Breakout-Strategie |
| LQ-007 | CLI + Echtdatenlauf | lokales CLI; `--gap-policy`/`--max-gaps`; manueller 30-Tage-CSV-Lauf |
| LQ-008 | MidBreakoutStrategyV1 | additive v1 (Breakout-Threshold, Cooldown), v0 als Regressionsbasis |
| LQ-009 | CLI Strategy Selection | `--strategy v0\|v1`, v1-only-Gating, Sentinel-Defaults |
| LQ-010 | Synthetic Strategy Comparison | deterministische v0/v1-Vergleichstests |
| LQ-011 | Strategy Metadata Reporting | additives `strategy_metadata` in Report/Dict |
| LQ-012 | CLI Cost Model Parameters | `--fee-rate`/`--spread`/`--slippage`; `cost_metadata` |
| LQ-013 | Structured Synthetic Comparison Reporting | `comparison_reporting.py` (Markdown-Vergleich) |
| LQ-014 | Synthetic Dataset Builders | `tests/helpers/synthetic_data.py` (Builder, In-Memory-Source) |
| LQ-015 | max_signals_per_day | aktives UTC-Tageslimit in v1 + CLI-Flag |
| LQ-016 | Synthetic Comparison Report (max_signals_per_day) | kontrollierter Vergleichstest (None/1/2 → 5/1/2) |

*Keine Profitabilitätsbewertung — die Tabelle beschreibt ausschließlich
technischen Funktionsumfang.*

## 3. Strategie-Stand

### MidBreakoutStrategy v0 (`src/liquent/strategy/mid_breakout.py`)

- **Regressionsbasis, unverändert.**
- Default `lookback_bars=3`; **kein** Threshold, **kein** Cooldown, **kein**
  `max_signals_per_day`.
- Strikter Breakout (`mid > max(window)` / `< min(window)`), `strength` fix `1.0`.

### MidBreakoutStrategyV1 (`src/liquent/strategy/mid_breakout_v1.py`)

Parameter (Defaults):
- `lookback_bars=12`
- `stop_distance_pct=0.01`
- `breakout_threshold_pct=0.001`
- `cooldown_bars=3`
- `allow_short=True`
- `min_strength=0.0`
- `max_signals_per_day=None`

Technische Gates / Eigenschaften:
- **Breakout-Threshold:** LONG `mid > prev_high·(1+thr)`, SHORT
  `mid < prev_low·(1-thr)`; `thr=0.0` reproduziert v0.
- **Cooldown:** nach erzeugtem Signal `cooldown_bars` Bars überspringen.
- **Tageslimit `max_signals_per_day`:** optional, je UTC-Tag
  (`timestamp.date()`); `None` = deaktiviert; letztes Gate vor dem Append; ein
  dadurch verworfenes Signal löst **keinen** Cooldown aus.
- **Kein Signal auf dem letzten Bar** (Close-to-Close braucht Folge-Bar).
- **Stop-Logik:** `mid·(1∓stop_distance_pct)` (percent_risk-konform).
- **`strength`/`min_strength`:** reiner Signalfilter; RiskEngine skaliert
  **nicht** über `strength`.
- **Keine Positionslogik;** **kein** echter Stop-Exit im Runner
  (`stop_price` dient nur dem Sizing — Exit ist stets der Folge-Bar-Mid).

## 4. CLI-Stand (`src/liquent/cli/backtest_mid_breakout.py`)

- `--strategy v0|v1` (Default **v0**, byte-identisch reproduzierbar).
- **v1-only-Gating** (bei v0 hart abgelehnt): `--breakout-threshold-pct`,
  `--cooldown-bars`, `--max-signals-per-day`.
- Gemeinsam: `--lookback-bars`, `--stop-distance-pct`, `--min-strength`,
  `--allow-short`.
- **Kostenmodell CLI-parametrisierbar:** `--fee-rate`, `--spread`, `--slippage`
  (Default `0.0` = frictionless).
- **Strategy- und Cost-Metadata** werden in den Markdown-Report geschrieben
  (`## Strategy`, `## Strategy Parameters`, `## Cost Model`).
- **Keine** Live-/Paper-/Exchange-/Netzwerk-/Download-Pfade (statisch getestet);
  fixer `sizing_mode="percent_risk"`; deterministischer Output.

## 5. Reporting-Stand

**Einzelreport (`src/liquent/backtesting/reporting.py`):**
- additives, optionales `strategy_metadata` (family/key/name/params),
- additives, optionales `cost_metadata` (fee_rate/spread/slippage),
- `BacktestResult.parameters` bleibt **skalar** (`str|int|float|bool`) — Metadaten
  liegen in separaten, optionalen Summary-Feldern (Default `None` →
  byte-identisch).

**Comparison-Reporting (`src/liquent/backtesting/comparison_reporting.py`):**
- `normalize_comparison` (stabile Defaults/Feldreihenfolge),
  `render_comparison_markdown` (**nur String, kein I/O**),
- technische Vergleichstabellen (Signals/Trades/Approved/Rejected je Variante),
- **keine** Bewertungssprache (kein Ranking/winner/better/worse),
- **kein** `ending_equity` im Comparison-Report.

## 6. Test-/Synthetic-Stand

- `tests/helpers/synthetic_data.py`:
  - `SyntheticDataset` (frozen), `make_mid_series_dataset` (deterministische
    UTC-Stamps, `bid=mid∓half_spread`, Validierung),
  - `InMemoryMarketDataSource` (`market_data()` + `order_book_snapshots()`),
  - Builder: `build_sideways_with_micro_long_breakout`,
    `build_sideways_with_micro_short_breakout`,
    `build_stair_breakout_for_cooldown`.
- Synthetische Tests decken ab: v0/v1-Vergleich, Threshold, Cooldown,
  `max_signals_per_day` (Strategie + CLI + Comparison-Report), Strategy-/Cost-
  Metadata-Reporting, CostModel-CLI, CLI-Gating, Comparison-Rendering.
- **Importweg:** `pyproject.toml` `pytest.pythonpath = ["src", "tests"]`
  (Helfer als `helpers.*`).

## 7. Sicherheits- und Projektgrenzen (bindend)

- keine Echtdaten in Tests/Commits; keine Reports committen
  (`reports/*` git-ignoriert außer `reports/README.md`; `data/raw|processed`
  ignoriert),
- keine API-Keys/Zugangsdaten, keine Netzwerk-Calls, kein Download,
- keine Exchange-Anbindung, kein Paper-Trading, kein Live-Trading,
- keine Profitabilitätsbewertung, keine Trading-Empfehlung,
- keine Optimierung/Parameter-Suche ohne separate Spezifikation.

## 8. Offene technische Themen (priorisiert)

### LQ-018 — CLI Help/Examples Review
CLI-Hilfe, README-Beispiele und Parametererklärungen konsolidieren. **Keine** neue
Logik — reiner Doku-/UX-Schritt.

### LQ-019 — JSON/Structured Output Spezifikation
Prüfen, ob Reports neben Markdown optional JSON/Dict liefern sollen
(`summary_to_dict`/`normalize_comparison` sind bereits JSON-fähig). **Keine**
Report-Artefakte committen.

### LQ-020 — Runner Stop-Exit Spezifikation
Aktuell nutzt der Runner `stop_price` nur fürs Sizing; Exit ist Folge-Bar-Mid.
Separat spezifizieren, ob ein **echter** Stop-Exit modelliert werden soll
(Runner-Änderung, nicht Strategie).

### LQ-021 — Position State / Holding Period Spezifikation
Aktuell 1-Bar-Haltedauer (Close-to-Close). Positionszustand/variable Haltedauer
wäre eine **Runner**-Änderung, keine Strategieänderung.

### LQ-022 — Cost Model Validation Erweiterung
Optional Obergrenzen/Warnungen für `fee_rate`/`spread`/`slippage`. **Keine**
Marktannahmen, nur technische Plausibilitätsgrenzen.

### LQ-023 — Controlled Real-Data Re-Run Plan
Nur **Planung**, keine Ausführung. Echtdatenlauf ausschließlich nach expliziter
Freigabe, manuell bereitgestellt. **Keine** Profitabilitätsbewertung.

## 9. Empfohlene nächste Phase

> **Empfehlung: LQ-018 — CLI Help/Examples Review.**
>
> Begründung: Die CLI ist inzwischen deutlich gewachsen
> (`--strategy`, v1-only-Parameter, Kostenmodell). Vor neuen
> Backtesting-Mechaniken sollten CLI-Hilfe, README und Beispiele konsistent sein.
> Reiner Doku-/UX-Schritt — kein Risiko für Strategie/Runner/RiskEngine.

## 10. Nicht-Ziele dieser Konsolidierung

- keine Implementierung, keine Strategieänderung, keine CLI-Änderung,
- keine Runner-/RiskEngine-Änderung, keine Tests ändern,
- keine Echtdaten, keine Reports,
- kein Commit ohne Freigabe, kein Push.

## 11. Visual Preview

- Visual Preview docs index: `docs/visual-preview-index.md`
- Quickstart: `docs/lq-025-visual-preview-quickstart.md`
- Stabilization checkpoint: `docs/lq-027-visual-preview-stabilization-checkpoint.md`
- Controlled Streamlit smoke-test checklist: `docs/lq-028-controlled-streamlit-smoke-test-checklist.md`
- Review pause / next-track decision: `docs/lq-029-visual-preview-review-pause-next-track.md`
- Manual Streamlit smoke-test execution plan: `docs/lq-030-manual-streamlit-smoke-test-execution-plan.md`
- Manual Streamlit smoke-test result template / execution gate: `docs/lq-031-manual-streamlit-smoke-test-result-template.md`
- Streamlit optional install decision / no-execution checkpoint: `docs/lq-032-streamlit-install-decision-no-execution-checkpoint.md`
- Optional Streamlit install execution plan: `docs/lq-033-optional-streamlit-install-execution-plan.md`
- Visual Preview documentation freeze / milestone summary: `docs/lq-034-visual-preview-documentation-freeze.md`
- Status: local visual preview checkpoint documented;
  LQ-028 documents the manual smoke-test procedure (no automation, no deployment);
  Visual Preview reached a stable local checkpoint; next track should be chosen explicitly;
  next step is manual UI smoke-test execution, not new feature work;
  execution gate and neutral result template documented; no UI execution yet;
  current recommended decision is no execution unless optional Streamlit install is separately approved;
  optional Streamlit install plan documented; installation still requires separate approval;
  Visual Preview documentation milestone reached;
  no further Visual Preview gate phases unless installation, UI execution, or new feature track is approved;
  no live/paper/exchange/API functionality.

## 12. BacktestRunner / Trade-Lifecycle Integration

- LQ-035 specification: `docs/lq-035-backtest-runner-trade-lifecycle-integration.md`
- Status:
  - existing Runner/RiskEngine/CostModel/Reporting stack verified
  - Visual Preview remains frozen
  - next suggested action: Runner regression test plan, no UI integration
- LQ-036 regression test plan: `docs/lq-036-backtest-runner-regression-test-plan.md`
- Status:
  - regression test plan finalized
  - next suggested action: add regression tests only, no implementation unless
    failing tests reveal a documented mismatch
- LQ-037 regression tests: `tests/test_backtest_runner_regressions.py`
- Status:
  - regression tests implemented
  - existing Runner behavior locked
  - no production logic changes
  - next suggested action: either commit/push this test layer or plan a targeted
    Runner lifecycle decision separately
- LQ-038 runner lifecycle / stop-exit semantics: `docs/lq-038-runner-lifecycle-stop-exit-semantics.md`
- Status:
  - lifecycle decision finalized
  - current decision: keep Close-to-Close and stop_price sizing-only
  - no Stop-Exit without separate specification
- LQ-039 explicit exit reason / stop-exit specification: `docs/lq-039-explicit-exit-reason-stop-exit-spec.md`
- Status:
  - exit_reason / stop-exit specification finalized
  - no implementation
  - Stop-Exit remains out of current Runner contract until separately approved
- LQ-040 runner lifecycle implementation decision / pause checkpoint: `docs/lq-040-runner-lifecycle-implementation-decision.md`
- Status:
  - recommended decision: pause Runner lifecycle implementation
  - current contract remains Close-to-Close and stop_price sizing-only
  - exit_reason / Stop-Exit stays a future track requiring separate approval
- LQ-041 risk engine hardening docs + regression coverage: `docs/lq-041-risk-engine-hardening.md`
- Status:
  - RiskEngine contract documented
  - 13 additional regression tests
  - no engine production logic changes
  - Runner Lifecycle stays paused per LQ-040
- LQ-042 cost model / metrics hardening docs + regression coverage: `docs/lq-042-cost-metrics-hardening.md`
- Status:
  - CostModel / Metrics contract documented
  - 12 additional regression tests
  - no production logic changes
  - Runner Lifecycle stays paused per LQ-040
- LQ-043 reporting / comparison stabilization docs + regression coverage: `docs/lq-043-reporting-comparison-stabilization.md`
- Status:
  - Reporting / Comparison contract documented
  - 10 additional regression tests
  - no production logic changes
  - no ranking / evaluation / recommendation logic
  - Runner Lifecycle stays paused per LQ-040
- LQ-044 cli output polish docs + regression coverage: `docs/lq-044-cli-output-polish.md`
- Status:
  - CLI output / validation / exit-code contract documented
  - 13 additional regression tests
  - no production logic changes
  - no new CLI flags / defaults / exit codes
  - Runner Lifecycle stays paused per LQ-040
- LQ-045 strategy fixtures / scenario coverage docs + regression coverage: `docs/lq-045-strategy-fixtures-scenario-coverage.md`
- Status:
  - fixture / scenario catalog documented
  - 4 additional behavior-locks (high existing coverage, deliberately small scope)
  - no production logic changes
  - no fixture changes; synthetic/local data only
  - Runner Lifecycle stays paused per LQ-040
- LQ-046 data-source / CSV-loader hardening docs + regression coverage: `docs/lq-046-data-source-csv-loader-hardening.md`
- Status:
  - DataSource / CSV-loader contract documented
  - 4 additional behavior-locks (high existing coverage, deliberately small scope)
  - no production logic changes
  - no fixture changes; local fixtures and tmp_path only
  - Runner Lifecycle stays paused per LQ-040
- LQ-047 domain model hardening: `docs/lq-047-domain-model-hardening.md`
  - Tests: `tests/test_domain_model_hardening.py`
  - Status: domain behavior locks implemented; no production logic changes
  - Runner Lifecycle stays paused per LQ-040
- LQ-048 domain model invariants / validation decision: `docs/lq-048-domain-model-invariants-validation-decision.md`
  - Status:
    - recommendation: document invariants; no runtime validation in domain models
    - future validation should prefer separate validator functions
    - no production logic changes
  - Runner Lifecycle stays paused per LQ-040
- LQ-049 domain model validator layer decision / implementation plan: `docs/lq-049-domain-model-validator-layer-plan.md`
  - Status:
    - recommendation: plan only; no validator implementation yet
    - future validator layer should stay outside frozen dataclasses
    - no production logic changes
  - Runner Lifecycle stays paused per LQ-040
- LQ-050 domain model validation track freeze / next-track decision: `docs/lq-050-domain-model-validation-track-freeze.md`
  - Status:
    - recommended decision: freeze Domain Validation Track
    - no validator implementation yet
    - future validator layer remains separate future track
    - no production logic changes
  - Runner Lifecycle stays paused per LQ-040
- LQ-051 liquent milestone review / next-track decision: `docs/lq-051-liquent-milestone-review-next-track.md`
  - Status:
    - milestone review finalized
    - recommended next step: pause/architecture review or product/use-case definition
    - no production logic changes
- LQ-052 architecture review checkpoint: `docs/lq-052-architecture-review-checkpoint.md`
  - Status:
    - architecture review finalized
    - frozen tracks and parked future specs identified
    - no production logic changes
- LQ-053 platform boundaries and evolution: `docs/lq-053-platform-boundaries-and-evolution.md`
  - Status:
    - Liquent Platform PRD gegen den vorhandenen Research-Kern abgeglichen
    - modularer Monolith als evolutionäre Zielgrenze festgelegt
    - Plattformobjekte, Ausführungsgrenzen und vertikale MVP-Slices definiert
    - keine Technologieauswahl und keine Produktionslogik geändert
- LQ-054 platform foundation quality and operations: `docs/lq-054-platform-foundation-quality-and-operations.md`
  - Status:
    - SLOs, Health/Readiness, Recovery und Observability definiert
    - Single-VPS-Kapazitäts- und Sicherheitsgrenzen festgelegt
    - Slice-0-Go-Live-Gates und LQ-055-Technologiekriterien dokumentiert
    - keine Technologieauswahl und keine Produktionslogik geändert
- LQ-055 start stack technology decision: `docs/lq-055-start-stack-technology-decision.md`
  - Status:
    - Python/FastAPI, React/Vite, PostgreSQL 18 und Docker Compose ausgewählt
    - PostgreSQL-basierte Research Jobs ohne initialen Message Broker festgelegt
    - Prometheus/Grafana, Restic/OVH Object Storage und GitHub CI/CD entschieden
    - Repository-Zielstruktur und LQ-056-Implementierungsfolge dokumentiert
    - keine Runtime-Abhängigkeit oder Produktionskonfiguration geändert
- LQ-056 repository foundation and architecture guardrails: `docs/lq-056-repository-foundation-architecture-guardrails.md`
  - Status:
    - additive `liquent_platform`-Paketstruktur angelegt
    - frameworkunabhängige Application-Ports für Zeit, Identitäten und Artefakte definiert
    - AST-basierte Architekturtests schützen Research-, Application-, Adapter- und Transportgrenzen
    - keine Runtime-Abhängigkeit, HTTP-App, Datenbank oder Tradingverbindung ergänzt
    - nächster Schritt: LQ-057 Slice-0-Compose- und Konfigurationsvertrag
- LQ-057 Slice-0 Compose and configuration contract: `docs/lq-057-slice-0-compose-configuration-contract.md`
  - Status:
    - Rollen für Control Plane, Research Worker, PostgreSQL und Observability deklariert
    - öffentliche Portfreigaben ausgeschlossen; vorhandene isolierte VPS-Netze referenziert
    - Image-Digests, Runtimekonfiguration und dateibasierte Secrets getrennt
    - Ressourcenobergrenzen, persistente Volumes und lokale Logrotation festgelegt
    - noch kein Image gebaut, Dienst gestartet oder VPS verändert
    - nächster Schritt: LQ-058 minimale Control Plane mit Health/Readiness
- LQ-058 minimal control plane with health and readiness: `docs/lq-058-minimal-control-plane-health-readiness.md`
  - Status:
    - FastAPI-App-Factory und Uvicorn-Entrypoint implementiert
    - fail-fast Production-Konfiguration mit Pydantic Settings umgesetzt
    - getrennte Liveness-/Readiness-Endpunkte mit 200/503-Vertrag ergänzt
    - keine Produkt-API, Datenbankverbindung oder Tradingfunktion aktiviert
    - nächster Schritt: LQ-059 PostgreSQL-Persistenz und Migration Gate
- LQ-059 PostgreSQL persistence and migration gate: `docs/lq-059-postgresql-persistence-migration-gate.md`
  - Status:
    - SQLAlchemy/Psycopg-Engine-Adapter und Alembic-Baseline implementiert
    - separates Compose-Migration-Gate vor Control Plane und Worker ergänzt
    - Readiness an Datenbankerreichbarkeit und exakte Head-Revision gebunden
    - keine fachlichen Tabellen, Produktendpunkte oder Tradingverbindungen ergänzt
    - nächster Schritt: LQ-060 Observability und externe Health-Prüfung
- LQ-060 observability and external health verification: `docs/lq-060-observability-external-health.md`
  - Status:
    - strukturierte JSON-Logs und validierte Correlation IDs implementiert
    - begrenzte Request-/Latenz-/Readiness-/Buildmetriken ergänzt
    - interner Prometheus-Endpunkt und HTTPS-only Smoke-Check implementiert
    - keine externe Überwachung aktiviert und kein VPS verändert
    - nächster Schritt: LQ-061 Backup-/Restore-Nachweis und Runbook
- LQ-061 backup, restore and recovery contract: `docs/lq-061-backup-restore-contract.md`
  - Status:
    - Restic-/PostgreSQL-Backup, getrennte Retention und sichere Restore-Verifikation implementiert
    - dateibasierte Secrets und optionales Compose-Operations-Profil ergänzt
    - Recovery-Runbook mit RPO/RTO- und Incident-Gates dokumentiert
    - echter OVH-Offsite-Snapshot und isolierter Vollrestore bleiben Go-live-Gate
    - kein VPS oder externer Bucket verändert
- LQ-062 CI quality and release artifact gate: `docs/lq-062-ci-quality-release-artifact-gate.md`
  - Status:
    - read-only GitHub-Actions-Workflow mit Test- und Wheel-Gate angelegt
    - CI-/Build-Abhängigkeiten exakt versioniert und externe Actions SHA-gepinnt
    - Wheel-Inhalt, Entrypoints, Migrationen und SHA-256 werden geprüft
    - Test- und Wheel-Gate im Pull Request erfolgreich ausgeführt; Branch Protection bleibt externes Gate
    - nächster Schritt: LQ-063 OCI-Image- und Container-Smoke-Gate
- LQ-063 OCI image and container smoke gate: `docs/lq-063-oci-image-container-smoke-gate.md`
  - Status:
    - mehrstufiges Application-Image mit digest-gepinntem Basisimage definiert
    - non-root Runtime, Liveness-Healthcheck und OCI-Commitmetadaten festgelegt
    - gehärteter Container-Smoke-Test als drittes CI-Gate ergänzt
    - Image-Build, Image-Vertrag und gehärteter Smoke-Test auf GitHub erfolgreich
    - nächster Schritt: LQ-064 SBOM-, Vulnerability- und Provenance-Gate
- LQ-064 SBOM, vulnerability and provenance gate: `docs/lq-064-sbom-vulnerability-provenance-gate.md`
  - Status:
    - SPDX-JSON-SBOM und fail-closed Struktur-/Identitätsprüfung ergänzt
    - Grype-Gate stoppt bei reparierbaren High/Critical-Funden; ungefixte Funde bleiben als Evidenz sichtbar
    - kurzlebige Supply-Chain-Evidenz und main-only GitHub-Provenance definiert
    - echter SBOM-/Vulnerability-Scan im Pull Request erfolgreich; Attestation bleibt main-only
    - nächster Schritt: LQ-065 kontrollierter GHCR-Release-/Promotionvertrag
- LQ-065 controlled GHCR release and promotion contract: `docs/lq-065-controlled-ghcr-release-promotion.md`
  - Status:
    - manueller, environment-geschützter Releaseworkflow angelegt
    - nur erfolgreiche main-Push-Quality-Commits als Kandidaten zugelassen
    - erneuter Smoke-/SBOM-/Vulnerability-Check vor Registry-Login erzwungen
    - commitqualifizierter Tag, Registry-Digest-Attestation und Evidenzmanifest definiert
    - Environment-Reviewer, erster GHCR-Release und VPS-Promotion bleiben offen
    - nächster Schritt: LQ-066 kontrollierte Staging-Promotion und Rollback
- LQ-066 controlled staging promotion and rollback: `docs/lq-066-staging-promotion-rollback.md`
  - Status:
    - digestgebundener, mutierungsfreier Preflight und operatorgesteuerte Promotion implementiert
    - Host-Lock, Laufjournal, Backup-Evidenz und externer HTTPS-Health-Nachweis ergänzt
    - Fehlerpfad stellt vorheriges Application-Image wieder her
    - Datenbankmigrationen werden bewusst nicht automatisch zurückgedreht
    - Staging-Bootstrap, Domain/TLS und echter Promotionslauf bleiben offen
    - nächster Schritt: LQ-067 Initial-Staging-Bootstrap und Edge-Routing-Plan
- LQ-067 initial staging bootstrap and edge routing: `docs/lq-067-initial-staging-bootstrap-edge-routing.md`
  - Status:
    - einmaliger Initial-Staging-Bootstrap mit expliziter Bestätigung implementiert
    - DNS-/TLS-/Release-/Backup-Preflight und Zertifikat-Key-Abgleich ergänzt
    - Edge veröffentlicht ausschließlich HTTPS-Liveness; alle anderen Pfade bleiben geschlossen
    - lokaler Offline-Preflight ist testbar, echter Online-Lauf bleibt offen
    - nächster Schritt: LQ-068 Git-Checkpoint und erster GitHub-CI-Lauf
- LQ-068 git checkpoint and first CI readiness: `docs/lq-068-git-checkpoint-ci-readiness.md`
  - Status:
    - gesamter LQ-053-bis-LQ-067-Checkpoint lokal auditiert
    - Secret-, Symlink-, Großdatei-, Syntax-, Dependency- und Regression-Gates grün
    - Branch ist committed, gepusht und als Pull Request `#1` reviewbar
    - erster realer GitHub-CI-Lauf inklusive Container-/Supply-Chain-Gates grün
    - Merge, Branch Protection, Release und Deployment bleiben externe Freigaben
- LQ-069 release environment governance: `docs/lq-069-release-environment-governance.md`
  - Status:
    - GitHub Environment `registry-release` angelegt und explizit auf `main` begrenzt
    - keine Environment-Secrets oder -Variablen hinterlegt
    - Required Reviewer bleibt bis zu einem unabhängigen zweiten Maintainer offen
    - erster GHCR-Release und jede VPS-Promotion benötigen separate Freigaben
- LQ-070 release readiness evidence: `docs/lq-070-release-readiness-evidence.md`
  - Status:
    - read-only Kandidatenprüfung von Release-Metadaten und erfolgreichem `main`-Quality-Lauf ergänzt
    - maschinenlesbarer Nachweis markiert Publication und Deployment ausdrücklich als nicht autorisiert
    - vorgeschlagener erster Kandidat `0.1.0` bleibt bis zur separaten Releasefreigabe unveröffentlicht
- LQ-071 local research product workflow: `docs/lq-071-local-research-product-workflow.md`
  - Status:
    - Slice-1-Happy-Path von Workspace bis Evidence Summary definiert
    - Produktobjekte, Jobzustände, Startgrenze sowie Fehler- und Leerezustände festgelegt
    - Broker, Automation, Empfehlungen und Technologieauswahl bleiben außerhalb dieses Slices
    - nächste Sequenz: LQ-072 Identitäten/Lifecycle, danach Anwendungsgrenze und In-Memory-Workflow
- LQ-072 research identity and lifecycle: `docs/lq-072-research-identity-lifecycle.md`
  - Status:
    - vier semantische String-ID-Typen ohne eigenes ID-Framework ergänzt
    - kleine explizite Research-Job-Übergangstabelle implementiert
    - terminale Zustände sind unveränderlich; ungültige Sprünge scheitern fail-closed
    - keine Persistenz, Events, State-Machine-Abstraktion oder neue Abhängigkeit eingeführt
- LQ-073 backtest application boundary: `docs/lq-073-backtest-application-boundary.md`
  - Status:
    - Ein-Methoden-Port und eine kleine Orchestrierungsfunktion zum vorhandenen Runner ergänzt
    - vorhandener `BacktestResult` und vorhandene neutrale Summary werden wiederverwendet
    - kein paralleles Evidence-Modell, keine Queue und keine Adapterhierarchie eingeführt
- LQ-074 in-memory research job: `docs/lq-074-in-memory-research-job.md`
  - Status:
    - bereits validierter Research-Job synchron im Speicher ausführbar
    - Erfolg liefert vorhandene Evidence; Fehler bleiben neutral und terminal
    - keine Queue, Persistenz, Worker-, Retry- oder Repository-Abstraktion eingeführt
- LQ-075 minimal HTTP/job contract: `docs/lq-075-http-job-contract.md`
  - Status:
    - Start-, Status- und Evidence-Ressourcen sowie neutrale Fehlersemantik definiert
    - bestehende Identitäten, Lifecycle und Evidence bleiben maßgeblich
    - Routenaktivierung wartet auf vollständigen Experiment-Snapshot und minimale Job-Ablage
    - keine Auth-, Datenbank-, Queue-, Worker- oder Produktendpunkt-Implementierung vorgezogen
- LQ-076 minimal in-memory job register: `docs/lq-076-in-memory-job-register.md`
  - Status:
    - konkrete Job- und Experiment-Identität getrennt
    - prozesslokales `add`/`get` ohne Repository-Abstraktion ergänzt
    - Duplikate und unbekannte Jobs scheitern explizit
    - nächster Schritt: unveränderlicher Experiment-Snapshot
- LQ-077 immutable experiment snapshot: `docs/lq-077-immutable-experiment-snapshot.md`
  - Status:
    - Dataset-Fingerprint, Strategieversion und wirksame Parameter gemeinsam eingefroren
    - kanonische skalare Parameterdarstellung ohne paralleles Konfigurationssystem
    - Research-Job verwendet den gebundenen Snapshot für seine Evidence
    - keine Datenkopie, Persistenz, Factory oder HTTP-Route eingeführt
- LQ-078 research read API: `docs/lq-078-research-read-api.md`
  - Status:
    - Jobstatus und erfolgreiche Evidence über zwei GET-Routen lesbar
    - vorhandenes In-Memory-Register und bestehende Evidence wiederverwendet
    - unfertige Jobs veröffentlichen keine Teil-Evidence
    - kein Start-Endpunkt, keine Authentifizierung oder Persistenz eingeführt
- LQ-079 research job start: `docs/lq-079-research-job-start.md`
  - Status:
    - bereits validierter Job wird vor synchroner Ausführung registriert
    - Erfolg und neutraler Fehler bleiben über die Lese-API beobachtbar
    - doppelte Job-ID verhindert den Runner-Aufruf
    - keine Factory, HTTP-POST-Route, Queue oder Persistenz eingeführt
- LQ-080 research runner resolver: `docs/lq-080-research-runner-resolver.md`
  - Status:
    - Ein-Methoden-Auflösung vom Experiment-Snapshot zum vorhandenen Runner-Port
    - erfolgreiche Auflösung verwendet ausschließlich den bestehenden Startpfad
    - Auflösungsfehler hinterlassen keinen halbfertigen Job
    - kein generisches Factory-, Plugin- oder Resolver-Register eingeführt
- LQ-081 local CSV resolver: `docs/lq-081-local-csv-resolver.md`
  - Status:
    - exakt eine lokale CSV-/MidBreakout-v0-/Absolute-Risk-Kombination unterstützt
    - Daten-Root und SHA-256-Fingerprint werden fail-closed geprüft
    - vorhandene Research-Komponenten ohne parallele Implementierung wiederverwendet
    - kein Plugin-System, Upload, HTTP-POST oder externe Datenquelle eingeführt
- LQ-082 research start API: `docs/lq-082-research-start-api.md`
  - Status:
    - POST-Route nur bei explizit injiziertem Resolver aktiviert
    - vollständiger Snapshot startet den bestehenden synchronen Research-Pfad
    - neutrale 422-/409-Fehler ohne interne Details
    - kein Upload, Auth, Queue, externer Datenzugriff oder Deployment eingeführt
- LQ-083 research data root gate: `docs/lq-083-research-data-root-gate.md`
  - Status:
    - lokaler Research-Start nur über expliziten Daten-Root aktiviert
    - sichere Standardeinstellung registriert keine POST-Route
    - fehlender Root stoppt den Prozess fail-fast
    - kein Upload, Download, Release oder Deployment ausgeführt
- LQ-084 research environment gate: `docs/lq-084-research-environment-gate.md`
  - Status:
    - lokaler Research-Start bis zur Authentifizierung auf local/ci begrenzt
    - preview und production scheitern mit Research-Data-Root fail-closed
    - keine provisorischen API-Keys oder Shared-Secret-Umgehung eingeführt
    - kein Release, VPS-Zugriff oder Deployment ausgeführt
- LQ-085 authentication and authorization boundary: `docs/lq-085-authentication-authorization-boundary.md`
  - Status:
    - User, Session, Workspace-Membership und zwei Research-Rechte definiert
    - Cookie-, CSRF-, 401-/403-/404- und Audit-Grenzen festgelegt
    - Shared-Environment-Gate bleibt bis zum Ende-zu-Ende-Nachweis aktiv
    - keine Provider-, Passwort-, Token- oder Datenbankimplementierung vorgezogen
- LQ-086 access domain types: `docs/lq-086-access-domain-types.md`
  - Status:
    - stabile `UserId` ohne paralleles Workspace-Modell ergänzt
    - Membership auf `active` und `inactive` begrenzt
    - Permission auf `research:read` und `research:write` begrenzt
    - keine Session-, Policy-, Middleware- oder Persistenzimplementierung vorgezogen
- LQ-087 research authorization decision: `docs/lq-087-research-authorization-decision.md`
  - Status:
    - eine reine, fail-closed Research-Entscheidung ergänzt
    - inaktive Mitgliedschaften und fehlende Rechte werden immer abgewiesen
    - `research:write` umfasst Lesen, `research:read` jedoch kein Schreiben
    - keine Session-, HTTP-, Datenbank- oder Policy-Engine-Integration vorgezogen
- LQ-088 workspace membership: `docs/lq-088-workspace-membership.md`
  - Status:
    - User und vorhandener Workspace in einem unveränderlichen Objekt gebunden
    - Membership-Status und Research-Rechte gemeinsam eingefroren
    - keine zweite Workspace-Identität oder Rollenabstraktion eingeführt
    - keine Repository-, Session-, HTTP- oder Persistenzintegration vorgezogen
- LQ-089 workspace membership lookup port: `docs/lq-089-workspace-membership-lookup-port.md`
  - Status:
    - genau ein Lookup über `UserId` und `WorkspaceId` definiert
    - Treffer liefert vorhandenes Membership-Objekt, fehlender Treffer neutral `None`
    - keine Listen-, Such- oder Mutationsoperation eingeführt
    - keine konkrete Ablage, Session-, HTTP- oder Middleware-Integration vorgezogen
- LQ-090 research authorization application: `docs/lq-090-research-authorization-application.md`
  - Status:
    - Membership-Lookup und reine Research-Entscheidung minimal verbunden
    - fehlende oder inkonsistente Memberships werden fail-closed abgewiesen
    - vorhandene Permission-Implikation ohne parallele Policy wiederverwendet
    - keine Session-, HTTP-, Speicher- oder Deploymentintegration vorgezogen
- LQ-091 session principal: `docs/lq-091-session-principal.md`
  - Status:
    - unveränderlicher Principal mit genau einer verifizierten `UserId` ergänzt
    - Workspace und Rechte bleiben serverseitig über Membership gebunden
    - keine Cookies, Tokens oder Session-Geheimnisse in die Anwendung getragen
    - keine Provider-, Middleware-, Speicher- oder Deploymentintegration vorgezogen
- LQ-092 principal-bound authorization: `docs/lq-092-principal-bound-authorization.md`
  - Status:
    - Research-Autorisierung akzeptiert nur noch den verifizierten Principal
    - Membership-Lookup verwendet ausschließlich dessen `UserId`
    - bestehende fail-closed Zuordnungs- und Permission-Prüfung bleibt erhalten
    - keine Principal-Prüfung, Session-, HTTP- oder Deploymentintegration vorgezogen
- LQ-093 neutral authorization error: `docs/lq-093-neutral-authorization-error.md`
  - Status:
    - genau ein öffentlicher Code `permission_denied` definiert
    - Fehler akzeptiert keine IDs, Ursachen oder internen Details
    - HTTP-Status und Ressourcen-Sichtbarkeit bleiben bewusst unberührt
    - keine Logging-, Session-, Provider- oder Deploymentintegration vorgezogen
- LQ-094 research authorization guard: `docs/lq-094-research-authorization-guard.md`
  - Status:
    - dünner Guard über der vorhandenen booleschen Entscheidung ergänzt
    - alle Ablehnungsgründe erzeugen denselben neutralen Fehler
    - Membership- und Permission-Regeln werden nicht dupliziert
    - keine HTTP-, Session-, Audit- oder Deploymentintegration vorgezogen
- LQ-095 research workspace binding: `docs/lq-095-research-workspace-binding.md`
  - Status:
    - jeder Experiment-Snapshot verpflichtend an einen Workspace gebunden
    - jeder Job übernimmt diese unveränderliche serverseitige Zuordnung
    - leere Workspace-Identität wird als ungültige Pflichtreferenz abgewiesen
    - noch keine HTTP-Guard-, Session- oder Deploymentintegration vorgezogen
- LQ-096 authorized research job read: `docs/lq-096-authorized-research-job-read.md`
  - Status:
    - Job wird vor der Autorisierung geladen
    - Guard verwendet ausschließlich die gespeicherte Workspace-ID des Jobs
    - unbekannte Jobs und Permission-Ablehnungen bleiben getrennte neutrale Fälle
    - keine HTTP-, Session-, Membership-Speicher- oder Deploymentintegration vorgezogen
- LQ-097 optional authorized status route: `docs/lq-097-optional-authorized-status-route.md`
  - Status:
    - Jobstatus-Route nutzt bei vollständiger Injection den autorisierten Lesepfad
    - Principal und Membership-Lookup müssen gemeinsam konfiguriert sein
    - unbekannte und nicht sichtbare Jobs liefern identisches neutrales 404
    - Local-/CI-Pfad bleibt ohne Freigabe von Shared Environments unverändert
- LQ-098 optional authorized evidence route: `docs/lq-098-optional-authorized-evidence-route.md`
  - Status:
    - Status und Evidence verwenden denselben sichtbaren-Job-Helfer
    - Evidence wird erst nach erfolgreicher Workspace-Autorisierung gelesen
    - unbekannte und nicht sichtbare Jobs bleiben auf beiden Routen ununterscheidbar
    - keine Start-, Session-, Membership-Speicher- oder Deploymentintegration vorgezogen
- LQ-099 authorized research job start: `docs/lq-099-authorized-research-job-start.md`
  - Status:
    - `research:write` wird gegen die gespeicherte Snapshot-Workspace-ID geprüft
    - Resolver, Registrierung und Ausführung erfolgen erst nach erfolgreicher Prüfung
    - Read-only- und fehlende Rechte hinterlassen keinen halbfertigen Job
    - noch keine POST-, Session-, CSRF- oder Deploymentintegration vorgezogen
- LQ-100 optional authorized research start route: `docs/lq-100-optional-authorized-start-route.md`
  - Status:
    - POST verwendet bei vollständiger Injection den autorisierten Schreibpfad
    - fehlendes `research:write` liefert neutral `403 permission_denied`
    - abgelehnte Starts lösen weder Resolver noch Registrierung aus
    - Local-/CI-Pfad bleibt unverändert; Shared Environments bleiben gesperrt
- LQ-101 CSRF validation guard: `docs/lq-101-csrf-validation-guard.md`
  - Status:
    - exakte, nicht leere CSRF-Nachweise werden konstant verglichen
    - fehlende, leere und abweichende Werte scheitern fail-closed
    - Fehler enthält ausschließlich `csrf_validation_failed`
    - noch keine Token-, Session-, HTTP- oder Deploymentintegration vorgezogen
- LQ-102 CSRF-authorized research job start: `docs/lq-102-csrf-authorized-research-job-start.md`
  - Status:
    - CSRF wird vor Membership, Resolver, Registrierung und Ausführung geprüft
    - gültiger Nachweis führt in den bestehenden autorisierten Schreibpfad
    - ungültiger Nachweis hinterlässt keinen Job und keine Folgeaufrufe
    - Session-, Token-, HTTP- und Deploymentintegration bleiben bewusst offen
- LQ-103 resolved browser session: `docs/lq-103-resolved-browser-session.md`
  - Status:
    - verifizierter Principal und erwarteter CSRF-Wert werden gemeinsam gebunden
    - CSRF-Wert ist nicht leer und wird nicht in der Darstellung ausgegeben
    - bestehender `SessionPrincipal` bleibt auf die `UserId` begrenzt
    - keine Session-Auflösung, Speicherung, HTTP- oder Deploymentintegration
- LQ-104 session-bound CSRF research start: `docs/lq-104-session-bound-csrf-research-start.md`
  - Status:
    - CSRF-Start akzeptiert den gebundenen `ResolvedBrowserSession`-Kontext
    - Principal und erwarteter CSRF-Wert sind keine losen Parameter mehr
    - gültiger Nachweis führt unverändert in die Schreibautorisierung
    - Session-Auflösung, HTTP und Deployment bleiben bewusst offen
- LQ-105 optional session-bound CSRF HTTP path: `docs/lq-105-optional-session-csrf-http.md`
  - Status:
    - optionale HTTP-Autorisierung nutzt den gebundenen Session-Kontext
    - POST verlangt in diesem Modus einen passenden `X-CSRF-Token`-Header
    - fehlende oder falsche Nachweise liefern neutral `csrf_validation_failed`
    - Local-/CI-Pfad bleibt unverändert; Shared Environments bleiben gesperrt
- LQ-106 browser session lookup port: `docs/lq-106-browser-session-lookup-port.md`
  - Status:
    - opake `SessionId` identifiziert genau einen serverseitigen Session-Eintrag
    - Lookup liefert aufgelösten Kontext oder neutral `None`
    - Speicher-, Provider- und Cookie-Details bleiben außerhalb des Ports
    - keine Adapter-, HTTP-, Shared-Environment- oder Deploymentintegration
- LQ-107 browser session guard: `docs/lq-107-browser-session-guard.md`
  - Status:
    - Guard löst opake Session-ID über den bestehenden Port auf
    - fehlende und unbekannte Sessions liefern `authentication_required`
    - Fehler enthält weder ID noch internen Ablehnungsgrund
    - keine Adapter-, Cookie-, HTTP- oder Deploymentintegration vorgezogen
- LQ-108 optional session cookie HTTP boundary: `docs/lq-108-optional-session-cookie-http.md`
  - Status:
    - optionale HTTP-Grenze löst `liquent_session` über den Session-Port auf
    - fehlende und unbekannte Sessions liefern `401 authentication_required`
    - alle Research-Routen verwenden denselben aufgelösten Kontext
    - Local-/CI-Pfad bleibt unverändert; Shared Environments bleiben gesperrt
- LQ-109 browser session validity contract: `docs/lq-109-browser-session-validity-contract.md`
  - Status:
    - nur vorhandene, nicht widerrufene und nicht abgelaufene Einträge sind gültig
    - Lookup bleibt read-only und verlängert keine Session
    - ungültige Zustände bleiben nach außen ununterscheidbar
    - konkrete Laufzeiten, Adapter, Persistenz und HTTP bleiben bewusst offen
- LQ-110 browser session record validity: `docs/lq-110-browser-session-record-validity.md`
  - Status:
    - unveränderlicher serverseitiger Record bindet Kontext und Ablauf
    - Ablaufzeitpunkt und Widerruf liefern neutral keinen Kontext
    - Gültigkeitsprüfung ist pure und verlangt eindeutige Zeitwerte
    - Adapter, Persistenz und Shared Environments bleiben bewusst offen
- LQ-111 in-memory browser sessions: `docs/lq-111-in-memory-browser-sessions.md`
  - Status:
    - read-only Lookup-Adapter erfüllt den vorhandenen Session-Port
    - vorgegebene Records werden kopiert und mit injizierter Uhr geprüft
    - unbekannte und ungültige Sessions liefern neutral keinen Kontext
    - Schreib-Lifecycle, Persistenz und Shared Environments bleiben offen
- LQ-112 session lifecycle command contract: `docs/lq-112-session-lifecycle-command-contract.md`
  - Status:
    - Lifecycle ist auf Erzeugen, Rotieren und Widerrufen begrenzt
    - Rotation muss neuen Eintrag und alten Widerruf atomar verbinden
    - Widerruf ist idempotent; unbekannte oder ungültige Quellen bleiben neutral
    - Ports, Store, HTTP und Shared Environments bleiben bewusst offen
- LQ-113 session lifecycle ports: `docs/lq-113-session-lifecycle-ports.md`
  - Status:
    - Port enthält ausschließlich Erzeugen, Rotieren und Widerrufen
    - Ausgabeobjekt schützt opake Session- und CSRF-Werte vor Darstellung
    - ungültige Rotation und Widerruf verraten keinen internen Bestand
    - Implementierung, Store, HTTP und Shared Environments bleiben offen
- LQ-114 create browser session: `docs/lq-114-create-browser-session.md`
  - Status:
    - Anwendungsfall bindet ausgegebenes Session-Material an den Principal
    - atomarer Store-Port verhindert stilles Überschreiben
    - Kollision liefert ausschließlich den neutralen Lifecycle-Konflikt
    - konkreter Store, Generatoren und HTTP bleiben bewusst offen
- LQ-115 browser session issuance: `docs/lq-115-browser-session-issuance.md`
  - Status:
    - Generator-Port trennt opake Session-ID und CSRF-Wert
    - positive Laufzeit bestimmt einen eindeutigen Ablaufzeitpunkt
    - ungültige Eingaben erreichen den atomaren Store nicht
    - konkrete Zufallsquelle, Store und HTTP bleiben bewusst offen
- LQ-116 secure session material generator: `docs/lq-116-secure-session-material-generator.md`
  - Status:
    - Standardgenerator verwendet unabhängige URL-sichere Zufallswerte
    - mindestens 32 Zufallsbytes schützen jeweils Session-ID und CSRF-Wert
    - schwächere oder ungültige Konfigurationen werden abgewiesen
    - Wiring, Store, HTTP und Shared Environments bleiben bewusst offen
- LQ-117 session cookie contract: `docs/lq-117-session-cookie-contract.md`
  - Status:
    - `liquent_session` transportiert ausschließlich die opake Session-ID
    - Cookie bleibt host-only, Secure, HttpOnly, SameSite=Lax und Path=/
    - Browser-Lebensdauer überschreitet den serverseitigen Ablauf nicht
    - Helfer, Routen, CSRF-Ausgabe und Shared Environments bleiben offen
- LQ-118 session cookie helpers: `docs/lq-118-session-cookie-helpers.md`
  - Status:
    - kleine HTTP-Helfer setzen und löschen ausschließlich `liquent_session`
    - Ausgabe bleibt host-only, Secure, HttpOnly, SameSite=Lax und Path=/
    - abgerundete Browser-Lebensdauer überschreitet den Serverablauf nicht
    - Routen, Store-Wiring, CSRF-Ausgabe und Shared Environments bleiben offen
- LQ-119 session issuance transport contract:
  `docs/lq-119-session-issuance-transport-contract.md`
  - Status:
    - Session-ID wird ausschließlich im sicheren HttpOnly-Cookie ausgegeben
    - gebundener CSRF-Nachweis wird ausschließlich als Response-Header geliefert
    - beide Werte bleiben aus Body, URL, Logs, Telemetrie und Web Storage fern
    - Routen, Provider-Wiring, Refresh und Shared Environments bleiben offen
- LQ-120 session issuance response helper:
  `docs/lq-120-session-issuance-response-helper.md`
  - Status:
    - ein Helfer gibt Cookie und gebundenen CSRF-Header gemeinsam aus
    - unsichere Headerwerte und abgelaufenes Material mutieren keine Response
    - Session-ID und CSRF-Nachweis bleiben aus dem Response-Body fern
    - Routen, Provider-Wiring, CORS und Shared Environments bleiben offen
- LQ-121 in-memory session creation store:
  `docs/lq-121-in-memory-session-creation-store.md`
  - Status:
    - lokaler Session-Adapter erfüllt Lookup- und Creation-Store-Port
    - neue Session-IDs werden ergänzt, bestehende niemals überschrieben
    - Gültigkeitsprüfung und injizierte Uhr bleiben unverändert
    - Rotation, Persistenz, HTTP-Wiring und Shared Environments bleiben offen
- LQ-122 atomic rotation store port:
  `docs/lq-122-atomic-rotation-store-port.md`
  - Status:
    - speicherneutraler Rotation-Store-Port beschreibt genau eine atomare Operation
    - Store erhält aktuelle ID und neues Material und übernimmt den bestehenden Principal
    - Erfolg widerruft die alte Session und legt den Ersatz gemeinsam an
    - unbekannte/ungültige Quelle und Ziel-ID-Kollision liefern neutral False
- LQ-123 rotate session use case:
  `docs/lq-123-rotate-session-use-case.md`
  - Status:
    - Anwendungsfall erzeugt unabhängiges Ersatzmaterial über den Rotation-Store
    - Uhr und positive Laufzeit werden explizit injiziert und vorab geprüft
    - kein Principal-Argument; der Store bindet den bestehenden Principal, Store-False bleibt neutral
    - In-Memory-Rotation, HTTP und Shared Environments bleiben bewusst offen
- LQ-124 in-memory rotation:
  `docs/lq-124-in-memory-rotation.md`
  - Status:
    - lokaler Adapter erfüllt zusätzlich den atomaren Rotation-Store-Port
    - Erfolg übernimmt den bestehenden Principal und tauscht einen Snapshot in einem Schritt
    - unbekannte/abgelaufene/widerrufene Quelle, Kollision und identische ID liefern neutral False
    - Uhr wird höchstens einmal gelesen; Persistenz und Shared Environments bleiben offen
- LQ-125 session revocation port and use case:
  `docs/lq-125-session-revocation.md`
  - Status:
    - speicherneutraler Revocation-Store-Port mit idempotentem revoke_session(id) -> None
    - unbekannte, bereits widerrufene oder abgelaufene Sessions sind neutrale No-ops
    - kein Rückgabewert verrät Existenz oder Gültigkeit; kein internes Material nach außen
    - Anwendungsfall delegiert genau einmal; Adapter, HTTP-Logout und Shared Environments bleiben offen
- LQ-126 in-memory revocation:
  `docs/lq-126-in-memory-revocation.md`
  - Status:
    - lokaler Adapter erfüllt zusätzlich den idempotenten Revocation-Store-Port
    - unbekannte und bereits widerrufene Sessions bleiben neutral ohne Uhr-Lesevorgang
    - aktive Session wird mit genau einem Uhrzeitwert per Snapshot in einem Schritt widerrufen
    - abgelaufene Session bleibt unverändert; HTTP-Logout und Shared Environments bleiben offen
- LQ-127 logout transport contract:
  `docs/lq-127-logout-transport-contract.md`
  - Status:
    - nur Vertrag: POST /v1/session/logout, keine Route, keine Ports, keine Tests
    - erfolgreicher und bereits zustandsloser Logout liefern neutral 204 mit gelöschtem Cookie
    - CSRF nur bei gültiger aktiver Session; Widerruf vor Cookie-Löschung; Store-Fehler täuscht keinen Erfolg vor
    - keine Session-/CSRF-Werte in Body/URL/Logs/Telemetrie; CORS/Provider/Deployment bleiben offen
- LQ-128 logout route:
  `docs/lq-128-logout-route.md`
  - Status:
    - dünne POST /v1/session/logout verbindet Lookup, CSRF-Pfad, Revocation und Clear-Cookie-Helfer
    - Route nur bei gepaarten optionalen create_app-Deps; genau eine gesetzt ist ein Konfigurationsfehler
    - fünf Vertragspfade: 204/204/403/204/500, leere Bodies, no-store, Cookie-Löschung bzw. Nicht-Löschung
    - nur CsrfValidationFailed und SessionRevocationUnavailable werden gefangen; bestehende Pfade unverändert
- LQ-129 provider-neutral identity boundary:
  `docs/lq-129-identity-boundary-contract.md`
  - Status:
    - externe Authentifizierung später über OIDC Authorization Code + PKCE, ohne eigene Passwörter
    - ausschließlich verifiziertes `(issuer, subject)` bindet eine externe Identität an `UserId`
    - Anmeldung erteilt keine Workspace-Rolle; Autorisierung und Onboarding bleiben intern
    - Anbieter, Routen, Persistenz, Wiring und Shared Environments bleiben bewusst offen
- LQ-130 persistence boundary:
  `docs/lq-130-persistence-boundary.md`
  - Status:
    - Persistenzgrenze für Identitätsbindungen, Login-Transaktionen und Browser-Sessions; keine Technologie/Schema
    - neue Bindung nur nach Admission; Issuer-Trust wird bei jeder Anmeldung gegen die aktive Konfiguration geprüft
    - atomare Session-Erzeugung/Rotation/Widerruf und Einmal-Konsum der Login-Transaktion; Tokens/Session-IDs/CSRF nie geloggt
    - Hash-only ist Zielrichtung (spätere Validierungsgrenze, nicht Teil von LQ-130); Restore ist fail-closed; Local/Test bleibt In-Memory
- LQ-131 external identity lookup:
  `docs/lq-131-external-identity-lookup.md`
  - Status:
    - unveränderliches ExternalIdentity-Wertobjekt (issuer, subject), beide nicht leer, exakt/opak
    - kein Lowercasing, keine Slash-Entfernung, keine E-Mail-Normalisierung; keine Claims/Tokens/Rollen im Modell
    - read-only ExternalIdentityLookup: get_user_id(identity) -> UserId | None
    - kein schreibender Binding-Port, keine Admission, kein Adapter/Schema/Persistenz-Wiring
- LQ-132 identity admission and binding contract:
  `docs/lq-132-identity-admission-binding-contract.md`
  - Status:
    - nur Vertrag: externe Auth allein erzeugt nie User, Bindung, Mitgliedschaft, Rolle oder Berechtigung
    - gebundene ExternalIdentity löst nur auf vorhandenen UserId; ungebundene bindet nur nach gültiger interner Admission
    - Admission-Prüfung, Einmal-Konsum und eindeutige Bindungsanlage sind atomar und idempotent; Umbiegen auf anderen UserId verboten
    - Kollision/konsumierte/abgelaufene Admission/anderweitig gebunden → neutraler Fehler; Account-Linking/Rebinding/Merge/Multi-Issuer bleiben offen
- LQ-133 external identity admission port:
  `docs/lq-133-external-identity-admission-port.md`
  - Status:
    - opakes IdentityAdmissionId-Wertobjekt (value nicht leer, exakt/opak, unveränderlich/hashbar) und Port-Grenze
    - ExternalIdentityAdmissionStore.consume_admission_and_bind(admission_id, identity) -> UserId | None; kein UserId-Parameter
    - Ziel-UserId nur aus der Admission; Prüfung/Ablauf/Einmal-Konsum/erstmalige Bindung atomar, exakte Wiederholung idempotent
    - unbekannt/abgelaufen/konsumiert/Kollision/anderweitig gebunden → identisch None; kein Adapter/Persistenz/User-/Workspace-Erzeugung
- LQ-134 identity admission record:
  `docs/lq-134-identity-admission-record.md`
  - Status:
    - unveränderliches IdentityAdmissionRecord (target_user_id, target_workspace_id, expires_at, consumed_at, bound_identity)
    - expires_at/consumed_at timezone-aware; consumed_at und bound_identity nur gemeinsam gesetzt; konsumierter Record bewahrt die exakte Identität
    - Zweck durch Modelltyp definiert (keine Purpose-Enum); keine Normalisierung, keine Validitäts-/Konsum-Logik, keine Mutation
    - Ziel-Workspace erzeugt keine Mitgliedschaft/Rolle/Berechtigung; keine Claims/Tokens/Rollen/Session-Felder; kein Store/Adapter/Route
- LQ-135 in-memory external identities:
  `docs/lq-135-in-memory-external-identities.md`
  - Status:
    - lokaler flüchtiger Adapter InMemoryExternalIdentities erfüllt ExternalIdentityLookup und ExternalIdentityAdmissionStore
    - Konstruktor kopiert beide Mappings; get_user_id rein lesend, exakt/opak, ohne Uhr
    - consume_admission_and_bind: Ziel-UserId nur aus Admission; strukturelle Neutralfälle/idempotente Wiederholung vor Uhr-Lesen; Uhr höchstens einmal
    - Erfolg tauscht beide Snapshots gemeinsam (consumed_at=now + exakte bound_identity); jeder Fehlerfall unverändert, neutral None; kein Linking/Persistenz
- LQ-136 oidc login transaction contract:
  `docs/lq-136-oidc-login-transaction-contract.md`
  - Status:
    - nur Vertrag: Authorization Code Flow + PKCE (nur S256), unabhängige state/nonce/code_verifier, code_verifier bleibt serverseitig
    - optionale IdentityAdmissionId beim Start an die Transaktion gebunden; optionales Rückkehrziel nur als validierter interner relativer Pfad
    - Callback prüft vollständig (state/aktuell vertrauenswürdiger Issuer/Signatur/Audience/nonce/PKCE/(issuer,subject)); atomarer Einmal-Konsum vor Code-Einlösung, fail-closed
    - Fehler neutral ohne Bestandsleak; keine IdP-Tokens als Session; Reihenfolge Verifizieren→Lookup→Admission→Autorisierung→Session; keine Modelle/Ports/Route
- LQ-137 secure oidc login material:
  `docs/lq-137-secure-oidc-login-material.md`
  - Status:
    - unveränderliches OidcLoginMaterial (state/nonce/code_verifier sensibel/repr-frei, code_challenge sichtbar); genau vier Felder
    - SecureOidcLoginMaterialGenerator: drei unabhängige URL-safe Ziehungen, 32–96 Bytes (RFC-7636-Verifier 43–128 Zeichen), bool/Nicht-int/<32/>96 abgewiesen
    - PKCE nur S256: code_challenge = base64url(sha256(ascii(code_verifier))) ohne Padding; keine plain-Option, keine konfigurierbare Hashfunktion
    - keine Tokens/Claims/Issuer/User/Admission/Session im Modell; kein Port/Store/Adapter/Route/Netzwerk/Logging
- LQ-138 pending oidc login transaction:
  `docs/lq-138-pending-oidc-login-transaction.md`
  - Status:
    - unveränderliche PendingOidcLoginTransaction (expected_issuer, expected_nonce, code_verifier, redirect_uri, created_at, expires_at, admission_id?, return_path?)
    - vier Pflichtstrings nicht leer, exakt gespeichert; expected_nonce/code_verifier/admission_id sensibel und repr-frei; kein state-, kein code_challenge-Feld
    - created_at/expires_at timezone-aware, Awareness vor Vergleich; expires_at strikt nach created_at; gesetzter return_path nicht leer
    - keine URL-/Redirect-Validierung, keine Issuer-Trust-Entscheidung, keine Mutation/Konsum; kein Store/Port/Route/Tokenverarbeitung
- LQ-139 oidc login transaction claim port:
  `docs/lq-139-oidc-login-transaction-claim-port.md`
  - Status:
    - opakes OidcLoginState-Wertobjekt (value nicht leer, exakt/opak, repr-frei, unveränderlich/hashbar); genau ein Feld
    - OidcLoginTransactionClaimStore.claim_transaction(state) -> PendingOidcLoginTransaction | None; Signatur nur self/state
    - Claim atomar und einmalig: vorhanden/pending/nicht abgelaufen, Erfolg konsumiert fail-closed und liefert den Record genau einmal
    - unbekannt/abgelaufen/bereits konsumiert identisch None; Store liest Uhr intern; keine Token-/Issuer-Trust-Prüfung; kein Adapter/Creation-Port/Tombstone/Route
    - vorhandene abgelaufene Transaktion wird beim Claim fail-closed entfernt oder geheimnisfrei tombstoned; keine Geheimnisse in einem abgelaufenen Pending-Zustand
- LQ-140 identity admission id repr hardening:
  `docs/lq-140-identity-admission-id-repr-hardening.md`
  - Status:
    - IdentityAdmissionId.value ist jetzt field(repr=False); sensibler Capability-Handle im Docstring benannt
    - unveränderlich/hashbar, exakt/opak, keine Normalisierung, Leerprüfung, Gleichheit und Hashverhalten unverändert
    - Wert bleibt über .value für autorisierte interne Verarbeitung verfügbar; Klassenname darf im repr erscheinen
    - keine Änderung an IdentityAdmissionRecord, Ports, Adaptern, Login-Modellen, Persistenz oder CI-Workflow
- LQ-141 in-memory oidc login transaction claims:
  `docs/lq-141-in-memory-oidc-login-transaction-claims.md`
  - Status:
    - lokaler flüchtiger Adapter InMemoryOidcLoginTransactions erfüllt OidcLoginTransactionClaimStore
    - Konstruktor kopiert das Mapping und speichert die injizierte Uhr; keine Add-/Create-Methode, kein Tombstone
    - unbekannter/bereits entfernter State liefert None ohne Uhr-Lesen; vorhandener State liest die Uhr genau einmal
    - Snapshot ohne den State wird vor jedem Ergebnis übernommen, daher Erfolg und Ablauf gleichermaßen fail-closed entfernt; keine Threads/Locks/Persistenz
- LQ-142 oidc login transaction creation port:
  `docs/lq-142-oidc-login-transaction-creation-port.md`
  - Status:
    - OidcLoginTransactionCreationStore.add_transaction(state, transaction) -> bool; Signatur nur self/state/transaction
    - Erfolg speichert exakt den unveränderlichen Record unter dem exakten/opaken State; keine Normalisierung, kein Überschreiben
    - bereits pending und bereits beansprucht/konsumiert/abgelaufen (Konsumnachweis/Tombstone) liefern identisch False; Replay-Schutz gegen Wiederbelegung eines State
    - kein now-Parameter, keine Issuer-Trust-/Token-/Admission-Entscheidung, keine Retry-/Materialerzeugung; kein Adapter/Generator-Port/Anwendungsfall/Route
- LQ-143 in-memory oidc login transaction creation:
  `docs/lq-143-in-memory-oidc-login-transaction-creation.md`
  - Status:
    - dieselbe InMemoryOidcLoginTransactions-Instanz erfüllt jetzt Creation- und Claim-Port; Konstruktorsignatur unverändert
    - interner _reserved_states-Satz: initiale Keys automatisch reserviert, erfolgreicher Add reserviert mit, Claim entfernt nur den Pending-Record
    - reservierter State wird nie erneut akzeptiert (Replay-Schutz); fehlgeschlagener Claim eines unbekannten State reserviert ihn nicht
    - Add liest keine Uhr und bereitet beide Snapshots vor dem Attributtausch vor; Reserved-Satz hält rohe sensible States, kein Hashing/Tombstone/Persistenz
- LQ-144 oidc login start use case:
  `docs/lq-144-oidc-login-start-use-case.md`
  - Status:
    - start_oidc_login(store, generator, *, expected_issuer, redirect_uri, now, lifetime, admission_id=None, return_path=None) -> StartedOidcLogin; transportfrei
    - Material genau einmal erzeugt, Record über den bestehenden Creation-Port genau einmal gespeichert; kein Retry, kein zweiter Generatoraufruf
    - StartedOidcLogin trägt exakt state/nonce/code_challenge; code_verifier bleibt serverseitig im Pending-Record, admission_id verlässt den Server nie
    - state und nonce sind repr-frei, code_challenge darf im repr erscheinen; Rückgabe unveränderlich
    - lifetime strikt positiv und now timezone-aware werden vor der Materialerzeugung geprüft; expires_at ist exakt now + lifetime, keine eigene Systemuhr
    - abgelehnter Store liefert den neutralen OidcLoginStartConflict ohne State/Nonce/Verifier/Issuer/Admission; Store-Ausnahmen bleiben unverändert
    - kein neuer Port, keine Authorization-URL, keine Route, kein Provider, keine Discovery-/JWKS-/Token-/Claim-/Issuer-Trust-Logik, keine Session
- LQ-145 oidc authorization request contract:
  `docs/lq-145-oidc-authorization-request-contract.md`
  - Status:
    - ADR/Vertrag, providerneutral; keine Implementierung, keine URL-Erzeugung, keine Route, keine Konfigurationstypen
    - vier strikt getrennte Quellen: vertrauenswürdige Serverkonfiguration und StartedOidcLogin speisen den Request; Browsertransport und Pending-Record sind ausgeschlossen
    - Issuer/Authorization Endpoint/Client-ID/Redirect-URI/Scopes ausschließlich serverseitig; der Browser wählt oder überschreibt keinen davon
    - Issuer-Trust ist Laufzeitzustand: die Transaktion hält den erwarteten Issuer, keinen eingefrorenen Trust; Callback prüft erneut gemäß LQ-136
    - Endpoint nur absolut HTTPS ohne Fragment/Userinfo; ein Endpoint mit Query oder Fragment wird abgewiesen, keine stille Parameterzusammenführung
    - verbindlich: response_type=code, response_mode=query, code_challenge_method=S256, client_id, redirect_uri, scope mit openid, state, nonce, code_challenge
    - kein Plain-PKCE, kein impliziter/hybrider Flow, keine doppelten sicherheitsrelevanten Parameter, standardkonforme Kodierung statt Konkatenation
    - Scopes nur aus Konfiguration, eindeutig und nicht leer; kein automatisches email/profile/offline_access; Scope-Gewährung erzeugt keine Liquent-Berechtigung
    - Zusatzparameter deny-by-default (login_hint, prompt, max_age, acr_values, hd, ...); jeder braucht Entscheidung, Allowlist, Kollisionsschutz und Datenschutzprüfung
    - code_verifier, admission_id, return_path, created_at und expires_at bleiben serverseitig; Request-URL nicht vollständig in Logs, Telemetrie oder Analytics
    - Redirect-URI exakt wie im Pending-Record, keine Ableitung aus Host/Forwarded/X-Forwarded-Host; return_path erreicht den IdP nie
    - Weiterleitung erst nach erfolgreicher Speicherung, leerer Response mit Cache-Control: no-store; Route-Pfad, Methode und Status ausdrücklich in einen späteren Route-Slice verschoben
    - neutraler Abbruch ohne Offenlegung von Issuer-, Client-, Admission-, State-, User- oder Workspace-Existenz; keine stillen Fallbacks
- LQ-146 trusted oidc client configuration:
  `docs/lq-146-trusted-oidc-client-configuration.md`
  - Status:
    - TrustedOidcClientConfiguration(issuer, authorization_endpoint, client_id, redirect_uri, scopes) — frozen, slots, hashbar, exakt fünf Pflichtfelder
    - Issuer und Authorization Endpoint: absolute HTTPS-URL mit Host, ohne Userinfo, ohne Query, ohne Fragment; Pfad und Port erlaubt
    - Redirect-URI: absolute HTTPS-URL mit Host, ohne Userinfo, ohne Fragment; fest konfigurierte Query erlaubt und exakt bewahrt
    - Scopes: Tupel, nicht leer, openid zwingend, jeder Eintrag nicht leer/eindeutig/ohne Whitespace, Reihenfolge exakt, keine Sortierung/Dedup/Ergänzung
    - alle Werte nach Prüfung verbatim: kein Trimmen, kein Lowercasing, kein Slash-Entfernen, keine Kanonisierung, keine Ableitung eines Feldes aus einem anderen
    - Validierung nur via urllib.parse.urlsplit; kein Netzwerk, keine DNS-Auflösung, keine Discovery, keine normalisierte Rückgabe; Fehler nennen nur Feldnamen
    - kein Trust-/Enabled-Flag: Besitz beweist keine aktive Freigabe, Auswahl bleibt einer späteren Trust-Grenze, Callback prüft Issuer-Trust erneut
    - kein Client-Secret, keine Tokens/Claims/Admission/Session/State/Nonce/Verifier/Discovery-Daten; kein Port, Adapter, Store oder URL-Builder
- LQ-147 oidc authorization request builder:
  `docs/lq-147-oidc-authorization-request-builder.md`
  - Status:
    - build_oidc_authorization_request(configuration, started) -> OidcAuthorizationRequest; deterministisch, seiteneffektfrei, transportfrei
    - exakt neun Parameter, je genau einmal, feste Reihenfolge: response_type, response_mode, client_id, redirect_uri, scope, state, nonce, code_challenge, code_challenge_method
    - Konstanten code/query/S256 ohne Alternativen; scope aus der Tupelreihenfolge mit einzelnen Leerzeichen, ohne Sortierung/Dedup/Ergänzung
    - Kodierung ausschließlich über urlencode auf einer geordneten Paarliste; reservierte Zeichen und Unicode rundlaufen, kein Fragment, keine Parameterinjektion
    - Ziel-URL ist der unveränderte Endpoint plus genau ein ?; keine Neukanonisierung, kein urlunsplit, keine Wiederholung der LQ-146-/LQ-144-Validierungen
    - OidcAuthorizationRequest ist frozen/slots/hashbar mit exakt einem Feld url und repr=False; Klassenname sichtbar, URL/State/Nonce/Client-ID/Redirect-URI/Challenge nicht
    - kein code_verifier, keine Admission-ID, kein return_path, keine Deny-by-default-Parameter; offline_access nur innerhalb des konfigurierten scope-Werts
    - keine Trust-Auswahl, kein Store, keine Materialerzeugung, kein Netzwerk, keine Route; Callback prüft Issuer-Trust weiterhin erneut
- LQ-148 active oidc client configuration lookup port:
  `docs/lq-148-active-oidc-client-configuration-lookup-port.md`
  - Status:
    - ActiveOidcClientConfigurationLookup.get_active_configuration() -> TrustedOidcClientConfiguration | None; Signatur exakt self
    - genau eine aktive Konfiguration an dieser Grenze; kein get_by_issuer/get_by_provider/list_configurations, kein Multi-Issuer- oder Tenant-Routing, kein Fallback
    - struktureller Schutz: ohne Auswahlparameter kann eine spätere HTTP-Grenze keinen browsergewählten Issuer/Provider/Client/Tenant/Host/Header/Cookie durchreichen
    - Erfolg liefert exakt das gespeicherte unveränderliche Objekt; keine Kopie, Normalisierung, Ergänzung, kein eingefrorener Trust, kein Secret
    - None heißt nur "derzeit keine aktive Konfiguration"; keine Unterscheidung nie-konfiguriert/deaktiviert/entzogen, keine Liste, kein Default-Fallback, keine Detailursache
    - echter Lese-/Infrastrukturfehler wird nicht zu None umgedeutet; der Port definiert keinen eigenen Fehlertyp und keine Fehlerbehandlung
    - read-only: aktiviert/deaktiviert/erzeugt/aktualisiert/löscht nichts, keine Secret-Rotation, keine Discovery/JWKS/Netzwerk, kein Caching als Vertrag
    - jeder Login-Start liest erneut; Callback prüft aktuellen Issuer-Trust weiterhin separat; kein Adapter, kein Store, keine Route, kein redundanter Anwendungsfall
- LQ-149 scope oidc claim port contract test:
  `docs/lq-149-scope-oidc-claim-port-contract-test.md`
  - Status:
    - reiner Test-Wartungsslice; keine Datei unter src/, keine Änderung an ports.py, fachliche LQ-139-Semantik unverändert
    - überbreiter test_ports_module_has_no_token_trust_http_or_persistence_logic entfernt: las via inspect.getsource(ports_mod) die ganze Datei und suchte Substrings
    - der globale Test koppelte LQ-139 an jeden späteren unabhängigen Portvertrag und blockierte LQ-148, dessen Docstring JWKS-Logik gerade ausschloss
    - Ersatz test_claim_port_declares_only_claim_transaction_without_a_body prüft ausschließlich inspect.getsource(OidcLoginTransactionClaimStore) per AST
    - belegt genau eine Methode claim_transaction mit reinem Ellipsis-Rumpf, also keine Adapter-/Ausführungslogik im Port; nachweislich nicht leerlaufend
    - keine Aussage über andere Klassen, Importe, Docstring-Wortwahl, Modulfläche oder künftige Adapter; vorhandene Signatur-/Annotations-/Stub-Tests unverändert
    - Testzahl netto null: ein Test entfernt, ein fokussierter ergänzt (Datei 35, Suite 1494)
- LQ-150 in-memory active oidc client configuration:
  `docs/lq-150-in-memory-active-oidc-client-configuration.md`
  - Status:
    - InMemoryActiveOidcClientConfiguration erfüllt ActiveOidcClientConfigurationLookup; frozen/slots, nach Konstruktion unveränderlich
    - Singular-Name, weil genau eine Konfiguration gehalten wird; frozen dataclass statt einfacher Klasse, weil der Adapter anders als die übrigen nicht mutiert
    - mit Konfiguration: get_active_configuration() liefert bei jedem Aufruf exakt dasselbe Objekt; keine Kopie/Normalisierung/Ergänzung/Rekonstruktion, kein Trust-Flag
    - ohne Argument oder mit None: neutrales None, keine Exception, kein Default, kein Fallback, keine Information über frühere Konfigurationen
    - keine set/replace/activate/deactivate/delete/clear/reload/refresh/discover-Methode und keine sonstige öffentliche Verwaltungs-API
    - Konfiguration ist repr-frei; der repr lautet in beiden Fällen identisch InMemoryActiveOidcClientConfiguration() und verrät nicht einmal, ob eine gesetzt ist
    - parameterlose Portsignatur bleibt; Konfiguration wird ausschließlich beim serverseitigen Aufbau festgelegt, keine browsergesteuerte Auswahl
    - Konstruktor nimmt exakt (self, configuration): keine Uhr, kein Generator, kein Netzwerk-Client, keine Discovery; keine erneute Validierung der LQ-146-Invarianten
    - lokaler Composition-Snapshot, kein lebender Trust: kein Aktivierungsstatus, keine dynamische Aktualisierung; Callback prüft Issuer-Trust weiterhin separat
- LQ-151 prepare oidc login authorization:
  `docs/lq-151-prepare-oidc-login-authorization.md`
  - Status:
    - prepare_oidc_login_authorization(configuration_lookup, transaction_store, generator, *, now, lifetime, admission_id=None, return_path=None) -> OidcAuthorizationRequest
    - verbindet LQ-148/150 (Konfiguration lesen), LQ-144 (Transaktion starten) und LQ-147 (Request bauen); transportfrei, keine Route, kein HTTP-Redirect
    - Signatur nimmt keinen Issuer/Endpoint/Client-ID/Redirect-URI/Scope/Provider/Tenant/Workspace/User/Request/Response; alle Werte kommen nur aus dem Lookup
    - Aufruffolge exakt lookup -> generator -> store -> builder, jede Abhängigkeit genau einmal; Request wird erst nach erfolgreicher Speicherung gebaut
    - Snapshot-Konsistenz: genau eine Konfigurationslesung speist Pending-Record (expected_issuer, redirect_uri) und Request (Endpoint, Client-ID, Redirect-URI, Scopes)
    - kein zweiter Lookup innerhalb eines Starts; zwei getrennte Aufrufe dürfen jeweils einen neueren Snapshot lesen
    - fehlende aktive Konfiguration -> neuer neutraler OidcLoginUnavailable (eigener Code, detailfrei); Generator, Store und Builder bleiben unberührt, kein Fallback, kein Retry
    - OidcLoginStartConflict, Lookup-, Store-, Generator- und Builderfehler propagieren unverändert und werden nie umgedeutet; kein partieller Request
    - Zeitvalidierung bleibt bei LQ-144 und wird nicht dupliziert: bei ungültiger Zeitgrenze kann der read-only Lookup schon erfolgt sein, Generator und Store nicht
    - Rückgabe ausschließlich OidcAuthorizationRequest mit unverändertem repr-Schutz; code_verifier, admission_id und return_path bleiben serverseitig
    - keine eigene Trust-Entscheidung, keine erneute Validierung, keine Discovery, keine Signaturschlüssel, keine Token-/Claim-Prüfung; Callback prüft Issuer-Trust separat
- LQ-152 oidc login start route contract:
  `docs/lq-152-oidc-login-start-route-contract.md`
  - Status:
    - ADR/Transportvertrag, keine Implementierung, keine Route, keine Cookie-Helfer, keine Änderung an LQ-151
    - Browserbindung als kritische Entscheidung: erzeugter state zusätzlich im kurzlebigen host-only Cookie; Callback vergleicht Query-state konstantzeitlich VOR dem Claim
    - fehlendes oder falsches Binding-Cookie bricht neutral ab, ohne Claim, ohne Token, ohne Session; dabei wird nichts gelöscht
    - erst nach erfolgreichem konstantzeitlichem Match wird geclaimt und das Cookie danach auf jedem weiteren Endpfad gelöscht
    - Mismatch löscht bewusst nicht: der eine Cookie-Slot gehört dann einer neueren Transaktion, sonst wäre ein alter Callback ein Login-Denial-of-Service
    - last-start-wins: neuer Start überschreibt das Cookie, älterer Pending-Record läuft fail-closed ab, älterer Callback mismatched und lässt das neuere Cookie unberührt
    - Route POST /v1/session/oidc/login (erzeugt Serverzustand, kein sicheres GET); GET /v1/session/oidc/callback reserviert, kein Issuer/Provider im Pfad
    - Eingabegrenze: keine Query, kein Body, keine Admission-ID, kein return_path; Handler ruft LQ-151 mit serverseitiger Uhr, fester Lebensdauer und None/None
    - unauthentifiziert, daher Origin-Pflicht gegen konfigurierte vertrauenswürdige Origin, Sec-Fetch-Site falls vorhanden same-origin, kein Referer-Ersatz, kein CORS, kein Fallback
    - Erfolg: prüfen, LQ-151 genau einmal, erst nach atomarer Speicherung Cookie setzen und 303 See Other mit URL nur im Location-Header; kein 302/307/308, leerer Body
    - Cookie __Host-liquent_oidc_state: Secure, HttpOnly, SameSite=Lax, Path=/, kein Domain, Max-Age <= Transaktionslebensdauer; bewusste Abweichung vom präfixlosen liquent_session
    - notwendige Vorbedingung: Folgeslice muss den State separat bereitstellen (PreparedOidcLoginAuthorization, repr-frei); kein Rückgewinnen durch URL-Parsen
    - Fehler: 405 mit Allow, 400 bei nicht leerer Eingabe, 403 cross-site, 503 einheitlich für OidcLoginUnavailable und OidcLoginStartConflict, 500 neutral; nie Cookie oder Redirect
    - kein Retry-After ohne belastbare Retryzeit; kein Rollback des atomaren Stores, verwaiste Pending-Transaktionen laufen fail-closed ab
    - Logging ohne URL/Location/State/Nonce/Cookie/Client-ID/Redirect-URI/Admission/Return-Path; keine Metriklabels mit Issuer, Client-ID, State oder Origin
    - no-store auf allen Pfaden, zusätzlich Pragma: no-cache und Referrer-Policy: no-referrer beim Erfolg; keine Speicherung in Web Storage
    - erfolgreicher Redirect heißt nur: kurzlebige Login-Transaktion sicher gestartet; keine Session, keine Mitgliedschaft, keine Berechtigung
- LQ-153 prepared oidc login authorization:
  `docs/lq-153-prepared-oidc-login-authorization.md`
  - Status:
    - Ergebnisgrenzen-Erweiterung von LQ-151 und notwendige Vorbedingung für die LQ-152-Route; Eingabesignatur unverändert, nur der Rückgabetyp ändert sich
    - PreparedOidcLoginAuthorization(request, state) — frozen, slots, exakt zwei Felder; state ist repr=False, die URL bleibt durch den LQ-147-Vertrag repr-frei
    - der Handler erhält den State direkt und darf ihn niemals aus der Authorization-URL parsen; das wäre eine zweite, schwächere Quelle für einen kritischen Wert
    - state wird verbatim aus started.state in OidcLoginState verpackt; gleich zum Store-Key (==, gleicher Hash, gleicher .value), keine Ableitung/Normalisierung/Kopie
    - derselbe opake State für Pending-Transaktionsschlüssel, state-Queryparameter und Ergebnisfeld, aus einem Generatoraufruf innerhalb eines Starts
    - .state.value bleibt exakt verfügbar; das Objekt trägt keine Nonce, Verifier, Challenge, Admission, Konfiguration, Transaktion, Tokens oder Identitätsdaten und autorisiert nichts
    - Aufrufreihenfolge, Fehlerarten und Aufrufzahlen unverändert: OidcLoginUnavailable, OidcLoginStartConflict, keine zweite Uhr/Lookup/Materialerzeugung
    - Nachweis kein URL-Parsing über fokussiertes Builder-Double mit abweichendem bzw. fehlendem state; keine Route, kein Cookie, kein Callback
- LQ-154 oidc login start route:
  `docs/lq-154-oidc-login-start-route.md`
  - Status:
    - Umsetzung des LQ-152-Vertrags als eine Route POST /v1/session/oidc/login; kein Callback, keine Token-Einlösung, keine Session, keine Persistenz
    - sechs neue create_app-Parameter (Lookup, Creation-Store, Generator, Uhr, Lebensdauer, vertrauenswürdige Origin); Default-App hat die Route nicht (404)
    - jede echte Teilmenge wird beim App-Aufbau mit ValueError abgelehnt
    - Origin strikt validiert: absolute https-Origin, Scheme exakt https, Host vorhanden, optional gültiger Port, kein Userinfo, kein Pfad auch nicht /, keine Query, kein Fragment, keine Leerzeichen oder Kommaliste
    - Scheme, Steuerzeichen und leere ?/#-Separatoren werden auf dem Rohwert geprüft, weil urlsplit das Scheme kleinschreibt, Tab/Newline/CR entfernt und leere Query/Fragment wie fehlende meldet
    - keine Normalisierung und keine Ableitung aus dem Request; ein konfigurierter Defaultport bleibt erforderlich, Fehlermeldungen geben den Wert nie wieder
    - Lebensdauer fail-fast: ganze Max-Age-Sekunden <= 0 werden beim App-Aufbau abgelehnt, damit kein Start mit sofort abgelaufenem Max-Age=0-Cookie erfolgreich aussieht
    - keine versteckte Systemuhr, keine Default-Origin, keine Ableitung aus Host/Forwarded/X-Forwarded-Host/Query/Body; Referer ist kein Ersatz, kein CORS
    - Reihenfolge: Methode, leere Query, leerer Body, Origin exakt gleich, Sec-Fetch-Site falls vorhanden same-origin; Eingabeablehnung schlägt Origin-Ablehnung
    - Uhr höchstens einmal und erst nach vollständiger Prüfung; eine auslösende Uhr ergibt einen leeren neutralen 500 ohne Use-Case-Aufruf und ohne Cookie
    - derselbe now für Transaktion und Cookie; prepare_oidc_login_authorization genau einmal mit admission_id=None und return_path=None
    - Erfolg: leerer 303 mit Location=prepared.request.url, no-store, Pragma no-cache, Referrer-Policy no-referrer, kein Content-Type, keine URL im Body
    - Cookie __Host-liquent_oidc_state ausschließlich aus prepared.state.value; Secure, HttpOnly, SameSite=Lax, Path=/, kein Domain, Max-Age <= Lebensdauer
    - eigenes Modul transport/http/oidc_state_cookie.py, weil der Callback denselben Slot löschen muss; session_cookie.py und liquent_session bleiben unverändert
    - expires wird nach UTC normalisiert, damit eine nicht-UTC Uhr nicht nach erfolgreicher Speicherung scheitert und einen verwaisten Pending-Record hinterlässt
    - der State wird nie aus der Authorization-URL geparst; nachgewiesen über vier Builder-Doubles mit abweichendem, leerem oder fehlendem URL-state, gegenprobiert
    - alle Ablehnungen ohne Uhrabfrage, ohne Use-Case-Aufruf, ohne Cookie, ohne Redirect, ohne reflektierte Origin und ohne Retry-After
    - OidcLoginUnavailable und OidcLoginStartConflict byte-identisch als 503; jeder sonstige interne Fehler als neutraler leerer 500 ohne Exceptiontext
    - die Route besitzt jede Methode selbst, weil FastAPIs 405 sonst einen JSON-Body hätte; keine globale Fehlerbehandlung für andere Routen
    - GET, HEAD, PUT, PATCH, DELETE, OPTIONS, TRACE und CONNECT antworten identisch mit leerem 405, Allow: POST und no-store, ohne jede Abhängigkeit aufzurufen
    - Responsefehler nach erfolgreicher Speicherung bleibt neutraler 500 ohne Rollback; verwaiste Pending-Transaktion läuft fail-closed ab
    - last-start-wins über den einen Cookie-Slot; 144 fokussierte Tests, keine globalen AST-, Import- oder Substring-Verbote
- LQ-155 oidc callback verification boundary:
  `docs/lq-155-oidc-callback-verification-boundary.md`
  - Status:
    - ADR/Sicherheitsvertrag, providerneutral; keine Route, kein Modell, kein Port, kein Adapter, keine Bibliothek, keine Discovery- oder JWKS-Implementierung
    - drei getrennte Callback-Ebenen: HTTP-/Browserbindung, atomarer Claim, externe OIDC-Verifikation; LQ-155 entscheidet ausschließlich Ebene 3 und ihre Schnittstelle zu Ebene 2
    - Eingabegrenze Ebene 3: nur Authorization Code plus expected_issuer, expected_nonce, code_verifier und redirect_uri aus der geclaimten Transaktion
    - admission_id, return_path und state überschreiten die Grenze bewusst nicht; der Admission-Handle ist ein Capability-Wert, den eine reine Beweisgrenze nicht tragen darf
    - Ablauf und Einmal-Konsum bleiben abschließend auf Ebene 2; keine zweite Ablaufprüfung an der Verifikationsgrenze
    - expected_issuer ist eine Erwartung, kein eingefrorener Trust; beim Callback wird die aktive Konfiguration genau einmal gelesen und ihr issuer byteweise exakt verglichen
    - deaktivierter, entfernter oder ersetzter Issuer endet neutral; kein Fallback, keine Trust-Entscheidung aus Tokenclaims, kein browserwählbarer Issuer/Endpunkt/Algorithmus
    - notwendige Vorbedingung: LQ-146 trägt heute keinen Token-Endpunkt, keine Schlüsselquelle, keine erlaubten Algorithmen und keine Clock-Skew; die Konfigurationsgrenze muss zuerst erweitert werden
    - diese vier Werte gehören in serverseitige Konfiguration, nie in die Transaktion, in Browserwerte oder in ungeprüfte Tokeninhalte; keine ungesicherte Laufzeit-Discovery als zweiter Trust-Pfad
    - Code-Einlösung genau einmal, PKCE S256, Redirect-URI und code_verifier aus dem Pending-Record, Client-Identität aus der aktuell aktiven Konfiguration, kein Retry
    - transienter Netzwerkfehler nach dem Claim verbraucht die Transaktion; kein Rollback, der Nutzer startet einen neuen Login
    - Konfigurationsrotation zwischen Start und Callback endet fail-closed: geänderte Redirect-URI lehnt der Provider ab, geänderte Client-ID lässt die aud-Prüfung scheitern
    - verpflichtende ID-Token-Prüfungen: Format, Signatur, erlaubter Algorithmus, Schlüssel aus aktueller Trust-Konfiguration, exakter iss, aud, azp bei mehreren Audiences, exp, nbf, iat, exakter nonce, nicht leeres opakes sub
    - Clock-Skew klein, explizit serverseitig konfiguriert, nie aus dem Token; kein veränderlicher Claim wird Identitätsschlüssel
    - keine Prüfung wird wegen eines erfolgreichen Token-Endpunkt-Response übersprungen; die von OIDC Core erlaubte Signaturauslassung im Code Flow wird bewusst nicht genutzt, UserInfo ersetzt nichts
    - Algorithmen als serverseitige Allow-List; alg darf auswählen, nie einführen; alg none verboten; jku, x5u und jwk werden nie befolgt; kid wählt nur innerhalb des vertrauenswürdigen Schlüsselsets
    - Ergebnis ausschließlich ExternalIdentity(issuer, subject), exakt und opak, ohne Tokens, Rohclaims, Admission, Session, Rollen oder Berechtigung; erzeugt weder User noch Binding noch Mitgliedschaft
    - Assurance: eine spätere Policy darf verifizierte acr/amr verlangen, ohne Policy entsteht daraus keine Rolle; Repräsentation und Policy bleiben ein eigener Slice
    - Providerfehler durchlaufen zuerst Bindung und Claim, danach keine Code-Einlösung; Transaktion bleibt verbraucht, Providertexte nie ungefiltert, gemischte code/error-Antworten neutral abgelehnt
    - zwei Fehlerklassen (neutrale Verifikationsablehnung, Infrastrukturfehler) bleiben intern getrennt; beide lassen die geclaimte Transaktion verbraucht, erlauben keinen Retry derselben Transaktion und kein Store-Rollback
    - neutral heißt detail- und bestandsfrei, nicht zwingend derselbe HTTP-Status für fachliche Ablehnung und technische Nichtverfügbarkeit
    - eine Verifikationsablehnung bleibt innerhalb ihrer Klasse einheitlich; ein Infrastrukturfehler darf später als generische temporäre Nichtverfügbarkeit ohne technische Details behandelt werden
    - gleiche oder unterschiedliche neutrale Statuscodes bzw. Benutzerpfade bleiben ausdrücklich dem späteren Callback-Transportvertrag überlassen; LQ-155 nimmt das nicht vorweg
    - keine Klasse legt jemals Code, Token, Nonce, Verifier, State, Claims, Providertexte oder Trust-Konfigurationsdetails offen
    - Geheimnisgrenze: Code, code_verifier und alle Tokens nie in URL, Cookies, Web Storage, Logs, Telemetrie, Traces, Metriklabels, Fehlertexten oder Anwendungsdaten; keine Tokenpersistenz, keine unnötigen Claims in inneren Modellen
    - Reihenfolge: Konfiguration erweitern, Verifikationsport, Callback-Transportvertrag, Callback-Route, danach Identitätsauflösung und Session

*Research-/Backtesting-Kontext. Keine Live-/Paper-Trading-Funktion, keine
Exchange-Anbindung, keine Profitabilitätsaussage, keine Handelsempfehlung.*
