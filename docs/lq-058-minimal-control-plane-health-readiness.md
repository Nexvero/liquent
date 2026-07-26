# LQ-058 — Minimal Control Plane with Health and Readiness

## Status

- Minimale FastAPI-Control-Plane als Application Factory implementiert.
- Uvicorn-Entrypoint liest und validiert Konfiguration vor dem Serverstart.
- Liveness und Readiness sind getrennte, maschinenlesbare Endpunkte.
- Production-Konfiguration erzwingt sichere Werte und dateibasiertes DB-Secret.
- Keine Produkt-API, Datenbankverbindung oder Tradingfunktion implementiert.

## 1. Laufzeitgrenze

`liquent-control-plane` startet genau einen Uvicorn-Prozess mit der über
`create_app()` erzeugten FastAPI-Anwendung. Es gibt weder Auto-Reload noch
mehrere interne Worker. Prozessneustart und Ressourcenbegrenzung gehören zum
Compose-Betriebsvertrag.

Der Transport importiert Application Health, aber keine Strategie-, Risk-,
Backtesting- oder Paper-Module. Interaktive API-Dokumentation und OpenAPI sind
bis zur ersten versionierten Produkt-API deaktiviert.

## 2. Endpunkte

| Pfad | Erfolg | Fehler | Bedeutung |
|---|---:|---:|---|
| `/health/live` | 200 | Prozessfehler | Prozess lebt; keine Netzwerkabhängigkeit |
| `/health/ready` | 200 | 503 | Prozess darf Verkehr übernehmen |

Readiness meldet derzeit ausschließlich den lokalen Startup-Lifecycle. Die
verpflichtende PostgreSQL-Prüfung wird in LQ-059 hinter derselben
Application-Grenze ergänzt. Ein Research-Stau darf später nicht Liveness
negativ machen.

## 3. Fail-fast-Konfiguration

`PlatformSettings` verwendet den Prefix `LIQUENT_`, validiert Defaults und
weist unbekannte Modellfelder ab. Verbindliche Sicherheitsregeln:

- Production benötigt JSON-Logging,
- Production lauscht intern auf `0.0.0.0`,
- Production benötigt `database_url` aus dem Secrets-Verzeichnis,
- Jobkonkurrenz bleibt exakt eins,
- Tradingkonnektivität bleibt ausschließlich `disabled`,
- Ports außerhalb 1–65535 werden abgewiesen,
- öffentliche Diagnosedaten enthalten kein DB-Secret.

## 4. Nicht-Ziele

- keine Nutzer-, Workspace- oder Experimentendpunkte,
- keine Datenbankverbindung oder Migration,
- kein Jobleasing und kein aktiver Research Worker,
- keine Authentifizierung oder öffentliche Freigabe,
- keine Broker-, Exchange-, Daten- oder AI-Verbindung,
- kein Containerbuild und kein VPS-Deployment.

## 5. Definition of Done

- App Factory und Production-Entrypoint sind importierbar.
- Konfigurationsfehler verhindern den Start.
- Liveness bleibt unabhängig von Readiness.
- Nicht bereite Prozesse antworten mit HTTP 503 und stabilem Grund.
- Compose besitzt einen internen Readiness-Healthcheck.
- Gesamte Testsuite bleibt grün.
- Nächster Schritt ist LQ-059: PostgreSQL-Persistenz und Migration Gate.
