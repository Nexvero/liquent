# LQ-059 — PostgreSQL Persistence and Migration Gate

## Status

- SQLAlchemy-2-Engine-Adapter und Psycopg-3-Production-Treiber ergänzt.
- Alembic-Migrationsumgebung mit eindeutiger Baseline angelegt.
- Migrationen beziehen die Datenbank-URL ausschließlich aus dem Secretvertrag.
- Control Plane und Worker starten im Compose erst nach erfolgreichem Gate.
- Readiness verlangt Erreichbarkeit und exakt aktuellen Alembic-Head.
- Keine fachliche Tabelle, Produkt-API oder Tradingfunktion ergänzt.

## 1. Entscheidung

Jeder Prozess verwendet genau eine langlebige SQLAlchemy Engine. Verbindungen
werden erst bei Nutzung geöffnet, vor Checkout geprüft und durch kleine Pools
auf dem Single-VPS begrenzt. Production akzeptiert ausschließlich den expliziten
Treiber `postgresql+psycopg://`.

Alembic ist alleiniger Schemaänderungspfad. Die programmatische Konfiguration
enthält keine URL; die Migrationshistorie wird als Package Data in das
unveränderliche Application-Artefakt aufgenommen. Der Entrypoint
`liquent-migrate` lädt `database_url` aus `/run/secrets` und führt `upgrade head`
aus. Ein Fehler beendet das Gate ungleich null; nachgelagerte Anwendungsprozesse
bleiben gestoppt.

## 2. Baseline ohne Scheinschema

Revision `20260726_0001` etabliert ausschließlich die Alembic-Versionskette.
Sie erzeugt absichtlich keine generische Key/Value-, User-, Job- oder
Experimenttabelle. Fachliche Tabellen werden erst gemeinsam mit ihrem
Application-Workflow und seinen Invarianten eingeführt.

Damit ist bereits überprüfbar:

- Datenbank erreichbar,
- Migration ausführbar,
- genau ein Head vorhanden,
- installierte Revision entspricht dem Release,
- veraltete oder unbekannte Revision verhindert Readiness.

## 3. Readiness-Vertrag

| Zustand | HTTP | Grund |
|---|---:|---|
| DB nicht erreichbar | 503 | `database_unavailable` |
| Revision fehlt/veraltet/unbekannt | 503 | `schema_revision_mismatch` |
| DB erreichbar und Head aktuell | 200 | `ready` |

Liveness bleibt von der Datenbank unabhängig. Diagnoseantworten enthalten weder
URL noch Benutzername, Host oder Fehlerdetails. Timeouts verhindern lange
Blockaden der Readiness-Prüfung.

## 4. Deploymentfolge

```text
PostgreSQL healthy
      ↓
migration-gate: upgrade head
      ↓ success only
Control Plane + Research Worker
      ↓
Readiness prüft DB + Revision
```

Migrationen laufen nie parallel in jedem Webprozess. Rollback einer Anwendung
bedeutet nicht automatisch Schema-Downgrade; jede destruktive Migration benötigt
vorher eine eigene Expand/Contract- und Recovery-Entscheidung.

## 5. Verifikation

Lokale Tests verwenden SQLite ausschließlich als isolierten Nachweis der
Alembic-Revisionsmechanik. Das ist kein freigegebener Production-Store und kein
PostgreSQL-Kompatibilitätsnachweis. Vor Deployment folgt ein eigener
PostgreSQL-Container-Integrationstest mit der freigegebenen Major-Version 18.

## 6. Definition of Done

- Production-Treiber und Engine-Grenze sind festgelegt.
- Migration Gate besitzt einen separaten, einmaligen Compose-Prozess.
- Repository und Alembic-Konfiguration enthalten keine Datenbank-Credentials.
- Leere, aktuelle und unerreichbare Datenbankzustände sind getestet.
- Readiness ist nur bei exakt passender Revision positiv.
- Gesamte bestehende Testsuite bleibt grün.
- Nächster Schritt ist LQ-060: Observability und externe Health-Prüfung.
