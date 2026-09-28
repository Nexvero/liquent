# LQ-348 — Evidence-first Runtime Cleanup Continuation Finalization Contract

## Zweck
LQ-348 definiert die kontrollierte Finalisierung eines durch LQ-347
reconcilierten LQ-345-Continuation-Versuchs.

Sie persistiert getrennte private Evidence vor möglicher Freigabe des exakten
Continuation-Claims. Dieser Slice implementiert keinen Command oder Write.
## Separate Finalisierungsautorisierung
Continuation und Reconciliation gewähren kein Finalisierungsrecht.
Ein späterer Finalizer benötigt eine neue owner-only Autorisierung mit
stabiler, nicht wiederverwendbarer Continuation-Finalization-ID.
Sie muss mindestens geschlossen binden:

- Continuation-Finalization-, Continuation-Reconciliation-, Continuation-,
  Cleanup-Reconciliation- und Cleanup-ID;
- Run-ID und Phase `disposable_postgres`;
- Source-Commit, Application-Image-Digest und Compose-SHA-256;
- ursprüngliche Reconciliation-, Claim-Reconciliation- und Disposition-ID;
- alle vorgelagerten Cleanup-, Dispositions- und Evidencehashes;
- SHA-256 der LQ-341-, LQ-345- und LQ-347-Autorisierung;
- Scope exakt `runtime_only` und dasselbe `resume_from`;
- Operation exakt `finalize_disposable_postgres_cleanup_continuation`;
- neue getrennte Executor- und Autorisiereridentitäten;
- aktuelles UTC-Fenster von höchstens einer Stunde.

Caller liefern weder beobachteten Zustand noch Claimstatus oder Zielausgang.
## Vollständige historische Bindung
Der Finalizer validiert die gesamte Run-, Dispositions-, Cleanup-, LQ-341-,
Continuation- und LQ-347-Kette erneut.

Historische Autorisierungen werden nur an ihrem ursprünglich gültigen
Fenstermittelpunkt ausgewertet.

Die neue Finalisierungsautorisierung muss aktuell sein und verlängert keine
frühere Mutations- oder Reconciliation-Autorität.

Alle IDs, Hashes, `resume_from`, Ressourcenbindungen und der Projektname
müssen exakt dieselbe Kette beschreiben.
## Ursprünglicher Cleanup-Claim bleibt Voraussetzung
Der LQ-339-Cleanup-Claim muss vor jeder Finalisierung offen, kanonisch und
exakt an den ursprünglichen Run gebunden sein.

Seine Abwesenheit ist `investigation_required`, weil die Continuation nicht
isoliert von der ursprünglichen Cleanup-Lebensdauer abgeschlossen wird.

Ein beschädigter oder fremd gebundener Cleanup-Claim bleibt technisch
unavailable.

Der ursprüngliche Cleanup-Claim wird durch LQ-348 niemals freigegeben.
## Evidence vor frischer Reconciliation
Der finale Evidencename wird ausschließlich aus dem vollständigen SHA-256 der
Continuation-Finalization-ID abgeleitet.

Exakt gebundene Finalization-Evidence wird vor LQ-347 geprüft und steuert den
idempotenten Retry.

Sie muss owner-only, regulär, einfach verlinkt und vollständig kanonisch sein.

Beschädigte, widersprüchliche oder anders gebundene Evidence ist technisch
unavailable und wird nicht überschrieben.
## Frische LQ-347-Entscheidung
Ohne Finalization-Evidence muss der Finalizer LQ-347 unmittelbar mit derselben
historischen Reconciliation-Autorisierung neu ausführen.

Ein gespeicherter oder caller-gelieferter früherer Ausgang genügt nicht.

Die Ausgabe muss kanonisches JSON mit exakter Operation, Schema-Version und
einem geschlossenen LQ-347-Ausgang sein.

LQ-347 darf seinerseits Docker nur bei offenem Doppelclaim ohne
Continuation-Evidence read-only beobachten.
## Finalisierbare Ausgänge
Diese frisch abgeleiteten Ausgänge dürfen Evidence-first finalisiert werden:

- `continuation_evidence_present` wird `continuation_evidence_confirmed`;
- `continuation_not_started` wird `continuation_attempt_finalized`;
- `container_removed` und `application_network_removed` werden
  `later_prefix_finalized`;
- `runtime_removed_evidence_missing` wird
  `runtime_removal_ready_for_cleanup_finalization`.

`not_found` bleibt neutral und erzeugt keinen Write.

`conflict` wird `investigation_required` ohne Evidence- oder Claimänderung.

Technische Nichtverfügbarkeit bleibt ohne Ergebnis und ohne Mutation.
## Bedeutung der Finalisierung
`continuation_attempt_finalized` bestätigt nur, dass der aktuelle Versuch
keinen beobachtbaren Fortschritt hinterlassen hat.

`later_prefix_finalized` hält den exakt beobachteten späteren Präfix fest. Es
erteilt kein Recht, die verbleibenden Schritte auszuführen.

