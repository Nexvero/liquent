# LQ-060 — Observability and External Health Verification

## Status

- Strukturierte JSON-Logs und validierte Correlation IDs implementiert.
- Niedrig-kardinale HTTP-Metriken und Readiness-Gauge ergänzt.
- Interner Prometheus-Endpunkt entspricht dem bestehenden Scrape-Vertrag.
- Externes HTTPS-Liveness-Werkzeug für Smoke Checks implementiert.
- Keine externe Überwachung aktiviert und kein VPS verändert.

## 1. Signalmodell

| Signal | Zweck | Kardinalitätsregel |
|---|---|---|
| Request Counter | Rate und Fehlerquote | Methode, Route-Template, Status |
| Duration Histogram | serverseitige Latenz | Methode und Route-Template |
| Readiness Gauge | letzter Readiness-Zustand | keine Labels |
| Build Info | installierte App-Version | feste Releaseversion |
| JSON Event | konkrete Diagnose | Correlation ID, keine Bodies/Secrets |

Unbekannte Pfade werden als `unmatched` zusammengefasst. Querystrings,
Workspace-IDs, Nutzerwerte und freie URL-Pfade erscheinen nie als Metric Label.
Der einzelne Uvicorn-Prozess vermeidet zunächst Prometheus-Multiprocess-State.

## 2. Correlation und Logs

Ein eingehendes `X-Correlation-ID` wird nur akzeptiert, wenn es 1–64 Zeichen
aus einer begrenzten ASCII-Menge enthält. Ungültige oder fehlende Werte werden
durch eine zufällige serverseitige ID ersetzt. Dieselbe ID erscheint im
Response Header und im Request-Log.

Production Logs sind einzeilige JSON-Objekte mit UTC-Zeit, Severity, Service,
Event und optionalem Korrelations-/HTTP-Kontext. Request Body, Querystring,
Header, Datenbank-URL und Exceptiontext werden nicht automatisch protokolliert.
Exceptionereignisse enthalten nur den Typ; detaillierte lokale Debugdiagnose
bleibt eine kontrollierte Operatoraktion.

## 3. Prometheus-Grenze

`/internal/metrics` wird ausschließlich über `liquent_observability` gescraped.
Der Edge darf diesen Pfad nicht öffentlich routen. Compose veröffentlicht
weiterhin keinen Hostport; Prometheus und Grafana bleiben intern.

Pflichtmetriken:

- `liquent_http_requests_total`,
- `liquent_http_request_duration_seconds`,
- `liquent_readiness`,
- `liquent_build_info`.

Host-, Container-, PostgreSQL- und Backupmetriken benötigen eigene Exporter
oder Jobs und folgen erst mit ihrem konkreten Alarmvertrag.

## 4. Externer Smoke Check

`liquent-health-check https://<host>/health/live`:

- akzeptiert standardmäßig nur HTTPS ohne eingebettete Credentials,
- besitzt einen begrenzten Timeout,
- erwartet HTTP 200 und den exakten Liveness-Vertrag,
- schreibt genau ein maschinenlesbares JSON-Ergebnis,
- beendet sich bei jedem unklaren Zustand ungleich null.

Das Werkzeug wird später nach Deployment und regelmäßig von außerhalb des VPS
ausgeführt. Es prüft Liveness; internes Readiness und Datenbankdetails bleiben
nicht öffentlich.

## 5. Noch offene Betriebsnachweise

- Edge-Route für öffentliche Liveness und explizites Deny für `/internal`,
- Prometheus-Scrape gegen ein gebautes Containerimage,
- Grafana-Dashboard und Alert Rules,
- externer Check von einem unabhängigen Standort,
- Host-/Disk-/Backupmetriken und Benachrichtigungskanal.

Diese Punkte benötigen ein gebautes Artefakt beziehungsweise kontrollierte
Infrastruktur und werden nicht durch lokale Unit Tests behauptet.

## 6. Definition of Done

- Requestlogs sind strukturiert und korrelierbar.
- Correlation Header werden validiert und zurückgegeben.
- Metriklabels sind begrenzt und enthalten keine dynamischen Pfade.
- Readiness und Buildidentität sind messbar.
- Externer Check ist fail-closed und HTTPS-only.
- Gesamte Testsuite bleibt grün.
- Nächster Schritt ist LQ-061: Backup-/Restore-Nachweis und Runbook.
