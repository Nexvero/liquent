# LQ-349 — Evidence-first Runtime Cleanup Continuation Finalizer

## Ergebnis

LQ-349 installiert
`liquent-disposable-postgres-cleanup-continue-finalize` als kontrollierten
Finalizer für einen durch LQ-347 reconcilierten Continuation-Versuch.

Er schreibt nur private Continuation-Finalization-Evidence und gibt danach
ausschließlich den exakt gebundenen LQ-345-Continuation-Claim frei.

## Finalisierungsautorisierung

Die neue owner-only Autorisierung bindet geschlossen:

- Continuation-Finalization-, Continuation-Reconciliation-, Continuation-,
  Cleanup-Reconciliation-, Cleanup- und Run-ID;
- Phase, Source-Commit, Image-Referenz und Compose-Hash;
- die ursprüngliche Reconciliation-, Claim- und Dispositionskette;
- alle vorgelagerten Evidence- und Autorisierungshashes;
- SHA-256 der vollständigen LQ-341-, LQ-345- und LQ-347-Autorisierung;
- Scope `runtime_only` und das historische `resume_from`;
- Operation `finalize_disposable_postgres_cleanup_continuation`;
- getrennte Executor- und Autorisiereridentitäten;
- ein aktuelles UTC-Fenster von höchstens einer Stunde.

Unbekannte Felder, doppelte Schlüssel und falsche Typen werden abgelehnt.

## Historische Autorität

LQ-345 und LQ-347 werden an ihrem ursprünglichen Fenstermittelpunkt erneut
validiert.

Die neue Finalisierungsautorisierung wird mit der aktuellen Clock geprüft und
verlängert keine historische Mutations- oder Inspection-Autorität.

IDs, Hashes, `resume_from`, Cleanup, Run und Projektname müssen exakt dieselbe
Kette beschreiben.

Caller liefern weder Beobachtung noch Claimstatus oder Zielausgang.

## Cleanup-Claim-Gate

Der ursprüngliche LQ-339-Cleanup-Claim wird aus dem SHA-256 der Cleanup-ID
abgeleitet und vollständig gegen seine kanonische Bindung geprüft.

Seine Abwesenheit ergibt vor LQ-347 neutral `investigation_required`.

Ein malformed oder fremd gebundener Cleanup-Claim bleibt technisch
unavailable.

LQ-349 gibt diesen Claim in keinem Ausgang frei.

## Evidence-first-Ordnung

Der Name der Finalization-Evidence stammt nur aus dem vollständigen SHA-256
der Continuation-Finalization-ID.

Exakt vorhandene Evidence wird vor LQ-347 vollständig zurückgelesen und
steuert den idempotenten Freigabe-Retry.

Sie muss owner-only, regulär, einfach verlinkt und kanonisch gebunden sein.

Beschädigte oder widersprüchliche Evidence bleibt unavailable und wird nie
überschrieben.

## Frische LQ-347-Reconciliation

Ohne Finalization-Evidence führt LQ-349 den LQ-347-Inspector unmittelbar mit
seiner historischen Autorisierung neu aus.

Die Ausgabe muss exakt Schema-Version, Operation
`disposable_postgres_cleanup_continuation_reconciliation` und einen
geschlossenen Ausgang enthalten.

Ein gespeicherter oder caller-gelieferter Ausgang wird nicht akzeptiert.

LQ-347 bleibt strikt read-only und beobachtet Docker nur bei offenem
Doppelclaim ohne Continuation-Evidence.

## Geschlossene Zuordnung

Die implementierte Zuordnung lautet:

- `continuation_evidence_present` wird
  `continuation_evidence_confirmed`;
- `continuation_not_started` wird `continuation_attempt_finalized`;
- `container_removed` und `application_network_removed` werden
  `later_prefix_finalized`;
- `runtime_removed_evidence_missing` wird
  `runtime_removal_ready_for_cleanup_finalization`.

