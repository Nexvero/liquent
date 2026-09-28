# LQ-353 — Read-only Runtime Cleanup Recontinuation Claim Inspector

## Ergebnis

LQ-353 installiert
`liquent-disposable-postgres-cleanup-recontinue-reconcile` als strikt
read-only Inspector für offene LQ-351-Recontinuation-Claims.

Er klassifiziert ausschließlich den aktuellen Cleanup-Präfix und verändert
weder Claim, Evidence noch Dockerressource.

## Neue Autorisierung

Die owner-only Reconciliation-Autorisierung bindet geschlossen:

- Recontinuation-Reconciliation- und Recontinuation-ID;
- LQ-349-Finalization-, alte Continuation-, Cleanup- und Run-Kette;
- Source, Image, Compose sowie sämtliche Evidence- und Autorisierungshashes;
- SHA-256 der vollständigen LQ-351-Autorisierung;
- SHA-256 der exakten LQ-349-Finalization-Evidence;
- Scope `runtime_only` und historisches `resume_from`;
- Operation `inspect_disposable_postgres_cleanup_recontinuation`;
- getrennte Executor- und Autorisiereridentitäten;
- ein aktuelles UTC-Fenster von höchstens einer Stunde.

Unbekannte Felder, doppelte Schlüssel, stale Zeit und Hashabweichungen bleiben
detailfrei unavailable.

## Historische Bindung

LQ-351 und LQ-349 werden an ihren ursprünglichen Fenstermittelpunkten erneut
validiert.

Die neue Autorisierung verlängert weder Mutations- noch frühere
Reconciliation-Autorität.

Alle IDs, Hashes, `resume_from`, Run und Projektname müssen exakt dieselbe
Kette beschreiben.

Die LQ-349-Evidence muss weiterhin `later_prefix_finalized` und denselben
beobachteten Startpräfix enthalten.

## Claim-Gates

Der ursprüngliche LQ-339-Cleanup-Claim wird kanonisch geprüft und muss offen
bleiben.

Seine Abwesenheit ergibt `conflict`; malformed Bindung bleibt unavailable.

Der alte LQ-345-Continuation-Claim muss exakt fehlen. Ein noch vorhandener
alter Claim wird validiert, aber als technisch unvollständige historische
Finalisierung abgelehnt.

Der neue Recontinuation-Claim wird ausschließlich aus dem SHA-256 der
Recontinuation-ID abgeleitet.

## Evidence-first

Exakt gebundene LQ-351-Evidence wird vor LQ-341 geprüft.

Ist sie vorhanden, lautet der Ausgang `recontinuation_evidence_present`.

Ein gleichzeitig vorhandener neuer Claim wird nicht freigegeben.

Fehlen Recontinuation-Evidence und Claim gemeinsam, lautet der Ausgang
`not_found` ohne Dockerzugriff.

Evidence ohne Claim bleibt ebenfalls `recontinuation_evidence_present`.

Beschädigte oder widersprüchliche Evidence wird nicht als Abwesenheit
umgedeutet.

## Kanonischer Claim

Der Claim muss owner-only, regulär, einfach verlinkt und vollständig gegen die
LQ-351-Bindung validierbar sein.

Er bindet historische Autorität, LQ-349-Evidence, `resume_from`, Restbudget,
Ressourcen, Identitäten und eine zeitzonenbehaftete Startzeit.

Alter und Dateiname beweisen keinen Fortschritt.

Der Inspector repariert oder ersetzt keinen Claim.

## Frische LQ-341-Inspection

Nur bei offenem Cleanup- und Recontinuation-Claim ohne Evidence wird LQ-341
frisch mit historischer Autorisierung ausgeführt.

Die Ausgabe muss exakt Schema-Version, Operation
`disposable_postgres_runtime_cleanup_reconciliation` und einen geschlossenen
Ausgang enthalten.

Caller-gelieferte oder gespeicherte Beobachtungen werden nicht akzeptiert.

LQ-341 bestätigt Compose-Modell, Ressourcenordnung und unverändert
rungebundenes Datenvolume read-only.

## Geschlossene Präfixmatrix

Ab `container_removed` sind zulässig:

- derselbe Zustand als `recontinuation_not_started`;
- `application_network_removed`;
- `runtime_removed_evidence_missing`.

Ab `application_network_removed` sind zulässig:

- derselbe Zustand als `recontinuation_not_started`;
- `runtime_removed_evidence_missing`.

Jeder frühere oder außerhalb liegende Zustand ergibt `conflict`.

Dies umfasst `container_stopped`, `runtime_intact`, `final_evidence_present`,
unmögliche Ressourcenbilder und Volumeabweichung.

Kein Ausgang erteilt Fortsetzungs- oder Finalisierungsrecht.

## Strikte Read-only-Grenze

LQ-353 besitzt keinen Write-, Release-, Stop-, Start-, Remove-, Disconnect-,
Down-, Kill-, Prune- oder Volume-Mutationspfad.

Auch bei vollständiger Runtimeentfernung bleiben Cleanup- und
Recontinuation-Claim unverändert.

Docker-Events, Logs, Historie, SQL und Volumeinhalte werden nicht gelesen.

Technische Nichtverfügbarkeit endet ohne Ergebnisobjekt oder private Details.

## Ausgabe

Die CLI liefert nur Schema-Version, Operation
`disposable_postgres_cleanup_recontinuation_reconciliation` und:

- `not_found` oder `recontinuation_evidence_present`;
- `recontinuation_not_started`;
- `application_network_removed`;
- `runtime_removed_evidence_missing`;
- `conflict`.

Private IDs, Hashes, Pfade und Ressourcen verlassen die Grenze nicht.

## Tests

Fake-basierte Tests decken die vollständige Präfixmatrix für beide
Startzustände ab.

Claims werden vor und nach jeder Entscheidung bytegenau verglichen.

Weitere Tests beweisen Evidence-first mit und ohne Claim sowie `not_found`
ohne Aufruf des LQ-341-Inspectors.

## Bundle und Nichtziele

Entry Point und Operatormodul erhöhen die Gates auf 42 Entry Points und 46
Operatormodule. Migrationen bleiben 27 mit Head `20260819_0027`.

LQ-353 implementiert keine Claimfreigabe, Evidencepersistenz, weitere
Continuation, Cleanup-Finalisierung oder Volume-Löschung.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Domainmodell-,
Compose- oder Production-Wiring-Änderung.

## Nächster Slice

LQ-354 sollte die evidence-first Finalisierung eines reconcilierten
Recontinuation-Claims getrennt definieren.

Weitere Fortsetzung und jede Volumenlöschung bleiben separate Entscheidungen.
