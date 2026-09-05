# LQ-299 — Research Worker Process Configuration

## Ergebnis

LQ-299 implementiert eine geschlossene owner-kontrollierte JSON-
Processkonfiguration und eine getrennte stabile Worker-ID-Quelle.

Beide Quellen lesen ausschließlich explizite absolute Dateien. Es gibt keinen
Fallback auf Umgebung, Hostname, PID, Container-ID, Zufall oder Datenbank.

## Owner-only Dateien

Konfiguration und Worker-ID müssen reguläre Dateien des aktuellen Processusers
mit Linkcount eins und Modus `0400` oder `0600` sein.

Symlinks werden mit `O_NOFOLLOW` abgewiesen. Gruppierbare oder öffentlich
lesbare/schreibbare Dateien, Hardlinks, leere und übergroße Dateien sind
detailfreie Nichtverfügbarkeit.

Dateiinhalte, Pfade und Betriebssystemfehler erscheinen weder in Exception noch
`repr`.

## Exakte JSON-Topologie

Die Konfiguration akzeptiert genau folgende Schlüssel:

- `worker_id_path`;
- `research_data_root`;
- `artifact_root`;
- `lease_seconds`;
- `idle_wait_seconds`;
- `unavailable_initial_wait_seconds`;
- `unavailable_max_wait_seconds`;
- `jitter_max_seconds`;
- `job_concurrency`;
- `trading_connectivity`.

Fehlende, unbekannte oder doppelte Schlüssel werden abgewiesen. Freie
Commands, Module, Importpfade, URLs, Rollen, Permissions und Allow-Werte können
nicht konfiguriert werden.

## Pfadgrenzen

Worker-ID-, Research-Data- und Artifactpfad müssen absolut sein.

Der Configloader öffnet diese Ziele noch nicht und erzeugt keine Verzeichnisse.
Ihre fach- und sicherheitsspezifische Prüfung bleibt bei Worker-ID-Quelle,
geschlossenem Resolver und LQ-296-ArtifactStore.

## Lease und Loop-Policy

Lease-Dauer muss endlich zwischen 5 und 3600 Sekunden liegen.

Idle-, technischer Initial-/Maximalwait und Jitter werden durch die bestehende
LQ-298-Policy validiert. Null-, negative, NaN-, Infinity- und unter dem
Initialwert liegende Maximalwerte scheitern vor Prozessstart.

`job_concurrency` ist typstreng exakt `1`; `true` gilt nicht als eins.
`trading_connectivity` ist typstreng exakt `disabled`.

## Stabile Worker-ID

`OwnerOnlyResearchWorkerIdSource` liest eine vorhandene Datei bis zu einer
begrenzten Größe. Genau ein abschließender Newline darf entfernt werden.

Die ID beginnt alphanumerisch und enthält danach höchstens 127 weitere
alphanumerische Zeichen sowie Punkt, Unterstrich oder Bindestrich.

Whitespace, Slash, mehrere Zeilen, leere und überlange Werte werden abgewiesen.
Die Quelle erzeugt, mutiert oder rotiert keine ID.

Wiederholtes Lesen unveränderter Bytes liefert dieselbe `ResearchWorkerId`.

## Fehlergrenze

Datei-, JSON-, Encoding-, Struktur-, Typ-, Policy- und ID-Fehler werden als
detailfreie `research_worker_configuration_unavailable` vereinheitlicht.

Die Worker-ID ist technische Claimidentität. Sie gewährt keine Session,
Membership, Researchpermission oder Managementauthority.

## Nicht enthalten

LQ-299 implementiert keine Datenbank-URL- oder Secretquelle, ID-Provisionierung,
Rotation, Signalhandler, Readiness, Liveness, Logging, CLI, Entry-Point,
Compose- oder Production-Aktivierung.

Schema und Migration-Head bleiben `20260819_0027`; Bundle und Entry Points
bleiben unverändert.

Die vollständige lokale Suite besteht mit 3387 Tests, 98 erwarteten
PostgreSQL-Skips und 615 bestehenden Warnungen.

## Implementierungsfolge

LQ-300 kann nun einen owner-kontrollierten Research-Worker-Entry-Point mit
expliziter Configdatei, Datenbank-Readiness, sicherer lokaler Composition,
SIGTERM-Stop und dem LQ-298-Loop implementieren.

Compose-Aktivierung und Production-Readiness bleiben anschließend separat.
