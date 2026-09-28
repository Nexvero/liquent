# LQ-409 — PostgreSQL Volume Disposition and Deletion Runbook Static Audit

## Ergebnis

LQ-409 implementiert das beaufsichtigte Betreiber-Runbook unter
`operations/runbooks/disposable-postgres-volume-disposition-deletion.md`.

Das Runbook ist eine manuelle Offline-Entscheidungsfolge und kein Skript,
Service, Scheduler, CI-Job, Deployment-Hook, HTTP-Pfad oder Authority.

## Vollständiges Commandinventar

Alle neun installierten Volume-Commands sind in ihrer Authority-Reihenfolge
dokumentiert:

1. Disposition;
2. Deletion-Preflight;
3. initiale Löschung;
4. ursprünglicher Claim-Inspector;
5. ursprünglicher Finalizer;
6. einzige Continuation;
7. Continuation-Claim-Inspector;
8. Continuation-Finalizer;
9. terminaler Handoff.

Die Liste ist ausdrücklich kein linear auszuführendes Skript. Jeder
kanonische Ausgang wählt genau eine Route oder einen Stop.

## Environment- und Rollengrenze

Das Runbook verlangt einen gebundenen Run mit immutable Image, Source,
Compose-Hash, Projekt, exaktem Volume und privater Evidencewurzel.

Environment Owner, Policy Owner, Authorizer, Executor, Reviewer,
Evidence-Retention Owner und Incident Owner bleiben getrennte
Verantwortlichkeiten.

Das dedizierte Prozesskonto gewährt keine Authority und erhält keine
allgemeinen Infrastrukturcredentials.

## Private Materialübergabe

Absolute owner-only Dateien, `umask 077`, sichere Pfadkarte und bytegenaue
SHA-256-Inventare sind verbindlich.

Jede neue Autorisierung wird aus unveränderten System-of-Record-Vorgängern
erstellt, separat geprüft und mit nicht wiederverwendbarer ID übergeben.

Der Executor erzeugt oder repariert keine Authority. Test-Fixture-Kopie,
Python-REPL, Shell-History und Environmentvariablen sind keine zulässigen
Übergaben.

## Geschlossene Betriebsrouten

Das Runbook dokumentiert den direkten positiven Pfad über LQ-394 sowie den
initialen Unknown-Outcome-Pfad über LQ-396 und LQ-398.

Nur `continuation_required` darf nach separater Entscheidung zu LQ-400
routen.

Ein LQ-400-Unknown-Outcome routet ausschließlich über LQ-402 und LQ-404.

Positive LQ-404-Evidence führt nach neuen Authorities zum terminalen
LQ-406-Handoff und dessen frischer LQ-398-Komposition.

Neutral, rejected, conflict, investigation_required und technische
Nichtverfügbarkeit bleiben getrennte Stopklassen.

## Mutationsbudgets

LQ-394 und LQ-400 dürfen jeweils höchstens einen exakten Volume-Remove
versuchen.

Ein dritter Remove, eine zweite Continuation, Blind-Retry und alternative
Dockerbefehle sind ausdrücklich verboten.

Unknown Outcome erhält Claims und Inputs unverändert und erlaubt nur den
zugeordneten read-only Inspector.

## Evidence- und Claimordnung

Jede Claimfreigabe folgt erst nach atomarer Evidenceanlage und vollständiger
Rücklesung.

Evidence-Retry verwendet unveränderte IDs, Authority und Artefakte, erreicht
weder Inspector noch Docker und wiederholt nur die exakte Claimfreigabe.

Der Unterclaim wird vor dem ursprünglichen Claim freigegeben. Der terminale
LQ-406-Abschluss delegiert Evidence und ursprüngliche Claimfreigabe an LQ-398.

## Incident und Retention

Exitcode 2, Conflict, Investigation, malformed Material, fremde Claims,
Hashabweichung, Hostverlust oder unerwartete Volumeanwesenheit stoppt alle
Commands.

Während der Untersuchung bleiben Docker-Mutation, Claimlöschung,
Evidence-Reparatur, ID-Ersetzung und automatische Wiederaufnahme verboten.

Die private Inventarisierung erhält Clearance-, Lineage-, Authority-, Claim-,
Evidence-, Retry- und Incidentartefakte über Claimfreigabe und lokalen
Abschluss hinaus.

Konkrete Fristen und Medien bleiben environment-owned.

## Terminale Bestätigung

Lokaler Abschluss ist nur zulässig, wenn LQ-406 kanonisch
`volume_deletion_finalized` ausgegeben hat, terminale Evidence erhalten ist,
beide Claims abwesend sind und kein Incident offen bleibt.

Claim- oder Volumeabwesenheit allein genügt nicht.

Der externe Status enthält nur opaque Runreferenz, UTC-Zeit und kanonischen
Ausgang.

## Aussagegrenze

Das Runbook bestätigt ausschließlich den Evidence-first Abschluss des exakten
lokalen Docker-Volumeobjekts.

Backups, Restoreartefakte, Exporte, Snapshots, Replikate, Logs und historische
Evidence besitzen eigene Retention- und Dispositionsgrenzen.

„Alle Daten entsorgt“ oder gleichwertige Aussagen bleiben verboten.

## Statischer Audit

Vier Tests prüfen:

- alle neun installierten Commands in Authority-Reihenfolge;
- Authority-, Unknown-Outcome- und Evidence-Retry-Routing;
- Incident-, Retention- und terminale Evidence-/Claim-Gates;
- Verbote von Automation, Abkürzungen und globaler Entsorgungsaussage.

Der Audit führt keinen Command und keine Dockerressource aus.

## Bundle und Nichtziele

LQ-409 fügt keinen Entry Point und kein Operatormodul hinzu. Der Bestand bleibt
bei 58 Entry Points, 62 Operatormodulen und 27 Migrationen mit Head
`20260819_0027`.

Der Slice implementiert keinen Authority-Generator, Operator, Writer,
Claimrelease, Volume-Remove, Monitoring, Deployment oder automatische
Ausführung.

## Nächster Slice

LQ-410 sollte die Betriebs- und Releasebereitschaft der vollständigen
PostgreSQL-Volume-Disposition- und -Deletion-Kette nach Runbookabschluss
erneut auditieren.

Der Reaudit muss prüfen, welche environmentbezogenen Freigaben weiterhin vor
einem realen Hostlauf fehlen und ob ein weiterer Funktionsslice überhaupt
erforderlich ist.
