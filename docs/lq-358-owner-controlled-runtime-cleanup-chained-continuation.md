# LQ-358 — Owner-controlled Runtime Cleanup Chained Continuation

## Ergebnis

LQ-358 installiert `liquent-disposable-postgres-cleanup-chain-continue` für
einen neuen Cleanup-Versuch nach nichtterminaler LQ-355-Finalisierung.

Der Operator bindet LQ-355 als jüngsten Autoritätsanker und führt nur das
autoritative verbleibende Network-Budget aus.

## Geschlossene Autorisierung

Die owner-only Datei bindet Chained-Continuation-,
Recontinuation-Finalization-, Recontinuation-, Continuation-, Cleanup- und
Run-Kette sowie sämtliche Evidence- und Autorisierungshashes.

Sie enthält SHA-256 der vollständigen LQ-355-Autorisierung und ihrer exakten
Finalization-Evidence.

Operation ist exakt
`continue_disposable_postgres_cleanup_from_finalized_recontinuation`, Scope
exakt `runtime_only` und das UTC-Fenster höchstens eine Stunde.

Executor und Autorisierer sind getrennte opaque Identitäten.

## Zwei getrennte Präfixwerte

`previous_resume_from` hält den historischen LQ-351-Startpräfix unverändert
fest.

`resume_from` ist der daraus und aus LQ-355-Evidence abgeleitete effektive
Startpräfix für den neuen Versuch.

Bei `recontinuation_attempt_finalized` bleiben beide Werte gleich.

Bei `later_prefix_finalized` ist `resume_from` zwingend
`application_network_removed`, auch wenn der frühere Wert
`container_removed` war.

Damit kann ein späterer Präfix nie auf ein älteres Restbudget zurückfallen.

## LQ-355-Evidence

Die Finalization-Evidence wird owner-only und kanonisch gegen die historische
LQ-355-Autorisierung validiert.

Nur `recontinuation_attempt_finalized` und `later_prefix_finalized` sind
zulässige Quellen.

Terminale, neutrale oder konfliktbehaftete Ausgänge bleiben unavailable für
diesen Mutationspfad.

Der Evidencehash muss bytegenau der neuen Autorisierung entsprechen.

## Claim-Gates

Der ursprüngliche LQ-339-Cleanup-Claim muss vollständig gebunden offen sein.

Alter LQ-345-Continuation-Claim und LQ-351-Recontinuation-Claim müssen exakt
abwesend sein.

Ein vorhandener historischer Claim wird vollständig geprüft, aber niemals
freigegeben oder ersetzt.

Neuer Claim und neue Evidence werden nur aus dem vollständigen SHA-256 der
Chained-Continuation-ID abgeleitet.

## Frische LQ-341-Bestätigung

Vor neuer Claimanlage führt LQ-358 LQ-341 mit historischer
Cleanup-Reconciliation-Autorisierung frisch aus.

Nur ein Ausgang exakt gleich dem effektiven `resume_from` erreicht die
Mutation.

Jeder andere lesbare Ausgang ergibt `rejected` ohne Claim oder Dockerwirkung.

Malformed oder technisch unklare Beobachtung bleibt detailfrei unavailable.

## Zwei minimale Restbudgets

Ab `container_removed` entfernt der Operator ausschließlich Application- und
Data-Netz.

Ab `application_network_removed` entfernt er ausschließlich das Data-Netz.

Nach jedem Remove bestätigt eine exakte Namensliste Abwesenheit, bevor der
nächste Schritt beginnt.

Containeroperationen und bereits abgeschlossene Network-Removes sind
unerreichbar.

## Erhaltenes Volume

Nach dem letzten Network-Remove inspiziert der Operator ausschließlich das
exakte PostgreSQL-Datenvolume.

Name und Projektbindung müssen unverändert dem ursprünglichen Run entsprechen.

Das Volume wird weder entfernt, geöffnet, gemountet, gelesen noch verändert.

## Evidence-first Claim

Der Claim bindet vollständige Autorität, beide Finalization-Evidenceketten,
historischen und effektiven Startpräfix, Restbudget, Ressourcen, Identitäten
und UTC-Startzeit.

Er wird owner-only exklusiv geschrieben und vor dem ersten Remove samt
Evidenceverzeichnis synchronisiert.

Ein vorhandener Claim stoppt vor Inspector und Docker und wird nicht aufgrund
von Alter freigegeben.

## Unknown Outcome

Ab dem ersten Remove beendet jede technische Mehrdeutigkeit den Ablauf
sofort.

Cleanup- und Chained-Continuation-Claim bleiben offen.

Es gibt keinen Blind-Retry, Ersatzbefehl, Folgeschritt oder heuristischen
Erfolg.

Eine spätere read-only Reconciliation ist erforderlich.

## Chained-Continuation-Evidence

Nach bestätigter Runtimeentfernung und Volume-Erhalt schreibt LQ-358 getrennte
owner-only Evidence atomar.

Sie bindet alle IDs und Hashes, beide Startpräfixe, Restbudget, Ressourcen,
UTC-Start und Abschluss sowie
`runtime_removed_pending_cleanup_finalization`.

Erst vollständige Rücklesung erlaubt die Freigabe ausschließlich des neuen
Claims.

Ein exakter Evidence-Retry führt weder LQ-341 noch Docker aus.

## Harte Verbote

Compose-Down, Stop, Start, Kill, Force, Disconnect, Prune, `--volumes`,
Wildcard-, Prefix-, Label- und Gruppencleanup sind ausgeschlossen.

LQ-358 verändert keine historische Evidence, gibt keinen Cleanup- oder
historischen Claim frei und führt kein SQL aus.

Docker-Events, Logs und Volumeinhalte werden nicht gelesen.

## Neutrale Ausgabe

Die CLI liefert nur Schema-Version, Operation
`disposable_postgres_runtime_cleanup_chained_continuation` und:

- `runtime_removed_pending_cleanup_finalization`;
- `rejected`;
- technisch unavailable ohne stdout oder stderr.

Private IDs, Hashes, Ressourcen, Pfade und Zeiten bleiben verborgen.

## Tests

Fake-basierte Tests prüfen das aus Nichtstart abgeleitete Zwei-Network-Budget
und das aus späterem Präfix abgeleitete einzelne Data-Network-Budget.

Sie beweisen das vollständige Fehlen jeder Containeroperation.

Ein Zustandsmismatch wird vor Claim und Docker neutral abgelehnt.

## Bundle und Nichtziele

Entry Point und Operatormodul erhöhen die Gates auf 44 Entry Points und 48
Operatormodule. Migrationen bleiben 27 mit Head `20260819_0027`.

LQ-358 implementiert keine Reconciliation des neuen Claims, keine
Cleanup-Finalisierung und keine Volume-Löschung.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Domainmodell-,
Compose- oder Production-Wiring-Änderung.

## Nächster Slice

LQ-359 sollte die strikt read-only Reconciliation eines offenen
Chained-Continuation-Claims nach unbekanntem Ausgang definieren.

Cleanup-Finalisierung und jede Volumenlöschung bleiben separate Slices.
