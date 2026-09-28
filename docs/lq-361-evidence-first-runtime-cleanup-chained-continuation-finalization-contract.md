# LQ-361 — Evidence-first Runtime Cleanup Chained Continuation Finalization Contract
## Zweck
LQ-361 definiert die kontrollierte Finalisierung eines durch LQ-360
reconcilierten LQ-358-Chained-Continuation-Versuchs.
Sie persistiert getrennte private Evidence vor möglicher Freigabe des exakten
aktuellen Claims. Dieser Slice implementiert keinen Command oder Write.
## Separate Finalisierungsautorisierung
Chained Continuation und Reconciliation gewähren kein Finalisierungsrecht.
Ein späterer Finalizer benötigt eine neue owner-only Autorisierung mit
stabiler, nicht wiederverwendbarer Chained-Finalization-ID.
Sie muss mindestens geschlossen binden:
- Chained-Finalization-, Chained-Reconciliation- und
  Chained-Continuation-ID;
- Recontinuation-Finalization-, Recontinuation-, Continuation-, Cleanup- und
  Run-Kette;
- Phase `disposable_postgres`, Source-Commit, Image-Digest und Compose-Hash;
- ursprüngliche Reconciliation-, Claim-Reconciliation- und Disposition-ID;
- sämtliche vorgelagerten Evidence- und Autorisierungshashes;
- SHA-256 der LQ-341-, LQ-345-, LQ-347-, LQ-349-, LQ-351-, LQ-353-,
  LQ-355-, LQ-358- und LQ-360-Autorisierung;
- SHA-256 der exakten LQ-349- und LQ-355-Finalization-Evidence;
- historischen `previous_resume_from` und effektiven `resume_from`;
- Scope exakt `runtime_only`;
- Operation exakt `finalize_disposable_postgres_cleanup_chained_continuation`;
- neue getrennte Executor- und Autorisiereridentitäten;
- aktuelles UTC-Fenster von höchstens einer Stunde.
Caller liefern weder beobachteten Zustand noch Claimstatus oder Zielausgang.
## Vollständige historische Bindung
Der Finalizer validiert die gesamte Run-, Dispositions-, Cleanup-,
Continuation-, Recontinuation-, LQ-355-, LQ-358- und LQ-360-Kette erneut.
Historische Autorisierungen werden nur an ihrem ursprünglich gültigen
Fenstermittelpunkt ausgewertet.
Die neue Finalisierungsautorisierung muss aktuell sein und verlängert keine
frühere Mutations- oder Reconciliation-Autorität.
Alle IDs, Hashes, beide Startpräfixe, Ressourcenbindungen und Projektname
müssen exakt dieselbe unveränderte Kette beschreiben.
## LQ-355-Evidence bleibt Anker
Die Recontinuation-Finalization-Evidence muss weiterhin owner-only, kanonisch
und exakt gebunden sein.
Sie muss einen nichtterminalen Ausgang enthalten, aus dem LQ-358 den effektiven
Startpräfix eindeutig abgeleitet hat.
Sie wird weder ersetzt noch durch neue Finalization-Evidence umgedeutet.
Eine Hash- oder Bindungsabweichung bleibt technisch unavailable.
## Claim-Gates
Der LQ-339-Cleanup-Claim muss offen, kanonisch und exakt an den ursprünglichen
Run gebunden sein.
Seine Abwesenheit ist `investigation_required`; malformed Bindung bleibt
technisch unavailable.
Alter LQ-345-Continuation-Claim und LQ-351-Recontinuation-Claim müssen exakt
abwesend sein.
Ein vorhandener historischer Claim bleibt unavailable und wird nicht entfernt.
Nur der aktuelle LQ-358-Claim liegt in der Freigabegrenze.
## Evidence vor frischer Reconciliation
Der finale Evidencename wird ausschließlich aus dem vollständigen SHA-256 der
Chained-Finalization-ID abgeleitet.
Exakt gebundene Finalization-Evidence wird vor LQ-360 geprüft und steuert den
idempotenten Retry.
Sie muss owner-only, regulär, einfach verlinkt und vollständig kanonisch sein.
Beschädigte, widersprüchliche oder anders gebundene Evidence ist technisch
unavailable und wird nicht überschrieben.
## Frische LQ-360-Entscheidung
Ohne Finalization-Evidence muss der Finalizer LQ-360 unmittelbar mit derselben
historischen Reconciliation-Autorisierung neu ausführen.
Ein gespeicherter oder caller-gelieferter früherer Ausgang genügt nicht.
Die Ausgabe muss kanonisches JSON mit exakter Operation, Schema-Version und
einem geschlossenen LQ-360-Ausgang sein.
LQ-360 darf Docker nur bei offenem Cleanup- und aktuellem Claim ohne Evidence
read-only beobachten.
## Finalisierbare Ausgänge
Diese frisch abgeleiteten Ausgänge dürfen Evidence-first finalisiert werden:
- `chained_continuation_evidence_present` wird
  `chained_continuation_evidence_confirmed`;
- `chained_continuation_not_started` wird
  `chained_continuation_attempt_finalized`;
- `application_network_removed` wird `later_prefix_finalized`;
- `runtime_removed_evidence_missing` wird
  `runtime_removal_ready_for_cleanup_finalization`.
