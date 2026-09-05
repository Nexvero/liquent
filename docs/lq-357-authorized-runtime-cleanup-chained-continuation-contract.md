# LQ-357 — Authorized Runtime Cleanup Chained Continuation Contract

## Zweck
LQ-357 definiert einen neuen Cleanup-Versuch nach einem nichtterminalen,
durch LQ-355 evidence-first finalisierten Recontinuation-Versuch.

Die chained Continuation bindet LQ-355 als jüngsten Autoritätsanker. Dieser
Slice implementiert keinen Operator, Claim, Writer oder Dockeraufruf.
## Zulässige LQ-355-Evidence
Nur kanonische LQ-355-Finalization-Evidence mit einem dieser Ausgänge darf
eine chained Continuation begründen:
- `recontinuation_attempt_finalized`;
- `later_prefix_finalized`.

`recontinuation_evidence_confirmed` und
`runtime_removal_ready_for_cleanup_finalization` sind terminal und werden
ausschließlich an LQ-343 übergeben.
`not_found`, `investigation_required` oder technisch unavailable erteilen
keine neue Autorität.
## Autoritativer Startpräfix
Caller liefern keinen Startzustand.

Bei `recontinuation_attempt_finalized` ist `resume_from` exakt der in der
LQ-355-Kette gebundene LQ-351-Startpräfix.

Er ist `container_removed` oder `application_network_removed`.

Bei `later_prefix_finalized` ist `resume_from` zwingend
`application_network_removed`.

Jede Abweichung zwischen Evidence, beobachtetem Zustand und historischer
Autorisierung bleibt technisch unavailable.
## Neue chained-Continuation-Autorisierung
Der spätere Operator benötigt eine neue owner-only Autorisierung mit stabiler,
nicht wiederverwendbarer Chained-Continuation-ID.
Sie muss mindestens geschlossen binden:

- Chained-Continuation-, Recontinuation-Finalization-,
  Recontinuation-Reconciliation- und Recontinuation-ID;
- Continuation-Finalization-, alte Continuation-, Cleanup-Reconciliation-,
  Cleanup- und Run-ID;
- Phase `disposable_postgres`, Source-Commit, Image-Digest und Compose-Hash;
- ursprüngliche Reconciliation-, Claim-Reconciliation- und Disposition-ID;
- sämtliche vorgelagerten Evidence- und Autorisierungshashes;
- SHA-256 der LQ-341-, LQ-345-, LQ-347-, LQ-349-, LQ-351-, LQ-353- und
  LQ-355-Autorisierung;
- SHA-256 der exakten LQ-349- und LQ-355-Finalization-Evidence;
- den autoritativ abgeleiteten `resume_from`;
- Scope exakt `runtime_only`;
- Operation exakt `continue_disposable_postgres_cleanup_from_finalized_recontinuation`;
- neue getrennte Executor- und Autorisiereridentitäten;
- aktuelles UTC-Fenster von höchstens einer Stunde.

Caller liefern weder Ressourcen, Restbudget noch Dockerargumente.
## Vollständige historische Bindung
Der Operator validiert Run-, Dispositions-, Cleanup-, Continuation-, LQ-349-,
LQ-351-, LQ-353- und LQ-355-Kette erneut.

Historische Zeitfenster werden ausschließlich an ihrem ursprünglich gültigen
Mittelpunkt ausgewertet.

Die neue Autorisierung muss aktuell sein und verlängert keinen früheren
Versuch oder dessen Claimautorität.

Alle IDs, Hashes, Ressourcenbindungen und der Projektname müssen dieselbe
unveränderte Kette beschreiben.
## Claim-Voraussetzungen
Der ursprüngliche LQ-339-Cleanup-Claim muss offen, kanonisch und exakt
gebunden bleiben.

Der alte LQ-345-Continuation-Claim und der abgeschlossene
LQ-351-Recontinuation-Claim müssen exakt abwesend sein.

Ein vorhandener historischer Claim ist technisch unavailable und darf weder
ersetzt noch freigegeben werden.

Der neue Claimname wird ausschließlich aus dem vollständigen SHA-256 der
Chained-Continuation-ID abgeleitet.
## Frische Zustandsbestätigung
Unmittelbar vor neuer Claimanlage muss der Operator LQ-341 mit der historischen
Cleanup-Reconciliation-Autorisierung frisch ausführen.

Nur ein Ausgang exakt gleich dem autoritativ abgeleiteten `resume_from` darf
die Mutation erreichen.

Ein früherer oder späterer Präfix, `runtime_intact`, vollständige
Runtimeentfernung, Final-Evidence oder Conflict ergibt `rejected` ohne neuen
Claim und ohne Ressourceneffekt.

Technisch nicht verfügbare Beobachtung bleibt unavailable.
## Minimale Restbudgets
Für `resume_from=container_removed` umfasst das Budget ausschließlich:

1. Application-Netz einmal entfernen und Abwesenheit bestätigen;
2. Data-Netz einmal entfernen und Abwesenheit bestätigen;
3. das exakte Datenvolume read-only als erhalten bestätigen.

