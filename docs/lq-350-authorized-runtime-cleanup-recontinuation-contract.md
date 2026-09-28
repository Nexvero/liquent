# LQ-350 — Authorized Runtime Cleanup Recontinuation Contract

## Zweck
LQ-350 definiert eine neue, streng autorisierte Cleanup-Continuation ab einem
durch LQ-349 belegten späteren Präfix.

Sie ist ein neuer Versuch mit eigener Autorität und kein Retry des
abgeschlossenen LQ-345-Versuchs. Dieser Slice implementiert keinen Operator.
## Zulässige Ausgangsevidence
Nur kanonische LQ-349-Finalization-Evidence mit Ausgang
`later_prefix_finalized` darf eine Recontinuation begründen.

Ihr `observed_state` ist exakt einer von:

- `container_removed`;
- `application_network_removed`.

`continuation_attempt_finalized`, `continuation_evidence_confirmed` und
`runtime_removal_ready_for_cleanup_finalization` erteilen kein Recht für
diesen Pfad.

Ein Dateiname, ein früherer Inspector-Ausgang oder caller-gelieferter Zustand
genügt nicht.
## Neue Recontinuation-Autorisierung
Der spätere Operator benötigt eine neue owner-only Autorisierung mit stabiler,
nicht wiederverwendbarer Recontinuation-ID.

Sie muss mindestens geschlossen binden:

- Recontinuation-, Continuation-Finalization-, Continuation-Reconciliation-,
  alte Continuation-, Cleanup-Reconciliation- und Cleanup-ID;
- Run-ID und Phase `disposable_postgres`;
- Source-Commit, Application-Image-Digest und Compose-SHA-256;
- ursprüngliche Reconciliation-, Claim-Reconciliation- und Disposition-ID;
- sämtliche vorgelagerten Evidence- und Autorisierungshashes;
- SHA-256 der LQ-341-, LQ-345-, LQ-347- und LQ-349-Autorisierung;
- SHA-256 der exakten LQ-349-Finalization-Evidence;
- `resume_from` exakt gleich deren `observed_state`;
- Scope exakt `runtime_only`;
- Operation exakt `continue_disposable_postgres_cleanup_from_finalized_prefix`;
- neue getrennte Executor- und Autorisiereridentitäten;
- aktuelles UTC-Fenster von höchstens einer Stunde.

Caller liefern weder Ressourcen, Fortschritt noch Dockerargumente.
## Vollständige historische Bindung
Der Operator validiert Run-, Dispositions-, Cleanup-, LQ-341-, LQ-345-,
LQ-347- und LQ-349-Autorisierung erneut.

Historische Zeitfenster werden ausschließlich an ihrem ursprünglich gültigen
Mittelpunkt ausgewertet.

Die neue Autorisierung muss aktuell sein und verlängert keinen früheren
Versuch oder dessen Claimautorität.

Alle IDs, Hashes, Ressourcenbindungen, `resume_from` und der Projektname
müssen dieselbe unveränderte Kette beschreiben.
## Claim-Voraussetzungen
Der ursprüngliche LQ-339-Cleanup-Claim muss offen, kanonisch und exakt
gebunden bleiben.

Der alte LQ-345-Continuation-Claim muss nach LQ-349 exakt abwesend sein.

Ein noch vorhandener alter Claim ist technisch unavailable und darf weder
durch Recontinuation ersetzt noch freigegeben werden.

Der neue Claimname wird ausschließlich aus dem vollständigen SHA-256 der
neuen Recontinuation-ID abgeleitet.

Claimnamen werden niemals gesucht, gruppiert oder nach Alter ausgewählt.
## Frische Zustandsbestätigung
Unmittelbar vor Anlage des neuen Claims muss der Operator LQ-341 mit der
historischen Cleanup-Reconciliation-Autorisierung frisch ausführen.

Nur ein Ausgang exakt gleich dem durch LQ-349 belegten `resume_from` darf die
Mutation erreichen.

Ein früherer Präfix, späterer Präfix, `runtime_intact`, vollständige
Runtimeentfernung, Final-Evidence oder Conflict ergibt `rejected` ohne neuen
Claim und ohne Ressourceneffekt.

Technisch nicht verfügbare Beobachtung bleibt unavailable.
## Minimales Restbudget
Für `resume_from=container_removed` umfasst das Budget ausschließlich:

1. Application-Netz einmal entfernen und Abwesenheit bestätigen;
2. Data-Netz einmal entfernen und Abwesenheit bestätigen;
3. das exakte Datenvolume read-only als erhalten bestätigen.

