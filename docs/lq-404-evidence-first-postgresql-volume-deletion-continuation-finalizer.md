# LQ-404 — Evidence-first PostgreSQL Volume Deletion Continuation Finalizer

## Ergebnis

LQ-404 installiert
`liquent-disposable-postgres-volume-delete-continue-finalize` für den
Evidence-first Abschluss geschlossener LQ-402-Zustände.

Der Finalizer schreibt eigene private Evidence vor Freigabe ausschließlich
des LQ-400-Unterclaims.

## Separate Finalization-Authority

Eine neue aktuelle owner-only Autorisierung bindet die stabile
Continuation-Finalization-ID an LQ-402, LQ-400 und die gesamte historische
Volume-Deletion-Kette.

Operation ist exakt
`finalize_disposable_postgres_volume_deletion_continuation`, Scope exakt
`data_volume_only` und das UTC-Fenster höchstens eine Stunde.

Executor, Authorizer und Reviewer sind getrennt. Alle IDs, Hashbeziehungen,
Ressourcen und historischen Autorisierungen werden fail-closed geprüft.

## Evidence vor Inspector

Der Finalization-Evidencepfad wird aus dem vollständigen SHA-256 der
Continuation-Finalization-ID abgeleitet.

Vorhandene vollständig gebundene Evidence wird vor LQ-402 und Docker erkannt
und steuert ausschließlich den idempotenten Unterclaim-Release-Retry.

Malformed oder fremde Evidence wird nicht überschrieben oder ignoriert.

## Frische LQ-402-Entscheidung

Ohne Finalization-Evidence führt der Operator den strikt read-only
LQ-402-Inspector unmittelbar neu aus.

Nur kanonische Ausgänge mit exakter Operation und Schemaversion werden
akzeptiert. Caller-gelieferte oder gespeicherte Zustände sind wirkungslos.

## Terminale Zustände

Zwei LQ-402-Ausgänge werden Evidence-first finalisiert:

- `continuation_evidence_present` wird
  `continuation_evidence_confirmed`;
- `volume_absent_evidence_missing` wird
  `volume_removal_ready_for_deletion_finalization`.

Vor neuer Evidence muss der ursprüngliche LQ-394-Claim weiterhin offen und
vollständig gebunden sein.

Der Finalizer erzeugt keine fehlende LQ-400-Evidence und erfindet keine
historische Removeantwort.

## Nichtterminale Zustände

`not_found` bleibt neutral und write-frei.

`volume_present`, `conflict` und ein lesbar fehlender ursprünglicher Claim
werden `investigation_required` ohne Evidence- oder Claimänderung.

Es gibt keinen weiteren Volume-Remove, Blind-Retry, neuen Claim oder neue
Continuation.

## Atomare Finalization-Evidence

Die private owner-only Evidence bindet alle fachlichen IDs und Hashes, den
frischen LQ-402-Zustand, den kanonischen Ausgang, getrennte Identitäten und
UTC-Abschlusszeit.

Sie wird exklusiv temporär geschrieben, geflusht, atomar final angelegt, mit
dem privaten Verzeichnis synchronisiert und vollständig zurückgelesen.

Erst erfolgreiche Rücklesung erlaubt die Unterclaimfreigabe.

## Exakte Unterclaimfreigabe

Nur der aus der gebundenen Continuation-Claim-ID abgeleitete LQ-400-Unterclaim
darf nach Evidence entfernt werden.

Ein vorhandener Claim wird vollständig gegen die historische LQ-400-Bindung
validiert. Fehlender Unterclaim gilt idempotent als bereits freigegeben.

Der ursprüngliche LQ-394-Claim bleibt in beiden positiven Ausgängen offen und
wird von LQ-404 niemals verändert.

## Evidence-Retry

Ist die Unterclaimfreigabe technisch mehrdeutig, bleibt die
Finalization-Evidence maßgeblich und der Aufruf endet unavailable.

Der exakte Retry liest dieselbe Evidence und versucht höchstens die Freigabe
desselben Unterclaims erneut.

LQ-402 und Docker werden im Retry nicht erreicht. Ein fremder oder
beschädigter Claim wird niemals entfernt.

## Strikte Ressourcengrenze

Der Operator führt keine Docker- oder SQL-Mutation aus.

Volume-Remove, Force, Prune, Compose-Down, Mount, Export sowie Container- und
Networkmutation sind unerreichbar.

Historische Evidence, Autorisierungen, Clearanceartefakte und der
ursprüngliche Claim bleiben unverändert.

## Öffentliche Ausgabe

Die CLI gibt nur Schemaversion, Operation
`disposable_postgres_volume_deletion_continuation_finalization` und einen der
Ausgänge aus:

- `continuation_evidence_confirmed`;
- `volume_removal_ready_for_deletion_finalization`;
- `not_found`;
- `investigation_required`;
- technisch unavailable ohne stdout oder stderr.

Private IDs, Hashes, Pfade, Ressourcen, Zeiten und Fehlerdetails bleiben
verborgen.

## Tests

Zehn Fake-basierte Tests prüfen beide terminalen Wege, Volumeanwesenheit,
Conflict, `not_found` und den fehlenden ursprünglichen Claim.

Weitere Fälle belegen atomare Evidence vor Unterclaimfreigabe,
Evidence-Retry ohne Inspector oder Docker, Hashbindung, CLI und Entry Point.

Kein Test verändert echte Dockerressourcen.

## Bundle und Nichtziele

Entry Point und Operatormodul erhöhen die Gates auf 57 Entry Points und 61
Operatormodule. Migrationen bleiben bei 27 mit Head `20260819_0027`.

LQ-404 implementiert keinen automatischen LQ-398-Abschluss, weiteren
Volume-Mutationsversuch oder allgemeinen Datenentsorgungsnachweis.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Domainmodell-,
Compose- oder Production-Wiring-Änderung.

## Nächster Slice

LQ-405 sollte den kontrollierten terminalen Handoff von positiver
LQ-404-Finalization-Evidence an eine frische LQ-398-Ausführung definieren.

Der Vertrag muss die erneute read-only Volumeabwesenheit verlangen, den
ursprünglichen LQ-394-Claim erst nach eigener LQ-398-Evidence freigeben und
jede automatische Ressourcenschreibwirkung ausschließen.