`not_found` wird ohne Write neutral weitergegeben.

`conflict` ergibt `investigation_required` ohne Claim- oder Evidenceänderung.

Jeder unbekannte Inspector-Ausgang bleibt technisch unavailable.

## Private Finalization-Evidence

Der neue Record bindet alle IDs und Hashes, `resume_from`, den frisch
beobachteten Zustand, den daraus abgeleiteten Ausgang, getrennte Identitäten,
den Finalisierungsautorisierungshash sowie UTC-Start und Abschluss.

Er wird owner-only per exklusiver Temporäranlage geschrieben, synchronisiert,
atomar final verlinkt und vollständig zurückgelesen.

LQ-349 erzeugt weder LQ-345-Continuation-Evidence noch LQ-339-Cleanup-Evidence
nachträglich.

Erst erfolgreiche Rücklesung erlaubt die Continuation-Claimfreigabe.

## Exakte Claimfreigabe

Der Continuation-Claimname wird nur aus dem SHA-256 der Continuation-ID
abgeleitet.

Vor Freigabe muss ein vorhandener Claim vollständig mit derselben
LQ-345-Evidence-Bindung übereinstimmen.

Nur dieser exakte Claim wird entfernt und das Evidenceverzeichnis danach
synchronisiert.

Ein bereits abwesender Claim gilt als idempotent freigegeben.

Suche, Alter, Präfix-, Label- oder Gruppenauswahl existieren nicht.

## Unbekannte Freigabe und Retry

Schlägt die Claimfreigabe nach persistierter Evidence technisch fehl, bleibt
die Evidence maßgeblich und der Command unavailable.

Der Retry validiert zuerst dieselbe Evidence und wiederholt ausschließlich
die Freigabe des exakten Continuation-Claims.

LQ-347 und Docker werden dabei nicht erneut aufgerufen.

Ein fremder oder beschädigter Claim wird niemals entfernt.

## Unveränderte ursprüngliche Kette

Der LQ-339-Cleanup-Claim bleibt nach jeder erfolgreichen Finalisierung offen.

Ressourcen, Datenvolume und sämtliche historischen Autorisierungen und
Evidence bleiben unverändert.

Ein späterer Teilpräfix gewährt keine automatische Fortsetzungsautorität.

Vollständige Runtimeentfernung benötigt weiterhin die getrennte
LQ-343-Cleanup-Finalisierung.

## CLI-Grenze

Die CLI gibt ausschließlich Schema-Version, Operation
`disposable_postgres_cleanup_continuation_finalization` und den neutralen
Ausgang aus.

Technische Nichtverfügbarkeit endet mit Exitcode 2 ohne stdout, stderr oder
private Details.

## Tests

Fake-basierte Tests decken alle fünf finalisierbaren Beobachtungen, `not_found`,
`conflict`, fehlenden Cleanup-Claim und eine falsche LQ-347-Hashbindung ab.

Ein eigener Test erzwingt unbekannte Claimfreigabe nach Evidence und beweist,
dass der Retry ohne Inspector nur die Freigabe abschließt.

Die Tests bestätigen, dass der ursprüngliche Cleanup-Claim stets erhalten
bleibt und keine Dockerprozesse ausgeführt werden.

## Bundle und Nichtziele

Entry Point und Operatormodul erhöhen die Gates auf 40 Entry Points und 44
Operatormodule. Migrationen bleiben 27 mit Head `20260819_0027`.

LQ-349 implementiert keine neue Continuation, Cleanup-Finalisierung,
Ressourcenmutation oder Volume-Löschung.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Domainmodell-,
Compose- oder Production-Wiring-Änderung.

## Nächster Slice

LQ-350 sollte den autorisierten Vertrag für eine neue Continuation ab einem
durch LQ-349 belegten späteren Präfix definieren.

Die ursprüngliche Cleanup-Finalisierung und jede Volumenlöschung bleiben
separate Grenzen.
