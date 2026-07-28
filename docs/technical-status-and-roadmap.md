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

---

*Research-/Backtesting-Kontext. Keine Live-/Paper-Trading-Funktion, keine
Exchange-Anbindung, keine Profitabilitätsaussage, keine Handelsempfehlung.*
