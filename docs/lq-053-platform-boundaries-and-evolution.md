# LQ-053 — Platform Boundaries and Evolution

## Status

- Product-/Systemabgleich zwischen Liquent Platform PRD und bestehendem Repository.
- Architekturentscheidung für die evolutionäre Weiterentwicklung dokumentiert.
- Keine Produktionslogik geändert.
- Keine Technologie-, Framework- oder Datenbankentscheidung getroffen.
- Keine Live-, Broker-, Exchange- oder Netzwerkfunktion aktiviert.

## 1. Zweck

Das bestehende Repository ist eine lokale, deterministische Research- und
Backtesting-Basis. Das PRD beschreibt dagegen eine professionelle Plattform vom
Marktverständnis über Strategieversionierung und Evidence bis zum kontrollierten
Betrieb. LQ-053 legt fest, wie beide Zustände verbunden werden, ohne den stabilen
Kern neu zu schreiben oder eine verfrühte verteilte Architektur einzuführen.

Leitentscheidung:

> Liquent wird evolutionär als modularer Monolith aufgebaut. Der vorhandene
> Research-Kern bleibt eine geschützte Capability innerhalb der Plattform. Neue
> Plattformfähigkeiten werden um ihn herum ergänzt und greifen nur über explizite
> Anwendungsgrenzen auf ihn zu.

## 2. Verbindliche Produktgrenze

Liquent verkauft ausschließlich Software. Der Nutzer definiert, prüft, genehmigt
und betreibt seine eigenen Strategien auf eigenen Konten. Die Plattform verwaltet
keine Kundengelder, bietet kein Copy Trading und erzeugt keine Kauf- oder
Verkaufsempfehlungen.

Für die Architektur folgen daraus unverrückbare Regeln:

- keine versteckte oder autonome Live-Aktivierung,
- keine Brokerberechtigung zur Auszahlung oder Verwahrung,
- keine Kauf- oder Verkaufsempfehlungen,
- keine Performance-Rankings als Produktempfehlung,
- keine Strategieänderung ohne neue unveränderliche Version,
- kein Übergang in einen riskanteren Zustand ohne explizites Gate,
- Fakten, historische Evidenz und Interpretation bleiben unterscheidbar,
- bei unklarem Zustand gilt der sicherere Betriebszustand.

## 3. Ist-Architektur des Repositorys

### 3.1 Wiederverwendbarer Kern

| Capability | Vorhandener Baustein | Entscheidung |
|---|---|---|
| Domain-Grundtypen | `src/liquent/domain/models.py` | Bewahren; nicht vorschnell zum Plattform-Gesamtmodell aufblasen |
| Historische Daten | `HistoricalFileSource` | Als lokaler Adapter und Testreferenz bewahren |
| Strategieauswertung | Strategy Protocol, MidBreakout v0/v1 | Als Beispiel-/Regressionsstrategien bewahren |
| Risikoentscheidung | `RiskEngine` | Als deterministischen Research-Risk-Kern bewahren |
| Backtesting | `BacktestRunner`, `CostModel`, Metrics | Als erste Evidence-Rechenfähigkeit bewahren |
| Reporting | Summary-/Comparison-Reporting | Als neutrale Ergebnisprojektion weiterverwenden |
| Paper-Simulation | `PaperTradingEngine` | Nicht als produktiven Paper-Betrieb einstufen; später neu einordnen |
| CLI | lokaler Backtest-Workflow | Als Entwickler-/Operatorwerkzeug bewahren |
| Visual Preview | optionales Streamlit-Tool | Eingefrorenes internes Werkzeug; keine Produkt-UI |

### 3.2 Nicht vorhandene Plattformfähigkeiten

Das Repository besitzt derzeit noch keine belastbare Implementierung für:

- Identität, Accounts, Organisationen, Rollen und Entitlements,
- persistente Workspaces, Hypothesen und Strategy Versions,
- Datenkatalog, Provenienz, Lizenzstatus und Freshness,
- asynchrone Experimente, Kontingente, Abbruch und Wiederaufnahme,
- versionierte Evidence Reports und Readiness Gates,
- produktiven Paper-Betrieb mit Zustandsmaschine und Reconciliation,
- Brokerverbindungen, Notifications, Incidents oder Audit Trail,
- Web-Anwendung und öffentliche Produkt-API,
- Billing, Marketplace oder Enterprise Governance,
- produktionsfähige Observability und Supportabläufe.

Diese Lücken werden nicht durch Umbenennen vorhandener Klassen geschlossen. Sie
benötigen eigene Domänenobjekte und Anwendungsworkflows.

## 4. Zielgrenzen des modularen Monolithen

```text
Experience
  Home · Observe · Build · Validate · Risk · Automate · Library
                              │
Application Workflows
  Workspace · Strategy Lifecycle · Experiment · Readiness · Operations
                              │
Domain Capabilities
  Market Context | Research Core | Evidence | Risk | Automation Operations
                              │
Trust & Control
  Identity · Permissions · Entitlements · Audit · Policy · Safety
                              │
Adapters
  Market Data · Broker/Sandbox · Notifications · Object Storage · AI Analysis
```

