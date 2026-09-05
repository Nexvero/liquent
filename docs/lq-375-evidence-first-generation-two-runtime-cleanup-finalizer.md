# LQ-375 — Evidence-first Generation-two Runtime Cleanup Finalizer

## Ergebnis

LQ-375 erweitert
`liquent-disposable-postgres-cleanup-generation-finalize` um den Abschluss
eines durch LQ-373 frisch reconcilierten Generation-2-Claims.

Der bestehende Generation-1-Pfad bleibt erhalten. Generation und direkte
Vorgängerart wählen weiterhin einen geschlossenen Validierungspfad.

## Geschlossene Generationen

Generation eins verlangt unverändert `predecessor_kind=lq362`, Generation null
als Vorgänger und keine Generation-Vorgängerdateien.

Generation zwei verlangt `predecessor_kind=repeatable_generation`, Generation
eins als Vorgänger sowie deren private Continuation- und Finalization-Datei.

Andere Generationen, gemischte Vorgängerarten und überzählige oder fehlende
Vorgängerdateien bleiben detailfrei technisch unavailable.

## Separate Finalisierungsautorisierung

Die owner-only Autorisierung bindet Finalization-, Reconciliation- und
Continuation-ID, Generation zwei, direkten Vorgänger und die vollständige
historische Root-Kette.

Sie bindet SHA-256 der LQ-373-Reconciliation-Autorisierung sowie der exakten
LQ-369-Autorisierung und Finalization-Evidence.

Operation bleibt exakt
`finalize_disposable_postgres_cleanup_generation_continuation`, Scope
`runtime_only` und das aktuelle UTC-Fenster höchstens eine Stunde.

Executor und Autorisierer müssen verschieden sein. Caller liefern weder
Zustand noch Ausgang, Claimstatus, Fortschritt oder Freigabeentscheidung.

## Direkte LQ-369-Basis

Die Generation-1-Continuation und ihre LQ-369-Finalisierung werden an den
historischen Fenstermittelpunkten erneut vollständig validiert.

Die gebundene LQ-369-Evidence muss owner-only, kanonisch und hashgenau sein.
Nur `generation_continuation_attempt_finalized` oder `later_prefix_finalized`
bilden eine nichtterminale Vorgängerbasis.

Der Vorgängerpräfix der Generation-2-Autorisierung muss mit dem Resume-Punkt
der Generation-1-Continuation übereinstimmen.

Ein noch vorhandener Generation-1-Claim wird exakt validiert und danach
fail-closed abgewiesen; der Finalizer entfernt ihn niemals.

## Historische Claim-Gates

Der ursprüngliche Cleanup-Claim muss offen und exakt gebunden sein.

LQ-345-, LQ-351- und LQ-358-Claims müssen fehlen. Ihre Anwesenheit wird nicht
als neutraler Zustand behandelt und gewährt keine Aufräumautorität.

Nur der aktuelle Generation-2-Claim darf nach erfolgreicher Evidence-Persistenz
freigegeben werden. Cleanup-Claim und Datenvolume bleiben erhalten.

## Frische Reconciliation

Fehlt passende Finalization-Evidence, führt der Finalizer LQ-373 frisch am
historischen Fenstermittelpunkt der gebundenen Reconciliation aus.

Dabei werden dieselben privaten Vorgängerdateien weitergereicht. Ein
gespeicherter oder caller-gelieferter Inspector-Ausgang wird nicht akzeptiert.

Die Ausgabe muss exakt die neutrale LQ-373-Struktur tragen; unbekannte Felder,
Operationen oder Zustände bleiben unavailable.

## Geschlossene Ausgangsmatrix

Die vier finalisierbaren Inspector-Zustände werden fest abgebildet:

- Evidence vorhanden → `generation_continuation_evidence_confirmed`;
- nicht gestartet → `generation_continuation_attempt_finalized`;
- Application-Network entfernt → `later_prefix_finalized`;
- Runtime vollständig entfernt →
  `runtime_removal_ready_for_cleanup_finalization`.

`not_found` bleibt neutral `not_found`; `conflict` wird neutral zu
`investigation_required`. Beide schreiben keine Evidence und lösen keinen
Claim.

Andere Zustände bleiben detailfrei technisch unavailable.

## Evidence-first-Freigabe

Bei einem finalisierbaren Zustand schreibt der Finalizer zuerst eine private,
kanonische und immutable Finalization-Evidence.

Sie bindet die vollständige Autorisierung, ihren SHA-256, den frisch
beobachteten Zustand, den geschlossenen Ausgang sowie Start- und Abschlusszeit.

Erst nach atomarem Write, Verzeichnis-Sync und erneutem exaktem Read darf der
aktuelle Generation-2-Claim entfernt und die Entfernung synchronisiert werden.

Ein Evidence-Writefehler oder eine widersprüchliche vorhandene Datei lässt den
Claim bestehen und endet unavailable.

## Sicherer Retry

Ist die exakte Finalization-Evidence bereits vorhanden, wird sie vollständig
validiert und ihr gespeicherter Ausgang wiederverwendet.

Der Retry überspringt LQ-373 und damit jeden Dockerzugriff. Nur ein noch offen
vorhandener, exakt gebundener aktueller Claim wird freigegeben.

Fehlgeschlagene Claimfreigabe kann dadurch ohne neue Beobachtung wiederholt
werden; fremde oder malformed Claims bleiben unangetastet unavailable.

## Neutrale CLI

Die bestehende CLI erhält zwei optionale Pfade für Generation-Continuation und
Finalisierung des direkten Vorgängers.

Generation eins weist beide zurück, Generation zwei verlangt beide. Es
entsteht kein neuer Entry Point.

Erfolg gibt nur Schema-Version, Operation
`disposable_postgres_cleanup_generation_continuation_finalization` und den
geschlossenen Ausgang aus. Technische Nichtverfügbarkeit endet mit Exitcode 2.

## Tests

Sieben neue Tests decken vier finalisierbare Generation-2-Zustände, zwei
neutrale Zustände und den Evidence-first-Retry nach unbekanntem
Claimfreigabeausgang ab.

Sie prüfen Generation zwei in der Evidence, Erhalt des Cleanup-Claims,
Freigabe ausschließlich des aktuellen Claims und den ausbleibenden zweiten
Inspectorzugriff.

Zusammen mit den Generation-1-Prüfungen bestehen 14 fokussierte
Finalizer-Tests.

## Bundle und Nichtziele

LQ-375 erweitert nur das bestehende Operatormodul und dessen CLI. Bundle-Gates
bleiben bei 49 Entry Points, 53 Operatormodulen, 27 Migrationen und Head
`20260819_0027`.

Keine Folgegeneration, Ressourcenmutation, Volume-Löschung, neue Migration,
Persistenz, Port-, Modell-, Signatur- oder Compose-Entscheidung wird ergänzt.

## Nächster Slice

LQ-376 sollte Generation eins und zwei gemeinsam auditieren und entscheiden,
welcher geschlossene Vertrag eine dauerhafte Folgegeneration erlaubt, ohne die
Vertrauenskette durch ungeprüfte Rekursion oder caller-gelieferte Historie zu
öffnen.
