# LQ-379 — Read-only Bounded Generation Lineage Inspector

## Ergebnis

LQ-379 erweitert
`liquent-disposable-postgres-cleanup-generation-reconcile` um die read-only
Reconciliation offener Claims ab Generation drei.

Generation eins und zwei behalten ihre bisherigen direkten Resolver.

## Gemeinsamer Lineage-Resolver

Ab Generation drei verwendet der Inspector denselben LQ-378-Resolver wie der
Continuation-Operator.

Die zwei geordneten Folgen enthalten exakt die Continuation- und
Finalisierungsautorisierungen der Generationen eins bis `n - 1`.

Länge und Gleichheit werden vor historischen Reads gegen die feste Obergrenze
16 geprüft.

Fehlende, überzählige, vertauschte, doppelte oder zu lange Lineages bleiben
detailfrei technisch unavailable.

## Genesis und direkte Kette

Generation eins muss weiterhin unmittelbar an die vollständige
LQ-362-Finalisierung und deren nichtterminale Evidence gebunden sein.

Jedes folgende Paar muss dieselbe kanonische Generation, Root-Kette und
Continuation-Fakten tragen.

Jede Continuation bindet Autorisierung und Evidence der unmittelbar vorherigen
Finalisierung hashgenau.

Alle historischen Autorisierungen werden an ihrem eigenen Fenstermittelpunkt
vollständig validiert.

Ältere, übersprungene oder caller-selektierte Vorgänger bleiben ausgeschlossen.

## Präfixrekonstruktion

Der Resolver rekonstruiert jeden historischen effektiven Präfix aus dem
Ausgang der direkten Vorgänger-Finalization-Evidence.

`generation_continuation_attempt_finalized` erhält den Vorgängerpräfix;
`later_prefix_finalized` ergibt `application_network_removed`.

Jede historische Continuation und die aktuelle Generation müssen diese
Fortschreibung exakt binden.

Terminale, neutrale, konfliktbehaftete oder unbekannte Evidence begründet
keine weitere Generation.

## Separate Reconciliation-Autorisierung

Die aktuelle owner-only Autorisierung bindet Reconciliation- und
Continuation-ID, Generation, direkten Vorgänger, vollständige Root-Kette und
SHA-256 der aktuellen Continuation-Autorisierung.

Operation bleibt exakt
`inspect_disposable_postgres_cleanup_generation_continuation`, Scope
`runtime_only` und das aktuelle UTC-Fenster höchstens eine Stunde.

Executor und Autorisierer sind getrennt. Caller liefern keinen Zustand,
Ausgang, Claimstatus, Präfix oder Allow-Bool.

## Historische Claims

Alle Claims der Lineage müssen exakt fehlen. Ein vorhandener historischer
Claim wird vollständig validiert und anschließend fail-closed abgewiesen.

Der Inspector entfernt, ersetzt oder repariert keinen historischen Claim.

LQ-345-, LQ-351- und LQ-358-Claims müssen ebenfalls fehlen; der ursprüngliche
LQ-339-Cleanup-Claim muss exakt offen bleiben.

Nur der aktuelle Generation-Claim ist Gegenstand der neutralen
Reconciliation.

## Evidence-Vorrang

Der Inspector prüft die aktuelle Continuation-Evidence vor dem aktuellen
Claim und vor LQ-341.

Ist exakte owner-only Evidence vorhanden, lautet der Ausgang
`generation_continuation_evidence_present`.

Der aktuelle Claim bleibt dabei offen und sämtliche Lineage-Artefakte bleiben
unverändert.

Malformed oder widersprüchliche Evidence bleibt technisch unavailable.

## Neutrale Claimabwesenheit

Fehlen aktuelle Evidence und aktueller Claim gemeinsam, ergibt der Inspector
neutral `not_found`.

Diese Abwesenheit beweist weder Runtimeentfernung noch Cleanup-Abschluss und
erteilt keine Finalisierungsautorität.

Ein vorhandener fremder oder malformed aktueller Claim bleibt unavailable und
wird nicht als Abwesenheit behandelt.

## Frische LQ-341-Klassifikation

Nur bei offenem exakt gebundenem Cleanup- und aktuellem Generation-Claim führt
der Inspector LQ-341 frisch und read-only aus.

Der historische Cleanup-Reconciliation-Zeitpunkt bleibt dessen ursprünglicher
Fenstermittelpunkt.

Caller-gelieferte oder gespeicherte Zustände werden nicht akzeptiert.

Die Ausgabe von LQ-341 muss exakt ihre geschlossene neutrale Struktur tragen.

## Geschlossene Zustandsmatrix

Für `resume_from=container_removed` gilt:

- gleicher Zustand → `generation_continuation_not_started`;
- `application_network_removed` → gleichnamiger Fortschritt;
- `runtime_removed_evidence_missing` → vollständige Entfernung;
- früherer oder unbekannter Zustand → `conflict`.

Für `resume_from=application_network_removed` gilt:

- gleicher Zustand → `generation_continuation_not_started`;
- `runtime_removed_evidence_missing` → vollständige Entfernung;
- `container_removed` oder jeder unbekannte Zustand → `conflict`.

Kein Ausgang gewährt Mutation, Claimfreigabe oder Finalisierung.

## Strikte Read-only-Grenze

Der Inspector liest private Autorisierungen, Claims und Evidence und verwendet
die bestehende read-only LQ-341-Composition.

Claimanlage, Claimfreigabe, Evidencewrite, Stop, Start, Remove, Disconnect,
Down, Kill, Prune, SQL und Volumezugriff bleiben ausgeschlossen.

Cleanup-, aktuelle und historische Claims sowie alle Lineage-Dateien bleiben
in sämtlichen Ausgängen bytegenau unverändert.

## CLI

Die bestehende CLI erhält dieselben zwei wiederholbaren Lineage-Optionen wie
der LQ-378-Continuation-Operator.

Generation eins und zwei weisen sie zurück. Ab Generation drei werden die
bisherigen einzelnen Vorgängeroptionen zurückgewiesen.

Erfolg gibt nur Schema-Version, Operation und geschlossenen Ausgang aus;
technische Nichtverfügbarkeit endet detailfrei mit Exitcode 2.

## Tests

Zehn neue Fake-basierte Tests decken die vollständige Generation-3-Matrix,
Evidence-Vorrang, neutrale Claimabwesenheit und vertauschte Lineage ab.

Sie vergleichen Cleanup-Claim, aktuellen Claim und alle Lineage-Dateien vor
und nach der Reconciliation bytegenau.

Zusammen mit Generation eins und zwei bestehen 28 fokussierte
Inspector-Tests und 56 Prüfungen der vollständigen Generation-Kette.

## Bundle und Nichtziele

LQ-379 erweitert nur das bestehende Inspector-Modul und dessen bestehenden
Entry Point. Bundle-Gates bleiben bei 49 Entry Points, 53 Operatormodulen, 27
Migrationen und Head `20260819_0027`.

Keine Claimfreigabe, Finalisierung, Ressourcenmutation, automatische
Folgegeneration, Migration, Persistenz, Port-, Modell-, Compose- oder
Production-Wiring-Entscheidung wird ergänzt.

## Nächster Slice

LQ-380 sollte den evidence-first Generation-Finalizer auf denselben begrenzten
Lineage-Resolver erweitern.

Er darf ausschließlich den aktuellen Claim nach eigener atomarer
Finalization-Evidence freigeben.
