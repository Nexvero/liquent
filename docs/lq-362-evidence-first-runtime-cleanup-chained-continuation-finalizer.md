# LQ-362 — Evidence-first Runtime Cleanup Chained Continuation Finalizer

## Ergebnis

LQ-362 installiert
`liquent-disposable-postgres-cleanup-chain-finalize` als kontrollierten
Finalizer für einen durch LQ-360 reconcilierten LQ-358-Versuch.

Er persistiert private Finalization-Evidence vor der Freigabe ausschließlich
des exakt gebundenen aktuellen Chained-Continuation-Claims.

## Neue Autorisierung

Die owner-only Autorisierung bindet Chained-Finalization-, Reconciliation-,
Continuation-, Recontinuation-, Cleanup- und Run-Kette geschlossen.

Sie enthält beide Startpräfixe, sämtliche historischen Evidence- und
Autorisierungshashes und den SHA-256 der vollständigen LQ-360-Autorisierung.

Operation ist exakt
`finalize_disposable_postgres_cleanup_chained_continuation`, Scope exakt
`runtime_only` und das aktuelle UTC-Fenster höchstens eine Stunde lang.

Executor und Autorisierer müssen getrennt sein. Caller liefern keinen Zustand,
Claimstatus oder gewünschten Ausgang.

## Historische Validierung

LQ-358 und LQ-360 werden an ihren ursprünglichen Fenstermittelpunkten erneut
validiert; die aktuelle Finalisierungsautorisierung verlängert sie nicht.

IDs, Hashes, `previous_resume_from`, `resume_from`, Run und Projektname müssen
dieselbe unveränderte Kette beschreiben.

Eine abweichende, beschädigte oder nicht private Bindung bleibt detailfrei
technisch unavailable.

## Claim-Gates

Der ursprüngliche LQ-339-Cleanup-Claim muss vollständig gebunden offen sein.
Seine Abwesenheit ergibt `investigation_required`.

LQ-345-Continuation- und LQ-351-Recontinuation-Claim müssen exakt fehlen.
Vorhandene historische Claims bleiben unavailable und werden nie entfernt.

Nur der aktuelle LQ-358-Claim liegt innerhalb der Freigabegrenze.

## Evidence-first

Der Evidencename wird ausschließlich aus dem vollständigen SHA-256 der
Chained-Finalization-ID abgeleitet.

Exakt vorhandene Evidence wird vor LQ-360 vollständig zurückgelesen und
steuert den idempotenten Retry.

Sie muss owner-only, regulär, einfach verlinkt und kanonisch gebunden sein.
Beschädigte oder widersprüchliche Evidence wird nicht überschrieben.

## Frische LQ-360-Entscheidung

Ohne Finalization-Evidence führt LQ-362 LQ-360 unmittelbar mit der historischen
Reconciliation-Autorisierung aus.

Die Ausgabe muss exakt Schema-Version, Operation
`disposable_postgres_cleanup_chained_continuation_reconciliation` und einen
geschlossenen Ausgang enthalten.

Ein gespeicherter oder caller-gelieferter Ausgang wird nicht akzeptiert.

## Geschlossene Zuordnung

Die implementierte Zuordnung lautet:

- `chained_continuation_evidence_present` wird
  `chained_continuation_evidence_confirmed`;
- `chained_continuation_not_started` wird
  `chained_continuation_attempt_finalized`;
- `application_network_removed` wird `later_prefix_finalized`;
- `runtime_removed_evidence_missing` wird
  `runtime_removal_ready_for_cleanup_finalization`.

`not_found` wird ohne Write neutral weitergegeben. `conflict` ergibt
`investigation_required` ohne Claim- oder Evidenceänderung.

Unbekannte Ausgänge bleiben technisch unavailable.

## Private Finalization-Evidence

Der Record bindet alle IDs und Hashes, beide Startpräfixe, den frisch
beobachteten Zustand, Ausgang, getrennte Identitäten und UTC-Zeitpunkte.

Er wird owner-only exklusiv geschrieben, synchronisiert, atomar final verlinkt
und vollständig zurückgelesen.

LQ-362 erzeugt keine LQ-358- oder historische Cleanup-Evidence nachträglich.
Erst erfolgreiche Rücklesung erlaubt Claimfreigabe.

## Exakte Claimfreigabe

Der aktuelle Claimname stammt ausschließlich aus dem SHA-256 der
Chained-Continuation-ID.

Vor Freigabe wird er vollständig gegen dieselbe LQ-358-Bindung geprüft. Nur
dieser Claim wird entfernt und das Evidenceverzeichnis synchronisiert.

Ein bereits abwesender Claim gilt als idempotent freigegeben. Suche, Alter,
Präfix-, Label- oder Gruppenauswahl existieren nicht.

## Unbekannte Freigabe

Schlägt die Freigabe nach persistierter Evidence technisch fehl, bleibt die
Evidence maßgeblich und der Command unavailable.

Der Retry validiert dieselbe Evidence und wiederholt ausschließlich die exakte
Claimfreigabe. LQ-360 und Docker werden nicht erneut aufgerufen.

Ein fremder oder beschädigter Claim wird niemals entfernt.

## Unveränderte Grenzen

Cleanup-Claim, Datenvolume, Ressourcen sowie historische Autorisierungen und
Evidence bleiben unverändert.

Kein Ausgang startet Folgearbeit. Terminale Ausgänge benötigen weiterhin die
getrennte LQ-343-Cleanup-Finalisierung.

Die CLI gibt nur Schema-Version, Operation und neutralen Ausgang aus.
Technische Nichtverfügbarkeit endet mit Exitcode 2 ohne private Details.

## Tests und Bundle

Sieben Fake-basierte Tests decken vier finalisierbare Beobachtungen,
`not_found`, `conflict` und unbekannte Claimfreigabe mit evidence-first Retry ab.

Entry Point und Operatormodul erhöhen die Gates auf 46 Entry Points und 50
Operatormodule. Migrationen bleiben 27 mit Head `20260819_0027`.

LQ-362 implementiert keine weitere Continuation, Ressourcenmutation,
Cleanup-Finalisierung oder Volume-Löschung.

## Nächster Slice

LQ-363 sollte den vollständigen Cleanup-Continuation-Chain-Abschluss erneut
auditieren und den nächsten notwendigen Schritt nur aus belegter Restarbeit
ableiten.
