# LQ-406 — Controlled Terminal PostgreSQL Volume Deletion Finalization Handoff

## Ergebnis

LQ-406 installiert
`liquent-disposable-postgres-volume-delete-terminal-handoff` für den
kontrollierten Abschluss einer positiv finalisierten LQ-400-Continuation.

Der Handoff besitzt keinen eigenen Writer und delegiert den terminalen
Evidence-first Abschluss vollständig an LQ-398.

## Separate Handoff-Authority

Eine neue aktuelle owner-only Autorisierung bindet die stabile Handoff-ID an
positive LQ-404-Evidence, die vollständige historische Löschkette und neue
LQ-396-/LQ-398-Autorisierungen.

Operation ist exakt
`handoff_disposable_postgres_volume_deletion_finalization`, Scope exakt
`data_volume_only` und das UTC-Fenster höchstens eine Stunde.

Executor, Authorizer und Reviewer sind getrennt. IDs, Hashes, Ressourcen und
Downstream-Autorisierungen werden fail-closed geprüft.

## Positive LQ-404-Evidence

Der Handoff akzeptiert ausschließlich vollständig gebundene private
LQ-404-Evidence mit einem der Ausgänge:

- `continuation_evidence_confirmed`;
- `volume_removal_ready_for_deletion_finalization`.

Der Evidencehash ist bytegenau in der Handoff-Authority gebunden. Fehlende,
malformed oder fremde Evidence erreicht LQ-398 nicht.

## Claim-Gates

Der exakt abgeleitete LQ-400-Unterclaim muss nach LQ-404 freigegeben sein.

Ein noch vorhandener kanonischer Unterclaim ergibt
`investigation_required`; ein beschädigter Claim bleibt technisch
unavailable.

Vor dem ersten terminalen LQ-398-Lauf muss der ursprüngliche LQ-394-Claim
offen und vollständig gebunden sein. Seine unerklärte Abwesenheit ergibt
ebenfalls `investigation_required`.

Der Handoff entfernt selbst keinen Claim.

## Neue LQ-396- und LQ-398-Authority

Frühere Autorisierungen aus dem `continuation_required`-Pfad werden nicht
wiederverwendet.

Der Handoff verlangt neue aktuelle stabile Reconciliation- und
Finalization-IDs sowie bytegenau gebundene owner-only Autorisierungen.

Die neue LQ-398-Autorisierung bindet den SHA-256 der neuen
LQ-396-Autorisierung. Beide besitzen getrennte Identitäten und aktuelle
Zeitfenster.

## Frische terminale Komposition

Der Handoff ruft LQ-398 genau einmal mit den neuen Downstream-Authorities und
allen autoritativen Quellartefakten auf.

LQ-398 führt LQ-396 frisch read-only aus. Bei erwarteter Abwesenheit ist nur
die exakt verankerte Volume-Namensliste erreichbar.

Danach schreibt LQ-398 eigene atomare Finalization-Evidence und gibt erst nach
vollständiger Rücklesung den ursprünglichen LQ-394-Claim frei.

Der Handoff schreibt keine zusätzliche Abschluss-Evidence.

## Geschlossene Ausgänge

`volume_removal_finalized` und `deletion_evidence_confirmed` von LQ-398 werden
öffentlich zu `volume_deletion_finalized` vereinheitlicht.

`continuation_required`, `not_found` und `investigation_required` werden
`investigation_required` und lösen keinen weiteren Versuch aus.

Malformed oder technisch nicht verfügbare Downstream-Ausgänge bleiben
detailfrei unavailable.

## Retry

Bei unbekannter ursprünglicher Claimfreigabe bleibt LQ-398-Evidence erhalten.

Ein Wiederholungsaufruf mit denselben Autorisierungen erreicht dieselbe
LQ-398-Grenze. LQ-398 erkennt eigene Evidence zuerst und wiederholt nur die
exakte Claimfreigabe.

LQ-396 und Docker werden im Retry nicht erneut ausgeführt.

## Strikte Mutationsgrenze

Die einzigen erreichbaren Writes sind LQ-398-Finalization-Evidence und die
anschließende Freigabe des ursprünglichen Claims.

Volume-Remove, Force, Prune, Compose-Down, Mount, Export, SQL sowie Container-
und Networkmutation sind ausgeschlossen.

Continuation-Evidence, LQ-404-Evidence, Autorisierungen, Clearanceartefakte
und alle anderen Claims bleiben unverändert.

## Öffentliche Ausgabe

Die CLI gibt nur Schemaversion, Operation
`disposable_postgres_volume_deletion_terminal_handoff` und einen der Ausgänge
aus:

- `volume_deletion_finalized`;
- `investigation_required`;
- technisch unavailable ohne stdout oder stderr.

Private IDs, Hashes, Pfade, Ressourcen, Identitäten, Zeiten und Fehlerdetails
bleiben verborgen.

## Tests

Neun Fake-basierte Tests prüfen beide positiven LQ-404-Evidenceausgänge,
Unterclaimabwesenheit, den ursprünglichen Claim und frische LQ-398-
Finalisierung.

Weitere Fälle belegen LQ-398-Evidence-Retry ohne Docker, Hashbindung,
nichtterminale Downstream-Ausgänge, detailfreie CLI und Entry Point.

Kein Test verändert echte Dockerressourcen.

## Bundle und Nichtziele

Entry Point und Operatormodul erhöhen die Gates auf 58 Entry Points und 62
Operatormodule. Migrationen bleiben bei 27 mit Head `20260819_0027`.

LQ-406 erzeugt keine Handoff-Evidence, keine Authority, keinen neuen Claim,
keine Continuation und keinen allgemeinen Datenentsorgungsnachweis.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Domainmodell-,
Compose- oder Production-Wiring-Änderung.

## Nächster Slice

LQ-407 sollte den gesamten PostgreSQL-Volume-Disposition- und
-Deletion-Lebenszyklus von LQ-388 bis LQ-406 abschließend auditieren.

Der Audit muss positive und Unknown-Outcome-Pfade, Claim- und
Evidenceordnung, Mutationsbudgets, Retention, lokale Aussagegrenzen und den
terminalen claimfreien Abschluss zusammenhängend nachweisen.
