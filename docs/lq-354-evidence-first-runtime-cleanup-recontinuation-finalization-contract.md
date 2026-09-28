# LQ-354 — Evidence-first Runtime Cleanup Recontinuation Finalization Contract

## Zweck
LQ-354 definiert die kontrollierte Finalisierung eines durch LQ-353
reconcilierten LQ-351-Recontinuation-Versuchs.

Sie persistiert getrennte private Evidence vor möglicher Freigabe des exakten
Recontinuation-Claims. Dieser Slice implementiert keinen Command oder Write.
## Separate Finalisierungsautorisierung
Recontinuation und Reconciliation gewähren kein Finalisierungsrecht.
Ein späterer Finalizer benötigt eine neue owner-only Autorisierung mit
stabiler, nicht wiederverwendbarer Recontinuation-Finalization-ID.
Sie muss mindestens geschlossen binden:

- Recontinuation-Finalization-, Recontinuation-Reconciliation- und
  Recontinuation-ID;
- Continuation-Finalization-, alte Continuation-, Cleanup-Reconciliation-,
  Cleanup- und Run-ID;
- Phase `disposable_postgres`, Source-Commit, Image-Digest und Compose-Hash;
- ursprüngliche Reconciliation-, Claim-Reconciliation- und Disposition-ID;
- sämtliche vorgelagerten Evidence- und Autorisierungshashes;
- SHA-256 der LQ-341-, LQ-345-, LQ-347-, LQ-349-, LQ-351- und
  LQ-353-Autorisierung;
- SHA-256 der exakten LQ-349-Finalization-Evidence;
- Scope exakt `runtime_only` und dasselbe `resume_from`;
- Operation exakt `finalize_disposable_postgres_cleanup_recontinuation`;
- neue getrennte Executor- und Autorisiereridentitäten;
- aktuelles UTC-Fenster von höchstens einer Stunde.

Caller liefern weder beobachteten Zustand noch Claimstatus oder Zielausgang.
## Vollständige historische Bindung
Der Finalizer validiert die gesamte Run-, Dispositions-, Cleanup-,
Continuation-, LQ-349-, LQ-351- und LQ-353-Kette erneut.

Historische Autorisierungen werden nur an ihrem ursprünglich gültigen
Fenstermittelpunkt ausgewertet.

Die neue Finalisierungsautorisierung muss aktuell sein und verlängert keine
frühere Mutations- oder Reconciliation-Autorität.

Alle IDs, Hashes, `resume_from`, Ressourcenbindungen und der Projektname
müssen exakt dieselbe unveränderte Kette beschreiben.
## LQ-349-Evidence bleibt Anker
Die ursprüngliche Continuation-Finalization-Evidence muss weiterhin
owner-only, kanonisch und exakt gebunden sein.

Sie muss Ausgang `later_prefix_finalized` und denselben durch LQ-351
übernommenen Startpräfix enthalten.

Sie wird weder ersetzt noch durch die neue Recontinuation-Finalization-
Evidence umgedeutet.

Eine Hash- oder Bindungsabweichung bleibt technisch unavailable.
## Ursprünglicher Cleanup-Claim
Der LQ-339-Cleanup-Claim muss vor jeder Finalisierung offen, kanonisch und
exakt an den ursprünglichen Run gebunden sein.

Seine Abwesenheit ist `investigation_required`, weil der Recontinuation-
Versuch nicht isoliert von der Cleanup-Lebensdauer abgeschlossen wird.

Ein beschädigter oder fremd gebundener Cleanup-Claim bleibt unavailable.

LQ-354 gibt den ursprünglichen Cleanup-Claim niemals frei.
## Historische Claim-Abwesenheit
Der alte LQ-345-Continuation-Claim muss weiterhin exakt abwesend sein.

Ein vorhandener alter Claim kennzeichnet eine unvollständige historische
Finalisierung und bleibt technisch unavailable.

Der Finalizer entfernt oder repariert diesen Claim nicht.

Nur der aktuelle LQ-351-Recontinuation-Claim liegt in seiner Freigabegrenze.
## Evidence vor frischer Reconciliation
Der finale Evidencename wird ausschließlich aus dem vollständigen SHA-256 der
Recontinuation-Finalization-ID abgeleitet.

Exakt gebundene Finalization-Evidence wird vor LQ-353 geprüft und steuert den
idempotenten Retry.

Sie muss owner-only, regulär, einfach verlinkt und vollständig kanonisch sein.

Beschädigte, widersprüchliche oder anders gebundene Evidence ist technisch
unavailable und wird nicht überschrieben.
## Frische LQ-353-Entscheidung
Ohne Finalization-Evidence muss der Finalizer LQ-353 unmittelbar mit derselben
historischen Reconciliation-Autorisierung neu ausführen.

Ein gespeicherter oder caller-gelieferter früherer Ausgang genügt nicht.

Die Ausgabe muss kanonisches JSON mit exakter Operation, Schema-Version und
einem geschlossenen LQ-353-Ausgang sein.

LQ-353 darf Docker nur bei offenem Cleanup- und Recontinuation-Claim ohne
Recontinuation-Evidence read-only beobachten.
## Finalisierbare Ausgänge
Diese frisch abgeleiteten Ausgänge dürfen Evidence-first finalisiert werden:

