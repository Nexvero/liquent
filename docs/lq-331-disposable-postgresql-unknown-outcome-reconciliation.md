# LQ-331 — Disposable PostgreSQL Unknown Outcome Reconciliation

## Ergebnis

LQ-331 installiert `liquent-disposable-postgres-reconcile` als strikt
read-only Operator für einen unbekannten LQ-330-Bereitstellungsausgang.

Der Command bindet den ursprünglichen Staginglauf an eine neue aktuelle
Reconciliation-Autorisierung, rendert die Composition erneut und klassifiziert
den exakt sichtbaren Runbestand neutral als `absent`, `isolated` oder
`conflict`.

Er startet, stoppt, entfernt oder verändert keine Ressource.

## Separate Reconciliation-Autorisierung

Die ursprüngliche Staging-Autorisierung gewährt kein späteres Recoveryrecht.
Sie wird ausschließlich als historische unveränderliche Runbindung geladen;
ihr damaliges Zeitfenster darf inzwischen abgelaufen sein.

Eine zweite owner-only Reconciliation-Datei bindet exakt:

- Schema-Version und stabile Reconciliation-ID;
- ursprüngliche Run-ID;
- Phase `disposable_postgres`;
- Source-Commit und Application-Kandidatendigest;
- SHA-256 des ursprünglichen Composefiles;
- getrennte Reconciliation-Executor- und Autorisiereridentitäten;
- ein aktuelles UTC-Zeitfenster von höchstens einer Stunde.

Sie enthält keinen gewünschten Ausgang, Ressourcenname, Dockerargument,
Allow-Boolean, Cleanup-, Fortsetzungs- oder Deploymentrecht.

## Historische Bindung

Run-ID, Source-Commit, Image-Digest und Compose-SHA-256 müssen zwischen
historischer und neuer Autorisierung exakt übereinstimmen.

Der Projektname wird erneut ausschließlich als `liquent-<run-id>` akzeptiert.
Das Composefile muss weiterhin den historisch gebundenen SHA-256 besitzen.

Runtime- und Image-Environmentdateien laufen erneut durch die owner-only
Grenzen. Das Application-Image muss dem historischen Kandidatendigest
entsprechen; alle Imagewerte bleiben unveränderliche Digestreferenzen.

Jeder Bindungs-, Rechte-, Typ-, Zeit- oder Hashfehler endet vor Dockerzugriff
detailfrei unavailable.

## Erneuter Compose-Render

Der Command führt genau einmal das gebundene read-only
`docker compose ... config --format json` aus.

Der vollständige Render wird durch dieselbe geschlossene PostgreSQL-
Modellprüfung wie LQ-330 geführt. Dadurch bleiben Service, PostgreSQL-Image,
Environment, Secret, Healthcheck, Capabilities, Netze und Volume identisch
gebunden.

Container, beide Netze und Volume werden erneut ausschließlich intern aus dem
Projektmodell abgeleitet. Der Caller kann kein Recoveryziel benennen.

## Read-only Präsenzklassifikation

Für die vier erwarteten Ressourcen verwendet der Operator ausschließlich
exakte read-only Dockerlisten:

- Runcontainer;
- internes Application-Netz;
- internes Data-Netz;
- PostgreSQL-Datenvolume.

Alle Aufrufe verwenden feste argv-Listen, den absoluten Dockerpfad, ein neues
leeres temporäres CWD und nur `LANG=C`, `LC_ALL=C`.

Vier leere Resultate ergeben `absent`.

Eine nur teilweise vorhandene Menge ergibt `conflict`. Sie wird weder ergänzt
noch entfernt.

Unerwarteter Listenoutput, Nonzero, stderr, Timeout, Truncation oder Hard Kill
ist technisch unavailable und kein neutraler Conflict.

## Vollständige Isolationsinspektion

Nur wenn alle vier exakten Namen vorhanden sind, inspiziert der Operator
Container, beide Netze und Volume read-only.

`isolated` verlangt gemeinsam:

- laufenden gesunden Container aus dem gebundenen PostgreSQL-Digest;
- passende Compose-Projekt- und PostgreSQL-Service-Labels;
- keine Portbindung;
- ausschließlich beide erwarteten Netze;
- genau das erwartete Volume am PostgreSQL-Datenziel;
- interne Netze mit passender Projektzuordnung;
- passendes Volume mit derselben Projektzuordnung.

Ein vollständig lesbarer, aber fremd gebundener oder invariantverletzender
Bestand ergibt `conflict`.

Malformed, doppelte Schlüssel oder technisch unvollständige Inspectantworten
bleiben unavailable.

## Neutrale Ausgabe

Erfolg schreibt genau ein kanonisches JSON-Objekt mit Schema-Version,
Inspectionname `disposable_postgres_reconciliation` und einem Ausgang:

- `absent`;
- `isolated`;
- `conflict`.

Run-ID, Reconciliation-ID, Ressourcennamen, Digests, Labels, Pfade,
Identitäten, Zeiten und technische Details werden nicht ausgegeben.

Technische Nichtverfügbarkeit endet still mit Exitcode zwei und ohne
stdout/stderr.

## Keine Mutation oder Fortsetzung

Der Operator enthält kein `compose up`, `down`, Start, Stop, Remove, Prune,
Volume-/Network-Delete, SQL, Restore oder Migration.

`absent` autorisiert keinen automatischen zweiten LQ-330-Versuch.

`isolated` setzt die ursprüngliche unavailable Phase nicht nachträglich auf
passed und startet weder Migration-Gate noch Worker.

`conflict` gewährt kein Cleanuprecht. Alle sichtbaren Ressourcen bleiben
unverändert.

Kein Ausgang ist eine Staging-, Readiness-, Deployment- oder
Productionfreigabe.

## Tests

Tests decken vollständige Abwesenheit, partielle Ressourcen, exakte isolierte
Ressourcen und fremde Projektzuordnung ab.

Sie beweisen den Stop vor Docker bei abweichender Reconciliation-Bindung,
technische Nichtverfügbarkeit bei unklarer Listenbeobachtung sowie die stille
CLI-Grenze.

Kein Test startet Docker oder PostgreSQL.

## Bundle und Nichtziele

Entry Point und Operatormodul erhöhen die Gates auf 31 Entry Points und 35
Operatormodule. Migrationen bleiben 27 mit Head `20260819_0027`.

LQ-331 persistiert noch keine Reconciliation-Evidence und implementiert keine
Claim-, Retry-, Resume-, Cleanup- oder Finalisierungsgrenze.

Es gibt keine Schema-, SQL-, Migration-, Port-, Domainmodell-, Compose-,
Produkt- oder Production-Wiring-Änderung.

## Nächster Slice

LQ-332 sollte die private atomare Reconciliation-Evidence und den
detailarmen Operator-Handoff definieren und implementieren. Erst danach kann
ein separater Vertrag über Retain, erneuten autorisierten Run oder eng
begrenztes Cleanup entscheiden.
