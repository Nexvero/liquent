# LQ-369 — Evidence-first Generation-bound Runtime Cleanup Finalizer

## Ergebnis

LQ-369 installiert
`liquent-disposable-postgres-cleanup-generation-finalize` für einen durch
LQ-367 reconciliierten Generation-Claim.

Der Finalizer persistiert kanonische Generation-Finalization-Evidence vor der
Freigabe ausschließlich des exakt gebundenen aktuellen Claims.

## Autorisierung und Generation

Die neue owner-only Autorisierung bindet Finalization-, Reconciliation- und
Continuation-ID, Generation, direkten Vorgänger und vollständige Root-Kette.

Sie bindet SHA-256 der LQ-365- und LQ-367-Autorisierung sowie der direkten
LQ-362-Autorisierung und Finalization-Evidence.

Aktuell ist ausschließlich Generation eins mit `predecessor_kind=lq362` und
Vorgängergeneration null zulässig.

Operation ist exakt `finalize_disposable_postgres_cleanup_generation_continuation`,
Scope exakt `runtime_only`, das UTC-Fenster höchstens eine Stunde und Executor
vom Autorisierer getrennt.

## Historische Validierung

Root-, LQ-362-, LQ-365- und LQ-367-Bindung werden vollständig erneut geprüft.

Historische Autorisierungen werden an ihren ursprünglichen Fenstermittelpunkten
ausgewertet und durch LQ-369 nicht verlängert.

Generation, Vorgänger, beide Präfixe, IDs, Hashes, Run und Projektname müssen
dieselbe unveränderte Kette beschreiben.

Caller liefern keinen Zustand, Claimstatus oder Zielausgang.

## Claim-Gates

Der ursprüngliche Cleanup-Claim muss kanonisch gebunden offen sein.

LQ-345-, LQ-351- und LQ-358-Claims müssen exakt fehlen. Vorhandene historische
Claims bleiben unavailable und werden niemals entfernt.

Nur der aktuelle Generation-Claim liegt innerhalb der Freigabegrenze.

Seine Abwesenheit vor Finalization-Evidence bleibt neutral beziehungsweise
über LQ-367 `not_found`.

## Evidence-first und frische Entscheidung

Der Evidencename stammt ausschließlich aus SHA-256 der
Generation-Finalization-ID.

Exakt vorhandene Finalization-Evidence wird vor LQ-367 vollständig gelesen und
steuert den idempotenten Retry.

Ohne Evidence führt LQ-369 LQ-367 frisch mit der historischen
Reconciliation-Autorisierung aus.

Gespeicherte oder caller-gelieferte Ausgänge werden nicht akzeptiert.

## Geschlossene Zuordnung

- `generation_continuation_evidence_present` wird
  `generation_continuation_evidence_confirmed`;
- `generation_continuation_not_started` wird
  `generation_continuation_attempt_finalized`;
- `application_network_removed` wird `later_prefix_finalized`;
- `runtime_removed_evidence_missing` wird
  `runtime_removal_ready_for_cleanup_finalization`.

`not_found` bleibt neutral ohne Write. `conflict` ergibt
`investigation_required` ohne Claim- oder Evidenceänderung.

Unbekannte oder malformed Ausgänge bleiben technisch unavailable.

## Kanonische Finalization-Evidence

Der Record bindet Generation, direkten Vorgänger, Root-Kette, beide Präfixe,
frisch beobachteten Zustand, Ausgang, Identitäten und UTC-Zeitpunkte.

Er wird owner-only exklusiv geschrieben, synchronisiert, atomar final verlinkt
und vollständig zurückgelesen.

Erst erfolgreiche Rücklesung erlaubt Claimfreigabe.

Nichtterminale Evidence ist der kanonische direkte Vorgängeranker für eine
spätere Generation zwei; sie erteilt selbst keine Mutationsautorität.

## Exakte Claimfreigabe

Der Claimname stammt ausschließlich aus SHA-256 der
Generation-Continuation-ID.

Vor Freigabe wird der Claim vollständig gegen dieselbe LQ-365-Bindung geprüft.

Nur dieser eine Claim wird entfernt und das Evidenceverzeichnis synchronisiert.

Ein bereits abwesender Claim gilt als idempotent freigegeben. Suche, Alter,
Präfix-, Label- oder Gruppenauswahl existieren nicht.

## Unbekannte Freigabe

Schlägt die Freigabe nach persistierter Evidence technisch fehl, bleibt die
Evidence maßgeblich und der Command unavailable.

Der Retry validiert dieselbe Evidence und wiederholt ausschließlich die
Freigabe des exakten Generation-Claims.

LQ-367 und Docker werden nicht erneut aufgerufen; eine zweite Evidence wird
nicht geschrieben.

Ein fremder oder beschädigter Claim wird niemals entfernt.

## Unveränderte Grenzen

Cleanup-Claim, Datenvolume, Ressourcen sowie historische Autorisierungen und
Evidence bleiben unverändert.

Terminale Ausgänge werden weiterhin separat über LQ-343 abgeschlossen.

Nichtterminale Ausgänge starten Generation zwei nicht automatisch.

Die CLI gibt nur Schema-Version, Operation und neutralen Ausgang aus;
technische Nichtverfügbarkeit endet mit Exitcode 2 ohne private Details.

## Tests und Bundle

Sieben Fake-basierte Tests decken vier finalisierbare Beobachtungen,
`not_found`, `conflict` und unbekannte Claimfreigabe mit evidence-first Retry ab.

Entry Point und Operatormodul erhöhen die Gates auf 49 Entry Points und 53
Operatormodule. Migrationen bleiben 27 mit Head `20260819_0027`.

LQ-369 implementiert keine Folgegeneration, automatische Schleife,
Ressourcenmutation, LQ-343-Ausführung oder Volume-Löschung.

## Nächster Slice

LQ-370 sollte den direkten Generation-2-Continuation-Vertrag auf Basis
nichtterminaler LQ-369-Finalization-Evidence definieren.