Für `resume_from=application_network_removed` beginnt es bei Schritt zwei.
Container-Stop, Container-Remove und abgeschlossene Network-Removes werden
niemals wiederholt.

Es gibt keinen freien Offset oder caller-gelieferten Endzustand.
## Evidence-first Claim
Der Chained-Continuation-Claim wird erst nach exakter frischer
Zustandsübereinstimmung owner-only exklusiv angelegt und synchronisiert.

Er bindet die vollständige Kette, beide Finalization-Evidencehashes,
`resume_from`, Restbudget, exakte Ressourcen, Identitäten und UTC-Startzeit.

Ein vorhandener oder technisch unklarer neuer Claim stoppt vor Docker.
Er wird nicht überschrieben oder aufgrund von Alter freigegeben.
Der ursprüngliche Cleanup-Claim bleibt während des Versuchs offen.
## Exakte Mutation
Jedes erlaubte Netzwerk wird einzeln mit intern abgeleitetem Namen entfernt.

Nach jedem Remove muss eine exakte read-only Namensliste vollständige
Abwesenheit bestätigen, bevor der nächste Schritt beginnt.

Nach dem letzten Remove muss Volume-Inspect das unveränderte rungebundene
Datenvolume bestätigen.

Compose-Down, Stop, Start, Kill, Force, Disconnect, Prune, `--volumes`,
Wildcard-, Prefix-, Label- und Gruppencleanup sind ausgeschlossen.
## Unknown Outcome
Ab dem ersten Remove beendet Nonzero, stderr, Timeout, Truncation, Hard Kill,
verlorene Bestätigung oder widersprüchliche Nachbeobachtung den Ablauf sofort.

Cleanup- und Chained-Continuation-Claim bleiben offen.
Es gibt keinen Blind-Retry, Ersatzbefehl, Folgeschritt oder heuristische
Erfolgsableitung.

Eine spätere read-only Reconciliation des neuen Claims ist erforderlich.
## Chained-Continuation-Evidence
Nach bestätigter Runtimeentfernung und Volume-Erhalt entsteht getrennte
private Evidence.

Sie bindet alle IDs und Hashes, beide Finalization-Evidencegenerationen,
autorisierten Startpräfix, Restbudget, Ressourcen, Identitäten sowie UTC-Start
und Abschluss.

Ihr Ausgang lautet `runtime_removed_pending_cleanup_finalization`.
Sie ist weder LQ-339-Cleanup- noch frühere Continuation-Evidence.

Erst atomare Anlage, Verzeichnissynchronisation und vollständige Rücklesung
erlauben die Freigabe des exakten neuen Claims.

Ein Evidence-Retry wiederholt nur die Claimfreigabe und führt kein Docker aus.
## Harte Grenzen
Der Operator gibt weder Cleanup- noch historische Claims frei und verändert
keine bestehende Evidence.
Er entfernt kein Volume oder Image, führt kein SQL aus und liest keine
Docker-Events, Logs oder Volumeinhalte.

Er erzeugt keine Cleanup- oder Finalization-Evidence und startet LQ-343 nicht
automatisch.
## Neutrale Ausgabe
Der spätere Command liefert ausschließlich:
- `runtime_removed_pending_cleanup_finalization`;
- `rejected` bei lesbarem Zustandsmismatch vor Mutation;
- technisch unavailable ohne Ergebnisobjekt.

Die Ausgabe enthält nur Schema-Version, Operation
`disposable_postgres_runtime_cleanup_chained_continuation` und Ausgang.

Private IDs, Hashes, Ressourcen, Pfade und Zeiten bleiben verborgen.
## Retention und Nichtwiederverwendung
Chained-Continuation-, Recontinuation-Finalization-, Cleanup- und Run-IDs
sowie Claims, Autorisierungen und Evidence bleiben mindestens für Audit,
Retry, Reconciliation und Cleanup-Finalisierung unterscheidbar.

Keine ID oder Evidence darf unter anderer Bindung wiederverwendet werden.

Claimfreigabe erlaubt keine Run-ID-Wiederverwendung oder Volumeübernahme. Eine
konkrete Retentionfrist oder Ablagestrategie wird nicht festgelegt.
## Nichtziele
LQ-357 implementiert keinen Operator, Entry Point, Test, Claim,
Evidencewriter, Reconciliationoperator oder Cleanup-Finalizer.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Domainmodell-,
Signatur-, Compose-, CLI- oder Production-Wiring-Entscheidung.

Bundle-Gates bleiben bei 43 Entry Points, 47 Operatormodulen, 27 Migrationen
und Head `20260819_0027`.
## Nächster Slice

LQ-358 sollte den owner-kontrollierten chained-Continuation-Operator mit
beiden minimalen Restbudgets und Fake-basierten Tests implementieren.

Reconciliation unbekannter Ausgänge und jede Volumenlöschung bleiben separate
spätere Slices.
