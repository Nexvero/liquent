# LQ-083 — Research-Data-Root-Gate

## Status

- `LIQUENT_RESEARCH_DATA_ROOT` ist ein optionales, explizites Runtime-Opt-in.
- Ohne Wert bleibt `POST /v1/research/jobs` nicht registriert.
- Mit Wert wird der lokale CSV-Resolver beim App-Aufbau erzeugt.
- Ein nicht vorhandener Root stoppt den Prozess fail-fast.

## Betriebsgrenze

Die sichere Standardeinstellung ist deaktiviert. Der Operator muss einen
existierenden lokalen Verzeichnis-Root bewusst konfigurieren. Der konkrete Pfad
wird nicht in der öffentlichen Konfigurationszusammenfassung ausgegeben; sichtbar
ist nur `research_start_enabled=true|false`.

Das Setzen des Roots ist noch keine Deployment-Freigabe. Es verdrahtet lediglich
die bereits geprüften LQ-081-/LQ-082-Komponenten im Prozess.

## Bewusst nicht gebaut

- kein automatisches Verzeichnis und kein Daten-Download,
- kein Datei-Upload oder externes Volume-Provisioning,
- keine Authentifizierung, Mandantenfähigkeit oder Berechtigungsverwaltung,
- keine Queue, Datenbankmigration oder Hintergrundausführung,
- keine VPS-Änderung, kein Release oder Deployment.

## Definition of Done

- Default bleibt geschlossen,
- Opt-in aktiviert ausschließlich den vorhandenen lokalen Resolver,
- fehlender Root scheitert vor dem Serverstart,
- Pfad wird nicht als öffentliche Startmetadaten geloggt,
- Architektur- und vollständige Testsuite bleiben grün.
