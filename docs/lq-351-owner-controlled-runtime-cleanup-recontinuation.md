# LQ-351 — Owner-controlled Runtime Cleanup Recontinuation

## Ergebnis

LQ-351 installiert `liquent-disposable-postgres-cleanup-recontinue` für einen
neuen Cleanup-Versuch ab einem durch LQ-349 belegten späteren Präfix.

Der Operator führt ausschließlich das verbleibende Network-Budget aus. Das
Datenvolume und der ursprüngliche Cleanup-Claim bleiben erhalten.

## Geschlossene Autorisierung

Die owner-only Autorisierung bindet Recontinuation-, Finalization-,
Reconciliation-, alte Continuation-, Cleanup- und Run-IDs sowie die gesamte
historische Evidence- und Autorisierungskette.

Sie enthält SHA-256 der LQ-349-Autorisierung und der exakten
LQ-349-Finalization-Evidence.

Operation ist exakt
`continue_disposable_postgres_cleanup_from_finalized_prefix`, Scope exakt
`runtime_only` und `resume_from` entweder `container_removed` oder
`application_network_removed`.

Executor und Autorisierer sind getrennt; das aktuelle UTC-Fenster ist auf
höchstens eine Stunde begrenzt.

## LQ-349 als Autoritätsanker

Der Operator validiert die historische LQ-349-Autorisierung an ihrem
ursprünglichen Fenstermittelpunkt.

Die Finalization-Evidence muss owner-only, kanonisch, vollständig gebunden und
mit `later_prefix_finalized` abgeschlossen sein.

Ihr `observed_state` muss exakt dem neuen `resume_from` entsprechen.

Andere Finalisierungsausgänge, Hashabweichungen oder caller-gelieferte
Zustände bleiben unavailable.

## Claim-Gates

Der ursprüngliche LQ-339-Cleanup-Claim muss vollständig gebunden offen sein.

Der alte LQ-345-Continuation-Claim muss exakt fehlen. Ein vorhandener alter
Claim wird validiert, aber niemals freigegeben oder ersetzt.

Neuer Claim und neue Evidence werden ausschließlich aus dem vollständigen
SHA-256 der Recontinuation-ID abgeleitet.

Ein vorhandener neuer Claim blockiert Blind-Retry vor Inspector und Docker.

## Frische Zustandsbestätigung

Vor Claimanlage führt LQ-351 den LQ-341-Inspector mit seiner historischen
Autorisierung frisch aus.

Nur ein Ausgang exakt gleich `resume_from` erreicht die Mutation.

Jeder andere lesbare Zustand ergibt `rejected`, ohne Claim oder
Ressourceneffekt.

Malformed oder technisch nicht verfügbare Beobachtung bleibt detailfrei
unavailable.

## Zwei minimale Budgets

Ab `container_removed` entfernt der Operator ausschließlich Application- und
Data-Netz.

Ab `application_network_removed` entfernt er ausschließlich das Data-Netz.

Nach jedem Remove bestätigt eine exakte Namensliste die Abwesenheit, bevor
der nächste Schritt beginnt.

Container-Stop, Container-Remove und bereits abgeschlossene Network-Removes
sind unerreichbar.

## Erhaltenes Volume

Nach dem letzten Network-Remove wird ausschließlich das exakte
PostgreSQL-Datenvolume inspiziert.

Name und Projektbindung müssen unverändert dem ursprünglichen Run entsprechen.

Der Operator entfernt, mountet, öffnet, liest oder verändert das Volume nie.

## Evidence-first Recontinuation-Claim

Der neue Claim bindet alle historischen IDs und Hashes,
Finalization-Evidence, `resume_from`, Restbudget, Ressourcen, Identitäten und
UTC-Startzeit.

Er wird owner-only exklusiv geschrieben und vor dem ersten Remove samt
Evidenceverzeichnis synchronisiert.

Ein unbekannter Ausgang nach dem ersten Remove behält Cleanup- und
Recontinuation-Claim offen.

Es gibt keinen Ersatzbefehl, Folgeschritt oder heuristischen Erfolg.

## Recontinuation-Evidence

Nach bestätigter Runtimeentfernung und Volume-Erhalt schreibt LQ-351 getrennte
owner-only Evidence atomar.

Sie bindet vollständige Autorität, LQ-349-Evidence, Restbudget, Ressourcen,
UTC-Start und Abschluss sowie Ausgang
`runtime_removed_pending_cleanup_finalization`.

Erst vollständige Rücklesung erlaubt die Freigabe ausschließlich des neuen
Recontinuation-Claims.

Ein exakter Evidence-Retry führt weder LQ-341 noch Docker aus und wiederholt
nur eine möglicherweise unbekannte Claimfreigabe.

## Harte Verbote

Compose-Down, Stop, Start, Kill, Force, Disconnect, Prune, `--volumes`,
Wildcard-, Prefix-, Label- und Gruppencleanup sind ausgeschlossen.

LQ-351 verändert keine historische Evidence, gibt keinen Cleanup- oder alten
Continuation-Claim frei und führt kein SQL aus.

Docker-Events, Logs und Volumeinhalte werden nicht gelesen.

## Neutrale Ausgabe

Die CLI liefert nur Schema-Version, Operation
`disposable_postgres_runtime_cleanup_recontinuation` und:

- `runtime_removed_pending_cleanup_finalization`;
- `rejected`;
- technisch unavailable ohne stdout oder stderr.

Private IDs, Hashes, Ressourcen, Pfade und Zeiten verlassen die Grenze nicht.

## Tests

Fake-basierte Tests prüfen beide minimalen Restbudgets und beweisen das
vollständige Fehlen jeder Containeroperation.

Ein Zustandsmismatch wird vor Claim und Docker neutral abgelehnt.

Die bestehende Prozesssimulation bestätigt jeden Network-Remove einzeln und
das Datenvolume abschließend read-only.

## Bundle und Nichtziele

Entry Point und Operatormodul erhöhen die Gates auf 41 Entry Points und 45
Operatormodule. Migrationen bleiben 27 mit Head `20260819_0027`.

LQ-351 implementiert keine Reconciliation eines offenen Recontinuation-Claims,
keine Cleanup-Finalisierung und keine Volume-Löschung.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Domainmodell-,
Compose- oder Production-Wiring-Änderung.

## Nächster Slice

LQ-352 sollte die strikt read-only Reconciliation eines offenen
Recontinuation-Claims nach unbekanntem Ausgang definieren.

Cleanup-Finalisierung und jede Volumenlöschung bleiben separate Slices.