`not_found` bleibt neutral und erzeugt keinen Write.
`conflict` wird `investigation_required` ohne Evidence- oder Claimänderung.
Technische Nichtverfügbarkeit bleibt ohne Ergebnis und ohne Mutation.
## Bedeutung der Ausgänge
`chained_continuation_attempt_finalized` bestätigt nur fehlenden beobachtbaren
Fortschritt des aktuellen Versuchs.
`later_prefix_finalized` hält exakt `application_network_removed` fest und
erteilt kein weiteres Fortsetzungsrecht.
`runtime_removal_ready_for_cleanup_finalization` bestätigt vollständige
Runtimeentfernung bei erhaltenem rungebundenem Datenvolume.
`chained_continuation_evidence_confirmed` bestätigt vorhandene LQ-358-Evidence
ohne Umschreiben.
## Getrennte Finalization-Evidence
Der Finalizer erzeugt weder LQ-358-Evidence noch historische
LQ-339-Cleanup-Evidence nachträglich.
Sein Record bindet alle IDs und Hashes, beide Startpräfixe, alle
Finalization-Evidencegenerationen, den frisch beobachteten LQ-360-Ausgang,
neutralen Ausgang, Identitäten sowie UTC-Start und Abschluss.
Die Datei wird owner-only exklusiv geschrieben, synchronisiert, atomar final
angelegt und vollständig zurückgelesen.

Erst erfolgreiche Rücklesung erlaubt die Claimfreigabe.

## Exakte aktuelle Claimfreigabe

Der Claimname wird ausschließlich aus dem SHA-256 der
Chained-Continuation-ID abgeleitet.

Ein vorhandener Claim muss vollständig gegen dieselbe LQ-358-Bindung geprüft
werden, bevor genau dieser eine Claim entfernt wird.

Ist er bereits abwesend, ist die Freigabe idempotent abgeschlossen.

Suche, Alter, Präfix-, Label- oder Gruppenauswahl sind ausgeschlossen.

Cleanup-Claim, Ressourcen und historische Evidence bleiben unverändert.

## Unbekannte Claimfreigabe

Ist die Freigabe nach persistierter Finalization-Evidence technisch
mehrdeutig, bleibt die Evidence maßgeblich und der Ausgang unavailable.

Ein Retry validiert zuerst dieselbe Evidence und prüft anschließend nur den
exakten aktuellen Claim.

Vorhanden bedeutet erneuten einzelnen Freigabeversuch; abwesend bedeutet
bereits freigegeben.

Der Retry führt weder LQ-360 noch Docker erneut aus und schreibt keine zweite
Evidence.

Ein fremder oder beschädigter Claim wird niemals entfernt.

## Weitere Arbeit

Nach `chained_continuation_attempt_finalized` oder `later_prefix_finalized`
benötigt jeder weitere Versuch eine neue ID und Bindung an diese jüngste
Finalization-Evidence.

Nach beiden terminalen Ausgängen bleibt LQ-343 für die separate Freigabe des
ursprünglichen Cleanup-Claims zuständig.

Kein LQ-361-Ausgang startet Folgearbeit automatisch.

## Strikte Mutationsgrenze

Erlaubt sind nur neue Finalization-Evidence und spätere Freigabe des exakten
aktuellen Claims.

Stop, Start, Remove, Disconnect, Down, Kill, Prune, SQL, Docker-Events,
Volumeinhaltszugriff und Cleanup-Claimfreigabe sind verboten.

Das Datenvolume bleibt unverändert dem ursprünglichen Run zugeordnet.

## Neutrale Ausgabe

Der spätere Command liefert ausschließlich `not_found`, die vier definierten
Finalisierungsausgänge, `investigation_required` oder technisch unavailable.

Die Ausgabe enthält nur Schema-Version, Operation
`disposable_postgres_cleanup_chained_continuation_finalization` und Ausgang.

Private IDs, Hashes, Pfade, Ressourcen und Fehlerdetails bleiben verborgen.

## Retention und Nichtwiederverwendung

Finalization-, Reconciliation-, Chained-Continuation-, Cleanup- und Run-IDs
sowie Claims, Autorisierungen und Evidence bleiben mindestens für Audit,
Retry, Fortsetzung und Cleanup-Finalisierung unterscheidbar.

Keine ID oder Evidence darf unter anderer Bindung wiederverwendet werden.

Claimfreigabe erlaubt keine Run-ID-Wiederverwendung oder Volumeübernahme. Eine
konkrete Retentionfrist oder Ablagestrategie wird nicht festgelegt.

## Nichtziele

LQ-361 implementiert keinen Finalizer, Entry Point, Test, Evidencewriter,
Claimrelease, weitere Continuation oder Cleanup-Finalisierung.

Es gibt keine Ressourcen- oder Volume-Löschung und keine Schema-, Tabellen-,
SQL-, Migration-, Port-, Domainmodell-, Signatur-, Compose-, CLI- oder
Production-Wiring-Entscheidung.

Bundle-Gates bleiben bei 45 Entry Points, 49 Operatormodulen, 27 Migrationen
und Head `20260819_0027`.

## Nächster Slice

LQ-362 sollte den evidence-first Chained-Continuation-Finalizer samt
Fake-basierten Tests für alle geschlossenen Ausgänge implementieren.

Weitere Fortsetzung und jede Volumenlöschung bleiben separate spätere Slices.
