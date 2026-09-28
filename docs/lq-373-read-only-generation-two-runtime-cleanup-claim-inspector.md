# LQ-373 — Read-only Generation-two Runtime Cleanup Claim Inspector

## Ergebnis

LQ-373 erweitert
`liquent-disposable-postgres-cleanup-generation-reconcile` um die strikt
read-only Reconciliation offener Generation-2-Claims.

Der bestehende Generation-1-Pfad bleibt unverändert; Generation und
Vorgängerart bestimmen jeweils den einzigen zulässigen Resolver.

## Zwei geschlossene Resolver

Generation eins akzeptiert weiterhin nur den direkten LQ-362-Vorgänger und
weist Generation-Vorgängerdateien zurück.

Generation zwei verlangt `predecessor_kind=repeatable_generation`,
Vorgängergeneration eins und beide privaten Vorgängerdateien.

Andere Generationen, fehlende Dateien oder gemischte Bindungen bleiben
detailfrei technisch unavailable.

## Separate Autorisierung

Die Generation-2-Reconciliation-Autorisierung bindet Reconciliation- und
Continuation-ID, Generation zwei, direkten Vorgänger und vollständige
historische Root-Kette.

Sie bindet SHA-256 der LQ-371-Autorisierung sowie der vollständigen
LQ-369-Autorisierung und exakten Finalization-Evidence.

Operation bleibt exakt
`inspect_disposable_postgres_cleanup_generation_continuation`, Scope
`runtime_only` und das aktuelle UTC-Fenster höchstens eine Stunde.

Executor und Autorisierer sind getrennt. Caller liefern keinen Zustand,
Fortschritt, Claimstatus oder Ausgang.

## Direkte LQ-369-Validierung

Generation-1-Continuation und LQ-369-Finalisierung werden an ihren historischen
Fenstermittelpunkten erneut validiert.

Die LQ-369-Evidence muss kanonisch, owner-only und mit
`generation_continuation_attempt_finalized` oder `later_prefix_finalized`
abgeschlossen sein.

Historischer und effektiver Präfix werden daraus getrennt rekonstruiert.

Eine Hashabweichung, terminale Evidence oder ältere direkte Vorgängerbindung
bleibt unavailable.

## Claim-Gates

Der ursprüngliche Cleanup-Claim muss vollständig gebunden offen sein.

LQ-345-, LQ-351- und LQ-358-Claims müssen fehlen. Der Generation-1-Claim wird
aus seiner ID abgeleitet und muss ebenfalls exakt abwesend sein.

Ein vorhandener historischer Claim wird validiert, aber niemals entfernt oder
als neutraler Zustand behandelt.

Nur der aktuelle Generation-2-Claim ist Gegenstand der Reconciliation.

## Evidence-first

Exakte Generation-2-Continuation-Evidence wird vor Docker vollständig geprüft.

Ist sie vorhanden, lautet der Ausgang
`generation_continuation_evidence_present`; ein offener Claim bleibt erhalten.

Fehlen Evidence und Claim gemeinsam, ergibt der Inspector `not_found` ohne
Dockerzugriff.

Malformed oder widersprüchliche Evidence bleibt technisch unavailable.

## Frische LQ-341-Klassifikation

Nur bei offenem Cleanup- und Generation-2-Claim ohne Evidence führt der
Inspector LQ-341 frisch und read-only aus.

Gespeicherte oder caller-gelieferte Zustände werden nicht akzeptiert.

Das Datenvolume muss in jedem zulässigen Präfix unverändert rungebunden
vorhanden sein.

## Geschlossene Präfixmatrix

Für `resume_from=container_removed` gilt:

- gleicher Zustand → `generation_continuation_not_started`;
- `application_network_removed` → gleichnamiger Fortschritt;
- `runtime_removed_evidence_missing` → vollständige Entfernung;
- früherer oder unbekannter Zustand → `conflict`.

Für `resume_from=application_network_removed` gilt:

- gleicher Zustand → `generation_continuation_not_started`;
- `runtime_removed_evidence_missing` → vollständige Entfernung;
- `container_removed` oder jeder andere Zustand → `conflict`.

Keine Klassifikation gewährt Mutations- oder Finalisierungsautorität.

## Strikte Read-only-Grenze

Der Inspector verwendet ausschließlich private Dateireads und die bestehende
read-only LQ-341-Composition.

Claimanlage, Claimfreigabe, Evidencewrite, Stop, Start, Remove, Disconnect,
Down, Kill, Prune, SQL und Volumezugriff bleiben ausgeschlossen.

Cleanup-, Generation-1- und Generation-2-Claim bleiben in sämtlichen Ausgängen
unverändert.

## Neutrale CLI

Die bestehende CLI erhält zwei optionale Vorgängerdateipfade. Generation eins
weist sie zurück; Generation zwei verlangt beide.

Die Ausgabe enthält nur Schema-Version, Operation
`disposable_postgres_cleanup_generation_continuation_reconciliation` und den
geschlossenen Ausgang.

Private Generation, IDs, Hashes, Pfade, Ressourcen und Fehlerdetails bleiben
verborgen. Technische Nichtverfügbarkeit endet mit Exitcode 2.

## Tests

Neun neue Fake-basierte Tests decken die vollständige Generation-2-Matrix,
Evidence-Vorrang und neutrale Claimabwesenheit ab.

Sie erzeugen einen echten offenen Claim über einen unbekannten LQ-371-Ausgang
und vergleichen Cleanup- und Generation-2-Claim bytegenau vor und nach der
Reconciliation.

Zusammen mit Generation eins bestehen 18 fokussierte Inspector-Tests.

## Bundle und Nichtziele

Es entsteht kein neuer Entry Point oder Operatormodul. Bundle-Gates bleiben bei
49 Entry Points, 53 Operatormodulen, 27 Migrationen und Head `20260819_0027`.

LQ-373 implementiert keine Generation-2-Finalisierung, Folgegeneration,
Claimfreigabe, Ressourcenmutation oder Volume-Löschung.

## Nächster Slice

LQ-374 sollte den evidence-first Finalisierungsvertrag für einen durch LQ-373
reconcilierten Generation-2-Claim definieren.