- `recontinuation_evidence_present` wird
  `recontinuation_evidence_confirmed`;
- `recontinuation_not_started` wird `recontinuation_attempt_finalized`;
- `application_network_removed` wird `later_prefix_finalized`;
- `runtime_removed_evidence_missing` wird
`runtime_removal_ready_for_cleanup_finalization`.
`not_found` bleibt neutral und erzeugt keinen Write.
`conflict` wird `investigation_required` ohne Evidence- oder Claimänderung.
Technische Nichtverfügbarkeit bleibt ohne Ergebnis und ohne Mutation.
## Getrennte Finalization-Evidence
Der Finalizer erzeugt weder LQ-351-Recontinuation-Evidence noch historische
LQ-339-Cleanup-Evidence nachträglich.

Sein Record bindet alle IDs und Hashes, beide Finalization-Evidenceketten,
`resume_from`, den frisch beobachteten LQ-353-Ausgang, den neutralen Ausgang,
Identitäten sowie UTC-Start und Abschluss.

Die Datei wird owner-only exklusiv geschrieben, synchronisiert, atomar final
angelegt und vollständig zurückgelesen.

Erst erfolgreiche Rücklesung erlaubt die Claimfreigabe.
## Exakte Recontinuation-Claimfreigabe
Der Claimname wird ausschließlich aus dem SHA-256 der Recontinuation-ID
abgeleitet.

Ein vorhandener Claim muss vollständig gegen dieselbe LQ-351-Bindung geprüft
werden, bevor genau dieser eine Claim entfernt wird.

Ist er bereits abwesend, ist die Freigabe idempotent abgeschlossen.
Suche, Alter, Präfix-, Label- oder Gruppenauswahl sind ausgeschlossen.
Cleanup-Claim, Ressourcen und historische Evidence bleiben unverändert.
## Unbekannte Claimfreigabe
Ist die Freigabe nach persistierter Finalization-Evidence technisch
mehrdeutig, bleibt die Evidence maßgeblich und der Ausgang unavailable.

Ein Retry validiert zuerst dieselbe Evidence und prüft anschließend nur den
exakten Recontinuation-Claim.

Vorhanden bedeutet erneuten einzelnen Freigabeversuch; abwesend bedeutet
bereits freigegeben.

Der Retry führt weder LQ-353 noch Docker erneut aus und schreibt keine zweite
Evidence.

Ein fremder oder beschädigter Claim wird niemals entfernt.
## Weitere Arbeit
Nach `later_prefix_finalized` benötigt jede weitere Fortsetzung eine neue ID
und neue Autorisierung, die den belegten Präfix explizit bindet.

Nach `runtime_removal_ready_for_cleanup_finalization` bleibt LQ-343 für die
separate Freigabe des ursprünglichen Cleanup-Claims zuständig.

Kein LQ-354-Ausgang startet diese Arbeit automatisch.
## Strikte Mutationsgrenze
Erlaubt sind nur neue Finalization-Evidence und spätere Freigabe des exakten
Recontinuation-Claims.

Stop, Start, Remove, Disconnect, Down, Kill, Prune, SQL, Docker-Events,
Volumeinhaltszugriff und Cleanup-Claimfreigabe sind verboten.

Das Datenvolume bleibt unverändert dem ursprünglichen Run zugeordnet.
## Neutrale Ausgabe
Der spätere Command liefert ausschließlich `not_found`, die vier definierten
Finalisierungsausgänge, `investigation_required` oder technisch unavailable.

Die Ausgabe enthält nur Schema-Version, Operation
`disposable_postgres_cleanup_recontinuation_finalization` und Ausgang.

Private IDs, Hashes, Pfade, Ressourcen und Fehlerdetails bleiben verborgen.
## Retention und Nichtwiederverwendung
Finalization-, Reconciliation-, Recontinuation-, Cleanup- und Run-IDs sowie
Claims, Autorisierungen und Evidence bleiben mindestens für Audit, Retry,
Fortsetzung und Cleanup-Finalisierung unterscheidbar.

Keine ID oder Evidence darf unter anderer Bindung wiederverwendet werden.

Claimfreigabe erlaubt keine Run-ID-Wiederverwendung oder Volumeübernahme. Eine
konkrete Retentionfrist oder Ablagestrategie wird nicht festgelegt.
## Nichtziele
LQ-354 implementiert keinen Finalizer, Entry Point, Test, Evidencewriter,
Claimrelease, weitere Continuation oder Cleanup-Finalisierung.

Es gibt keine Ressourcen- oder Volume-Löschung und keine Schema-, Tabellen-,
SQL-, Migration-, Port-, Domainmodell-, Signatur-, Compose-, CLI- oder
Production-Wiring-Entscheidung.

Bundle-Gates bleiben bei 42 Entry Points, 46 Operatormodulen, 27 Migrationen
und Head `20260819_0027`.
## Nächster Slice
LQ-355 sollte den evidence-first Recontinuation-Finalizer samt Fake-basierten
Tests für alle geschlossenen Ausgänge implementieren.

Weitere Fortsetzung und jede Volumenlöschung bleiben separate spätere Slices.
