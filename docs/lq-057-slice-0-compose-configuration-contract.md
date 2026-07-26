# LQ-057 — Slice-0 Compose and Configuration Contract

## Status

- Single-VPS-Prozessrollen als deklarativer Compose-Vertrag angelegt.
- Nicht-geheime Runtimekonfiguration, Imageidentitäten und Secrets getrennt.
- Öffentliche Portveröffentlichung im Anwendungs-Compose ausgeschlossen.
- Ressourcenobergrenzen, Logrotation und interne Netzgrenzen dokumentiert.
- Noch keine Anwendung gebaut, kein Image gepullt und kein Dienst gestartet.

## 1. Betriebsvertrag

`operations/compose/compose.yaml` beschreibt fünf Rollen:

| Rolle | Zweck | öffentlich |
|---|---|---:|
| control-plane | synchrone Plattform-Workflows | nein; nur über vorhandenen Edge |
| research-worker | begrenzte Research Jobs | nein |
| postgres | System of Record und Jobkoordination | nein |
| prometheus | interne Metriksammlung | nein |
| grafana | interne Operatoransicht | nein |

Der vorhandene Edge-Proxy bleibt außerhalb dieses Vertrags der einzige
öffentliche Eintrittspunkt. Kein Service verwendet `ports:`. Das Public-Netz
ist ausschließlich der Control Plane zugänglich; Data und Observability bleiben
getrennte interne Netze.

## 2. Konfigurationsklassen

| Klasse | Beispiel | Quelle | Git |
|---|---|---|---:|
| Buildidentität | App-Image-Digest | freigegebenes CI-Artefakt | nur Platzhalter |
| Runtime, nicht geheim | Log Level, Port, Jobkonkurrenz | `runtime.env` auf Host | Example ja, Wertedatei nein |
| Secret | DB-URL, Passwörter | root-geschützte Hostdatei | niemals |
| Persistenter Zustand | DB, Artefakte, Metriken | benannte Volumes | nein |

Production-Images müssen per `@sha256:` identifiziert werden. Fehlende Images
oder Secretverzeichnisse brechen die Compose-Auflösung ab. Secretwerte werden
als Dateien unter `/run/secrets` eingebunden und nicht als Environmentwert in
Prozesslisten oder Diagnoseausgaben weitergegeben.

## 3. Verbindliche Runtimefelder

- `LIQUENT_ENVIRONMENT`: `local`, `ci`, `preview` oder `production`.
- `LIQUENT_LOG_LEVEL`: kontrollierter Severity-Wert.
- `LIQUENT_LOG_FORMAT`: Production ausschließlich `json`.
- `LIQUENT_HTTP_HOST` und `LIQUENT_HTTP_PORT`: interne Listeneradresse.
- `LIQUENT_ARTIFACT_ROOT`: gemounteter Artefaktpfad des Workers.
- `LIQUENT_JOB_CONCURRENCY`: in Slice 0/1 exakt `1`.
- `LIQUENT_TRADING_CONNECTIVITY`: zwingend `disabled`.
- `database_url`: Secretdatei, keine normale Environmentvariable.

LQ-058 implementiert diese Regeln fail-fast mit Pydantic Settings. Unbekannte
Felder, fehlende Pflichtfelder, Production-Plaintext-Secrets und aktivierte
Tradingkonnektivität müssen den Prozessstart verhindern.

## 4. Ressourcenbudget

Die Obergrenzen reservieren Hostkapazität für Edge, Betriebssystem, Backup und
Spitzen. Sie sind Ceilings, keine garantierte Reservierung:

- Control Plane: 1,5 CPU / 1,5 GiB,
- Research Worker: 3 CPU / 4 GiB,
- PostgreSQL: 1,5 CPU / 3 GiB,
- Prometheus: 0,35 CPU / 512 MiB,
- Grafana: 0,35 CPU / 512 MiB.

Da nicht alle Prozesse gleichzeitig ihr Limit ausschöpfen dürfen, werden reale
Nutzung und Memory Pressure ab LQ-060 gemessen. Bis dahin bleibt die
Worker-Konkurrenz eins. Dauerhafte Überlast führt zu Kapazitätsprüfung, nicht zu
unkontrolliertem Hochskalieren.

## 5. Sicherheits- und Fehlerverhalten

- `read_only`, `no-new-privileges` und Capability-Drops gelten soweit mit dem
  jeweiligen offiziellen Image vereinbar.
- Schreibpfade sind explizite Volumes oder begrenzte `tmpfs`-Mounts.
- Logs rotieren lokal und sind größenbegrenzt.
- PostgreSQL startet nicht ohne Passwortdatei.
- Control Plane und Worker warten auf einen gesunden PostgreSQL-Prozess.
- Fehlende Readiness der Control Plane darf nicht durch direkten Portzugriff
  umgangen werden.
- Kein Daten-, AI-, Broker-, Exchange- oder Tradingsecret ist vorgesehen.

## 6. Validierung und Aktivierung

Die statischen Tests prüfen Struktur und Sicherheitsinvarianten ohne Docker
oder Netzwerk. Vor einem ersten Start sind zusätzlich erforderlich:

1. LQ-058 liefert echte Control-Plane-/Worker-Entrypoints und Healthchecks.
2. LQ-059 liefert Migrationen und überprüfte PostgreSQL-Kompatibilität.
3. Freigegebene Image-Digests ersetzen alle Platzhalter.
4. Compose-Konfiguration wird mit Hostwerten gerendert und geprüft.
5. Start erfolgt zuerst lokal/isoliert, nicht direkt in Production.
6. VPS-Aktivierung benötigt einen eigenen Deployment- und Rollbackplan.

## 7. Definition of Done

- Rollen, Netze, Volumes und Ressourcen sind deklarativ festgelegt.
- Kein Anwendungsservice veröffentlicht einen Hostport.
- Secrets und nicht-geheime Runtimekonfiguration sind getrennt.
- Images sind auf unveränderliche Digests verpflichtet.
- Tradingkonnektivität bleibt explizit deaktiviert.
- Vertragsinvarianten sind automatisiert getestet.
- Nächster Schritt ist LQ-058: minimale Control Plane mit Health/Readiness.