Die Darstellung beschreibt Verantwortungsgrenzen, keine Prozesse, Container,
Services, Frameworks oder Deploymenteinheiten.

### 4.1 Experience

Besitzt Navigation, Interaktionszustände und verständliche Projektionen. Die
Oberfläche berechnet keine Handelslogik und spricht Adapter nicht direkt an.

### 4.2 Application Workflows

Orchestriert Nutzerabsichten über Domänengrenzen hinweg. Beispiele sind
„Strategieversion testen“, „Evidence Review abschließen“ und später
„Paper Deployment pausieren“. Jeder kritische Workflow besitzt Vorbedingungen,
Ergebniszustand, Auditkontext und sichere Fehlerbehandlung.

### 4.3 Domain Capabilities

- **Market Context:** Instrumente, Sessions, Datenabdeckung und Datenqualität.
- **Strategy Lifecycle:** Hypothese, Draft, unveränderliche Version und Status.
- **Research Core:** deterministische Strategieauswertung und Backtesting.
- **Evidence:** Experimentidentität, Annahmen, Resultate und Robustheitsstatus.
- **Risk:** Limits, Entscheidungen und später Portfolio-/Betriebsrisiko.
- **Automation Operations:** Deploymentzustände, Reconciliation und Safe State;
  im ersten Plattform-Slice noch nicht implementiert.

### 4.4 Trust & Control

Identity, Berechtigungen, Entitlements, Audit und Policies sind horizontale
Plattformfähigkeiten. Sie dürfen nicht als UI-only Checks implementiert werden.

### 4.5 Adapters

Externe Systeme liegen hinter austauschbaren Grenzen. Der Domain- und
Research-Kern kennt keine konkreten Datenanbieter, Broker, Benachrichtigungswege
oder AI-Modelle.

## 5. Gemeinsame Plattformobjekte

Das PRD verlangt eine Single Source of Truth. Die erste Plattformarchitektur
benötigt daher folgende konzeptionelle Identitäten:

| Objekt | Bedeutung | Beziehung zum Bestand |
|---|---|---|
| Workspace | Nutzerkontext für Markt, Hypothese, Strategie und Evidenz | neu |
| Hypothesis | prüfbare Marktbeobachtung mit Invalidierung | neu |
| Strategy Draft | veränderbarer Entwurf | neu; nutzt später Strategy Protocol |
| Strategy Version | unveränderliche freigegebene Definition | neu; darf nicht mit einer Python-Klasse gleichgesetzt werden |
| Data Snapshot | reproduzierbarer Datenstand samt Provenienz | neu; `HistoricalFileSource` ist ein möglicher Adapter |
| Experiment | Auftrag mit Version, Datenstand und Annahmen | vorhandenes Modell ist Ausgangspunkt, nicht fertiger Plattformvertrag |
| Evidence Report | versionierte Evidenz und Warnungen | Reporting liefert erste Inhalte |
| Risk Profile | versionierter zulässiger Risikorahmen | `RiskLimits` ist ein Rechenkern-Baustein |
| Deployment | Bindung von Version, Umgebung, Konto und Risk Profile | später neu |
| Incident/Audit Event | nachvollziehbares kritisches Ereignis | neu |

## 6. Ausführungsgrenzen

Research und Operations teilen versionierte Definitionen, aber nicht dieselben
Laufzeitannahmen.

```text
Research Plane                         Operations Plane (später)
--------------                         -------------------------
fehlertolerante Jobs                   priorisierte Zustandsführung
historische Daten                      aktuelle Daten/Brokerzustand
reproduzierbare Experimente            Heartbeat/Reconciliation
abbrechbare Rechenlast                  Safe State/Kill Controls
keine Brokerrechte                     minimale explizite Brokerrechte
```

Auf dem ersten VPS dürfen beide Bereiche zunächst im selben Deploymentkontext
existieren, bleiben aber logisch und in ihren Ressourcen-/Netzwerkgrenzen
getrennt. Eine spätere Extraktion erfolgt nur aufgrund gemessener Last,
Verfügbarkeit oder Sicherheitsanforderungen.

## 7. Capability-Mapping PRD → Repository

| PRD-Capability | Abdeckung heute | Entscheidung |
|---|---|---|
| Observe / Charts / Liquidity | niedrig | späterer Produktslice; vorhandene Datentypen nur Ausgangspunkt |
| Build / Strategy Builder | niedrig | Plattformobjekte zuerst; keine UI direkt auf Python-Klassen koppeln |
| Validate / Backtesting | mittel | stärkster vorhandener Kern; als erste Plattformfähigkeit exponieren |
| Walk Forward / Monte Carlo | nicht vorhanden | nach reproduzierbarem Experimentmodell |
| Risk | mittel im Research-Kontext | bewahren; Betriebs-/Portfolio-Risk separat modellieren |
| Paper Automation | Prototyp, nicht produktionsreif | nicht aktivieren; Lifecycle und Reconciliation zuerst |
| Broker / Live | nicht vorhanden | ausdrücklich außerhalb des ersten Plattform-Releases |
| AI | nicht vorhanden | erst nach strukturierten Strategy-/Evidence-Objekten |
| Marketplace | nicht vorhanden | nicht vor Sandbox, Permissions und Asset-Governance |
| Enterprise | nicht vorhanden | nicht vor Organisations- und Auditfähigkeit |

