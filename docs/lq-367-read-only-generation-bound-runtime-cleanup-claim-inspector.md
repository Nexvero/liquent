# LQ-367 — Read-only Generation-bound Runtime Cleanup Claim Inspector

## Ergebnis

LQ-367 installiert
`liquent-disposable-postgres-cleanup-generation-reconcile` als strikt
read-only Inspector eines offenen LQ-365-Generation-Claims.

Er klassifiziert den aktuellen Runtimepräfix relativ zum autoritativ gebundenen
Startpräfix und verändert weder Claims noch Evidence oder Ressourcen.

## Separate Autorisierung

Die neue owner-only Reconciliation-Autorisierung bindet
Generation-Reconciliation-ID, Generation-Continuation-ID, Generation,
Vorgängerart und Vorgängergeneration.

Sie bindet außerdem die vollständige Root-Kette, direkte
Vorgänger-Finalization-Evidence, LQ-365-Autorisierung sowie historischen und
effektiven Startpräfix.

Operation ist exakt
`inspect_disposable_postgres_cleanup_generation_continuation`, Scope exakt
`runtime_only` und das aktuelle UTC-Fenster höchstens eine Stunde.

Executor und Autorisierer sind getrennt. Caller liefern keinen Zustand,
Fortschritt, Claimstatus oder gewünschten Ausgang.

## Aktuelle Generationsgrenze

Der Inspector akzeptiert ausschließlich Generation eins mit direktem
LQ-362-Vorgänger.

LQ-362-Autorisierung und exakte Finalization-Evidence werden an ihrer
historischen Bindung erneut vollständig geprüft.

Eine andere Generation, Vorgängerart oder Hashbindung bleibt fail-closed und
detailfrei technisch unavailable.

## Claim-Gates

Der ursprüngliche LQ-339-Cleanup-Claim muss offen und kanonisch gebunden sein.

LQ-345-, LQ-351- und LQ-358-Claims müssen exakt fehlen. Vorhandene historische
Claims werden validiert, aber niemals entfernt oder neutralisiert.

Der aktuelle Generation-Claimname stammt ausschließlich aus SHA-256 der
Generation-Continuation-ID.

Malformed Claims bleiben unavailable; Alter oder Dateiname beweist keinen
Fortschritt.

## Evidence-first

Exakte generationengebundene LQ-365-Evidence wird vor Docker geprüft.

Ist sie vorhanden, lautet der Ausgang
`generation_continuation_evidence_present`, unabhängig davon, ob der aktuelle
Claim nach unbekannter Freigabe noch vorhanden ist.

Fehlen Evidence und Claim gemeinsam, ergibt der Inspector `not_found` ohne
Dockerzugriff.

Evidence und Claim bleiben in beiden Fällen unverändert.

## Frische Klassifikation

Nur bei offenem Cleanup- und Generation-Claim ohne Evidence führt LQ-367 die
bestehende LQ-341-Reconciliation frisch aus.

Die historische Cleanup-Reconciliation-Autorisierung wird an ihrem
ursprünglichen Fenstermittelpunkt ausgewertet.

Gespeicherte oder caller-gelieferte Zustände werden nicht akzeptiert.

Das Datenvolume muss in jedem zulässigen Präfix unverändert rungebunden sein.

## Geschlossene Präfixmatrix

Für `resume_from=container_removed` gilt:

- `container_removed` → `generation_continuation_not_started`;
- `application_network_removed` → `application_network_removed`;
- `runtime_removed_evidence_missing` bleibt gleich;
- frühere oder unbekannte Zustände → `conflict`.

Für `resume_from=application_network_removed` gilt:

- `application_network_removed` → `generation_continuation_not_started`;
- `runtime_removed_evidence_missing` bleibt gleich;
- `container_removed` oder jeder andere Zustand → `conflict`.

Keine Klassifikation gewährt Mutations- oder Finalisierungsautorität.

## Strikte Read-only-Grenze

Der Inspector verwendet ausschließlich private Dateireads und die bestehende
read-only LQ-341-Composition.

Claimanlage, Claimfreigabe, Evidencewrite, Stop, Start, Remove, Disconnect,
Down, Kill, Prune, SQL und Volumezugriff sind ausgeschlossen.

Cleanup- und Generation-Claim bleiben auch bei vollständiger
Runtimeentfernung unverändert.

## Neutrale CLI

Die Ausgabe enthält ausschließlich Schema-Version, Operation
`disposable_postgres_cleanup_generation_continuation_reconciliation` und einen
geschlossenen Ausgang.

Private Generation, IDs, Hashes, Pfade, Ressourcen und Fehlerdetails bleiben
verborgen.

Technische Nichtverfügbarkeit endet mit Exitcode 2 ohne stdout oder stderr.

## Tests

Neun Fake-basierte Tests decken die vollständige Präfixmatrix für beide
Startpräfixe, Evidence-Vorrang und neutrale Claimabwesenheit ab.

Die Matrixtests vergleichen Cleanup- und Generation-Claim bytegenau vor und
nach jedem Inspectoraufruf.

## Bundle und Nichtziele

Entry Point und Operatormodul erhöhen die Gates auf 48 Entry Points und 52
Operatormodule. Migrationen bleiben 27 mit Head `20260819_0027`.

LQ-367 implementiert keine Finalisierung, Folgegeneration, Claimfreigabe,
Ressourcenmutation oder Volume-Löschung.

## Nächster Slice

LQ-368 sollte den evidence-first Finalisierungsvertrag für einen durch LQ-367
reconcilierten Generation-Claim definieren.

Erst dessen Finalization-Evidence darf eine spätere direkte Folgegeneration
begründen.
