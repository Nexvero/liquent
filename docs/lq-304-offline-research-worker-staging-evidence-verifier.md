# LQ-304 — Offline Research Worker Staging Evidence Verifier

## Ergebnis

LQ-304 implementiert den installierbaren Offline-Command
`liquent-research-worker-staging-evidence`.

Der Verifier bewertet einen bereits erhobenen, redigierten LQ-303-Evidence-
Datensatz und gibt ausschließlich `approved`, `rejected` oder `unavailable`
aus.

Er führt den Staginglauf nicht aus und macht den aktuell fehlenden externen
Nachweis nicht nachträglich zu einem Approval.

## Eingabegrenze

Der Command verlangt genau `--evidence` mit einem absoluten Pfad.

Die Datei wird über die bestehende owner-only Grenze gelesen: regulär,
aktueller Owner, Linkcount eins, kein Symlink, Modus 0400 oder 0600 und maximal
65536 Bytes.

Es gibt keinen Environment-, stdin-, URL-, Default- oder Verzeichnisfallback.

JSON muss ein geschlossenes Objekt ohne doppelte oder unbekannte Schlüssel
sein. Syntax-, Encoding-, Datei- und Strukturfehler ergeben detailfrei
`unavailable`.

## Gebundener Lauf

Der Datensatz bindet Schema-Version eins, opake Run-ID, exakt `staging`,
40-stelligen Source-Commit, unveränderliche Image-Referenz mit SHA-256,
Compose-SHA-256 und den aktuellen Repository-Migration-Head.

`observed_at` und `review_by` sind UTC-Zeitpunkte. Evidence aus der Zukunft,
abgelaufene Reviewfristen oder nicht vorwärts gerichtete Fenster sind
`unavailable`.

Vorbereiter und Reviewer müssen verschiedene gültige opake Identitäten sein.
Diese Reviewidentitäten sind keine Produktrollen oder Authorities.

## Vollständige Checks

Der Verifier verlangt exakt alle 29 LQ-303-Gates:

- Image-Digest, Revision, Entry Point und Runtimeidentität;
- disposable PostgreSQL, Rollback und deaktiviertes Trading;
- Compose-Render, Command, Netze, Mounts, Secretziel und Grace Period;
- effektive Input-Ownership, read-only Daten und Artifactfähigkeiten;
- Migration-Gate, exakter Head, Idle-Start und mutationsfreies Idle;
- Logredaction, autorisierte Annahme, Claim/Heartbeat und terminales Outcome;
- Artifactintegrität, Revocation sowie Idle-/Running-SIGTERM ohne SIGKILL.

Fehlende oder zusätzliche Checks sind keine Teilfreigabe, sondern
`unavailable`.

## Checknachweise

Jeder ausgeführte Check trägt Status, opake Evidenzreferenz und lowercase
SHA-256 des geschützten Evidenzobjekts.

`passed` und `failed` verlangen Referenz und Digest. `unavailable` verlangt
beide Werte exakt `null`, damit fehlende Evidence nicht durch einen
scheinbaren Nachweis aufgewertet wird.

Die Referenz ist kein Pfad und keine URL. Der Verifier öffnet keine
Evidenzobjekte und vertraut keinem caller-gelieferten Gesamt-Allow.

## Redaction

Der gesamte JSON-Input wird vor fachlicher Auswertung auf verbotene private
Materialklassen geprüft.

DSN-Schemata, HTTP(S)-URLs, bekannte private absolute Pfadpräfixe,
Secretpfade, Authorization-/Password-/Credentialbegriffe und Private-Key-
Marker führen detailfrei zu `unavailable`.

Die CLI schreibt niemals Input, Pfad, Checkname, Digest, Actor oder
Fehlerursache nach stdout oder stderr.

## Entscheidung

Sind alle Checks vollständig, aktuell und `passed`, lautet die Entscheidung
`approved` mit Exitcode null.

Mindestens ein explizites `failed` ergibt `rejected` mit Exitcode eins.

Mindestens ein `unavailable`, jede beschädigte Bindung oder jeder technische
Fehler ergibt `unavailable` mit Exitcode zwei, sofern kein strukturell gültiger
expliziter Fail vorliegt.

Die Entscheidung ist eine Offline-Auswertung des gebundenen Stagingruns. Sie
startet keinen Worker und autorisiert weder Production noch Deployment.

## Nebenwirkungsgrenze

Der Verifier importiert keinen Dockerclient, öffnet kein Netzwerk, baut keine
Datenbank-Engine und liest keine Runtime-Secrets.

Er erstellt, ändert oder löscht keine Container, Volumes, Datenbanken,
Identitäten, Memberships, Jobs, Claims, Outcomes oder Artifacts.

Es gibt keine Schema-, SQL-, Migration-, Port- oder Domainmodelländerung.

## Packaging

Der neue Console Entry Point erhöht das geprüfte Bundle auf 22 Entry Points
und 21 Operatormodule. Der Migration-Head bleibt unverändert
`20260819_0027`.

## Aktueller Status und Folge

Da noch kein realer LQ-303-Staginglauf stattgefunden hat, existiert kein
zulässiger vollständiger Evidence-Datensatz. Der reale externe Status bleibt
`unavailable`.

LQ-305 sollte einen kontrollierten Staging-Executor für eine ausdrücklich
freigegebene isolierte Umgebung definieren. Dessen Ausgabe muss redigierte
Evidence für diesen Verifier erzeugen, ohne selbst Approval zu entscheiden.