`runtime_removal_ready_for_cleanup_finalization` bestätigt nur den
beobachteten Endpräfix bei erhaltenem rungebundenem Datenvolume.

`continuation_evidence_confirmed` bestätigt die bereits vollständige
LQ-345-Evidence, ohne sie umzuschreiben.
## Getrennte Finalization-Evidence
Der Finalizer erzeugt weder LQ-345-Continuation-Evidence noch historische
LQ-339-Cleanup-Evidence nachträglich.

Sein eigener Record bindet alle IDs und Hashes, `resume_from`, den frisch
beobachteten LQ-347-Ausgang, den neutralen Finalisierungsausgang, getrennte
Identitäten sowie UTC-Start und Abschluss.

Die Datei wird owner-only per exklusiver Temporäranlage geschrieben,
synchronisiert, atomar final angelegt und vollständig zurückgelesen.

Erst erfolgreiche Rücklesung erlaubt die Claimfreigabe.
## Exakte Continuation-Claimfreigabe
Der Claimname wird nur aus dem SHA-256 der Continuation-ID abgeleitet.

Ein vorhandener Claim muss vollständig gegen dieselbe LQ-345-Bindung geprüft
werden, bevor genau dieser eine Claim entfernt wird.

Ist er bereits abwesend, ist die Freigabe idempotent abgeschlossen.

Suche, Alter, Präfix-, Label- oder Gruppenauswahl sind ausgeschlossen.

Cleanup-Claim, Ressourcen und historische Evidence bleiben unverändert.
## Unbekannte Claimfreigabe
Ist die Freigabe nach persistierter Finalization-Evidence technisch
mehrdeutig, bleibt die Evidence maßgeblich und der Ausgang unavailable.

Ein Retry validiert zuerst dieselbe Evidence und prüft anschließend nur den
exakten Continuation-Claim.

Vorhanden bedeutet einen erneuten einzelnen Freigabeversuch; abwesend bedeutet
bereits freigegeben.

Der Retry führt weder LQ-347 noch Docker erneut aus und schreibt keine zweite
Evidence.

Ein fremder oder beschädigter Claim wird niemals entfernt.
## Weitere Arbeit nach Finalisierung
Nach `later_prefix_finalized` benötigt jede Fortsetzung eine neue
Continuation-ID und neue Autorisierung, die den belegten späteren Präfix
explizit bindet.

Nach `runtime_removal_ready_for_cleanup_finalization` bleibt LQ-343 für die
separate Finalisierung des ursprünglichen Cleanup-Claims zuständig.

Kein LQ-348-Ausgang startet diese Arbeit automatisch.
## Strikte Mutationsgrenze
Erlaubt sind nur die neue Finalization-Evidence und die spätere Freigabe des
exakten Continuation-Claims.

Stop, Start, Remove, Disconnect, Down, Kill, Prune, SQL, Docker-Events,
Volumeinhaltszugriff und Cleanup-Claimfreigabe sind verboten.

Das Datenvolume bleibt unverändert dem ursprünglichen Run zugeordnet.
## Neutrale Ausgabe
Der spätere Command liefert ausschließlich `not_found`, die vier definierten
Finalisierungsausgänge, `investigation_required` oder technisch unavailable
ohne Ergebnisobjekt.

Die Ausgabe enthält nur Schema-Version, Operation
`disposable_postgres_cleanup_continuation_finalization` und Ausgang.

Private IDs, Hashes, Pfade, Ressourcen und Fehlerdetails bleiben verborgen.
## Retention und Nichtwiederverwendung

Finalization-, Reconciliation-, Continuation-, Cleanup- und Run-IDs sowie
Claims, Autorisierungen und Evidence bleiben mindestens für Audit, Retry,
Fortsetzung und Cleanup-Finalisierung unterscheidbar.

Keine ID oder Evidence darf unter anderer Bindung wiederverwendet werden.
Claimfreigabe erlaubt keine Run-ID-Wiederverwendung oder Volumeübernahme.

Dieser Vertrag bestimmt keine konkrete Retentionfrist oder Ablagestrategie.
## Nichtziele

LQ-348 implementiert keinen Finalizer, Entry Point, Test, Evidencewriter,
Claimrelease, erneute Continuation oder Cleanup-Finalisierung.

Es gibt keine Ressourcen- oder Volume-Löschung und keine Schema-, Tabellen-,
SQL-, Migration-, Port-, Domainmodell-, Signatur-, Compose-, CLI- oder
Production-Wiring-Entscheidung.

Bundle-Gates bleiben bei 39 Entry Points, 43 Operatormodulen, 27 Migrationen
und Head `20260819_0027`.
## Nächster Slice

LQ-349 sollte den evidence-first Continuation-Finalizer samt Fake-basierten
Tests für alle geschlossenen Ausgänge implementieren.

Eine erneute Fortsetzung ab belegtem späterem Präfix und jede Volumenlöschung
bleiben separate spätere Slices.