Für `resume_from=application_network_removed` beginnt es bei Schritt zwei.

Container-Stop, Container-Remove und bereits abgeschlossene Network-Removes
werden niemals wiederholt.

Das Budget enthält keinen frei wählbaren Offset oder gewünschten Endzustand.
## Neuer Evidence-first Claim
Der Recontinuation-Claim wird erst nach exakter frischer
Zustandsübereinstimmung owner-only exklusiv angelegt und synchronisiert.

Er bindet die vollständige historische Kette, LQ-349-Evidencehash,
`resume_from`, Restbudget, exakte Ressourcen, Identitäten und UTC-Startzeit.

Ein vorhandener oder technisch unklarer neuer Claim stoppt vor Docker.

Er wird nicht überschrieben oder aufgrund von Alter freigegeben.

Der ursprüngliche Cleanup-Claim bleibt während des gesamten Versuchs offen.
## Exakte Mutation
Jede erlaubte Ressource wird einzeln mit intern abgeleitetem Namen entfernt.

Nach jedem Remove muss eine exakte read-only Namensliste vollständige
Abwesenheit bestätigen, bevor der nächste Schritt beginnt.

Nach dem letzten Network-Remove muss Volume-Inspect das unveränderte,
rungebundene Datenvolume bestätigen.

Es gibt kein Compose-Down, Stop, Start, Kill, Force, Disconnect, Prune,
`--volumes`, Wildcard-, Prefix-, Label- oder Gruppencleanup.
## Unknown Outcome
Ab dem ersten Remove beendet Nonzero, stderr, Timeout, Truncation, Hard Kill,
verlorene Bestätigung oder widersprüchliche Nachbeobachtung den Ablauf sofort.

Cleanup- und Recontinuation-Claim bleiben offen.

Es gibt keinen Blind-Retry, Ersatzbefehl, Folgeschritt oder heuristische
Erfolgsableitung.

Eine spätere read-only Reconciliation des neuen Claims ist erforderlich.
## Recontinuation-Evidence
Nach bestätigter Runtimeentfernung und Volume-Erhalt entsteht getrennte
private Recontinuation-Evidence.

Sie bindet alle IDs und Hashes, LQ-349-Evidence, autorisierten Startpräfix,
Restbudget, Ressourcen, Identitäten sowie UTC-Start und Abschluss.

Ihr Ausgang lautet `runtime_removed_pending_cleanup_finalization`.

Sie ist weder nachträgliche LQ-339-Cleanup-Evidence noch LQ-345-Evidence.

Erst atomare Anlage, Verzeichnissynchronisation und vollständige Rücklesung
erlauben die Freigabe des exakten Recontinuation-Claims.

Ein Evidence-Retry wiederholt nur diese Claimfreigabe und führt kein Docker
aus.
## Harte Grenzen
Der Operator gibt weder den ursprünglichen Cleanup-Claim noch historische
Claims frei und verändert keine bestehende Evidence.

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
`disposable_postgres_runtime_cleanup_recontinuation` und Ausgang.

Private IDs, Hashes, Ressourcen, Pfade und Zeiten bleiben verborgen.
## Retention und Nichtwiederverwendung

Recontinuation-, Finalization-, Continuation-, Cleanup- und Run-IDs sowie
Claims, Autorisierungen und Evidence bleiben mindestens für Audit, Retry,
Reconciliation und Cleanup-Finalisierung unterscheidbar.

Keine ID oder Evidence darf unter anderer Bindung wiederverwendet werden.

Claimfreigabe erlaubt keine Run-ID-Wiederverwendung oder Volumeübernahme.
Eine konkrete Retentionfrist oder Ablagestrategie wird nicht festgelegt.
## Nichtziele

LQ-350 implementiert keinen Operator, Entry Point, Test, Claim,
Evidencewriter, Reconciliationoperator oder Cleanup-Finalizer.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Domainmodell-,
Signatur-, Compose-, CLI- oder Production-Wiring-Entscheidung.

Bundle-Gates bleiben bei 40 Entry Points, 44 Operatormodulen, 27 Migrationen
und Head `20260819_0027`.
## Nächster Slice

LQ-351 sollte den owner-kontrollierten Recontinuation-Operator mit beiden
minimalen Restbudgets und Fake-basierten Tests implementieren.

Reconciliation unbekannter Recontinuation-Ausgänge und jede Volumenlöschung
bleiben separate spätere Slices.