## 8. MVP-Neuschnitt

Das vollständige PRD-MVP ist für einen ersten technischen Slice zu breit. Die
technische Umsetzung wird deshalb in vollständige vertikale Inkremente geteilt.

### Slice 0 — Platform Foundation

- Repository- und Betriebsstandard,
- Umgebungsmodell ohne Secrets im Repository,
- Health-/Readiness-Konzept,
- nachvollziehbarer Build- und Deploymentprozess,
- noch keine öffentliche Produktfunktion.

### Slice 1 — Local Research as a Product Workflow

- Workspace anlegen,
- lokales/synthetisches Dataset auswählen,
- bestehende Strategieparameter konfigurieren,
- Backtest als Experiment ausführen,
- Evidence Summary ansehen,
- keine Accounts, Broker oder Automation.

### Slice 2 — Persistent Evidence

- Strategy Draft und unveränderliche Strategy Version,
- Data Snapshot und Experimentstatus,
- gespeicherter Evidence Report,
- Abbruch, Fehlerzustand und Reproduzierbarkeit,
- Auditbasis für kritische Änderungen.

### Slice 3 — Controlled Paper Operations

- erst nach eigener Spezifikation,
- Deployment State Machine,
- Risk Profile und Readiness Gate,
- Heartbeat, Reconciliation, Pause und Safe State,
- keine Live-Brokerverbindung.

Live-Betrieb, Marketplace, breite Multi-Asset-Unterstützung und generative
AI-Flächen sind keine Bestandteile dieser ersten drei Slices.

## 9. Architekturregeln für die Umsetzung

1. Bestehende Research-Tests bleiben Verhaltensschutz.
2. Produktworkflows importieren den Research-Kern über eine explizite
   Anwendungsgrenze, nicht aus UI-Komponenten heraus.
3. Strategy Version, Experiment und Evidence erhalten stabile Identitäten.
4. Externe I/O-Aufgaben werden von deterministischer Rechenlogik getrennt.
5. Keine neue Netzwerkfähigkeit im Kernpaket.
6. Keine Service-Aufteilung ohne belegten Betriebsgrund.
7. Keine Technologieentscheidung ohne vorherige Qualitäts- und Betriebsziele.
8. Keine Live-Funktion durch bloßes Aktivieren des vorhandenen Paper-Prototyps.
9. Änderungen an sicherheitskritischen Zuständen sind explizit, auditierbar und
   reversibel.
10. Sprache und UI bleiben deskriptiv und neutral.

## 10. Übergangsplan

### Jetzt bewahren

- Domain-, Data-, Risk-, Backtesting- und Reporting-Regressionsbasis,
- CLI als lokales Referenzwerkzeug,
- Sicherheitsflags und neutrale Berichtssprache,
- eingefrorene Tracks aus LQ-052.

### Als Nächstes spezifizieren

- Qualitätsziele und Betriebsmodell für Slice 0,
- Repository-Zielstruktur,
- unveränderliche IDs und Lifecycle der Slice-1-Objekte,
- Anwendungsgrenze zum vorhandenen BacktestRunner,
- minimaler Nutzerfluss und Akzeptanzkriterien.

### Bewusst später

- Broker- und Live-Ausführung,
- produktiver Paper-Betrieb,
- Portfolio-/Cross-Strategy-Risk,
- Marketplace, Enterprise und offene API,
- AI-Analyse jenseits deterministischer regelbasierter Checks.

## 11. Entscheidungstore vor Technik

Vor einer konkreten Technologieauswahl werden getrennt entschieden:

- erwartete Nutzer- und Joblast des ersten Jahres,
- Datenvolumen, Aufbewahrung und Reproduzierbarkeit,
- Antwortzeit für interaktive und asynchrone Workflows,
- Verfügbarkeitsklasse von Research gegenüber späteren Operations,
- RTO/RPO, Backup und Wiederherstellung,
- Mandanten- und Sicherheitsgrenzen,
- Observability, Audit und Supportfähigkeit,
- Teamkompetenz und Betriebsbudget auf dem eigenen VPS.

Erst danach folgen Entscheidungen zu Programmiersprachen, Frameworks,
Datenhaltung, Queueing und Deploymentdetails.

## 12. Definition of Done LQ-053

- PRD und Repository sind capability-basiert abgeglichen.
- Wiederverwendbare Kernbausteine und echte Plattformlücken sind getrennt.
- Modulare Zielgrenzen und gemeinsame Plattformobjekte sind definiert.
- Das MVP ist in risikoarme vertikale Slices geschnitten.
- Live-/Broker-/AI-/Marketplace-Umfang ist ausdrücklich zurückgestellt.
- Keine Produktionslogik, Dependency oder Laufzeitkonfiguration wurde geändert.
