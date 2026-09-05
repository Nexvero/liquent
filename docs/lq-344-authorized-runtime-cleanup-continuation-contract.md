# LQ-344 — Authorized Runtime Cleanup Continuation Contract

## Zweck

LQ-344 definiert die streng autorisierte Fortsetzung eines eindeutig
beobachteten LQ-339-Teilcleanup.

Er erlaubt nur ausstehende Runtime-Schritte. Das Volume bleibt ausgeschlossen.
Dieser Slice implementiert keinen Command, Claim, Writer oder Dockeraufruf.

## Neue Continuation-Autorisierung

Cleanup- und Cleanup-Reconciliation-Autorisierung gewähren kein
Fortsetzungsrecht.

Eine spätere Fortsetzung benötigt eine neue owner-only Autorisierung mit
stabiler, nicht wiederverwendbarer Cleanup-Continuation-ID.

Sie muss mindestens geschlossen binden:

- Continuation-, Cleanup-Reconciliation- und Cleanup-ID;
- Run-ID und Phase `disposable_postgres`;
- Source-Commit, Application-Image-Digest und Compose-SHA-256;
- ursprüngliche Reconciliation-, Claim-Reconciliation- und Disposition-ID;
- alle Cleanup-, Dispositions- und Evidencehashes;
- SHA-256 der vollständigen LQ-341-Reconciliation-Autorisierung;
- Operation exakt `continue_disposable_postgres_runtime_cleanup`;
- Scope exakt `runtime_only`;
- einen geschlossenen erwarteten Ausgangszustand;
- neue getrennte Executor- und Autorisiereridentitäten;
- aktuelles UTC-Fenster von höchstens einer Stunde.

Caller liefern weder Ressourcen, Zustand noch Dockerargumente.

## Drei geschlossene Ausgangszustände

`resume_from` ist exakt einer von:

- `container_stopped`;
- `container_removed`;
- `application_network_removed`.

Die Autorisierung gilt nur dafür, ohne Erweiterung oder Herabstufung.

Ein allgemeines `continue=true`, freies Startoffset oder gewünschter
Endzustand ist unzulässig.

## Vollständige Neuprüfung

Der spätere Operator validiert die gesamte historische Kette erneut.

Die gebundene LQ-341-Autorisierung wird bytegenau geprüft und nur an ihrem
historischen gültigen Mittelpunkt verwendet. Die neue
Continuation-Autorisierung muss aktuell sein.

Der LQ-339-Claim muss offen und kanonisch an dieselbe Kette gebunden sein.

Unmittelbar vor dem Continuation-Claim wird LQ-341 mit denselben autoritativen
Inputs erneut ausgeführt.

Nur wenn der frisch beobachtete Ausgang exakt `resume_from` entspricht, darf
die Mutation beginnen. Jeder andere lesbare Ausgang ergibt `rejected` ohne
Claim oder Ressourceneffekt.

## Minimale Restbudgets

Für `container_stopped` umfasst das Budget ausschließlich:

1. den bereits gestoppten Container einmal ohne Force und Volumeoption
   entfernen und Abwesenheit bestätigen;
2. Application-Netz einmal entfernen und Abwesenheit bestätigen;
3. Data-Netz einmal entfernen und Abwesenheit bestätigen;
4. das exakte Datenvolume read-only als erhalten bestätigen.

Für `container_removed` beginnt das Budget bei Schritt zwei.
Für `application_network_removed` beginnt es bei Schritt drei.

Abgeschlossene Schritte werden nie wiederholt. Bei fehlendem Container gibt
es keinen Stop-, Kill- oder Container-Remove-Aufruf.

## Evidence-first Continuation-Claim

Der Continuation-Claimname wird ausschließlich aus dem vollständigen SHA-256
der Cleanup-Continuation-ID abgeleitet.

Er wird erst nach exakter frischer Zustandsübereinstimmung owner-only per
exklusiver Neuanlage geschrieben und vor dem ersten Effekt synchronisiert.

Er bindet IDs, Hashes, `resume_from`, Restbudget, Ressourcen, Identitäten und
UTC-Startzeit.

Ein vorhandener oder technisch unklarer Continuation-Claim stoppt vor Docker.
Er wird nicht aufgrund von Alter entfernt.

Der ursprüngliche Cleanup-Claim bleibt während der gesamten Fortsetzung
offen und wird von diesem Operator niemals freigegeben.

## Exakte Mutation und Bestätigung

Jede Ressource wird einzeln mit intern abgeleitetem Namen adressiert.

Nach jedem Remove muss eine exakte read-only Namensliste vollständige
Abwesenheit bestätigen, bevor der nächste Schritt beginnt.

Nach dem letzten Network-Remove muss Volume-Inspect dieselbe rungebundene
owner-only Zuordnung bestätigen.

Alle Prozesse verwenden absoluten Dockerpfad, temporäres leeres CWD,
`LANG=C`, `LC_ALL=C`, keine Shell sowie feste Zeit- und Outputgrenzen.

## Unknown Outcome

Ab dem ersten möglichen Remove führt Nonzero, stderr, Timeout, Truncation,
Hard Kill, verlorene Bestätigung oder widersprüchliche Nachbeobachtung zum
sofortigen Abbruch.

Es gibt keinen Retry, Ersatzbefehl oder heuristische Erfolgsableitung.

Beide Claims bleiben bestehen; spätere read-only Reconciliation ist nötig.

Teilfortsetzung darf niemals als Erfolg ausgegeben werden.

## Continuation-Evidence

Nach bestätigter Runtimeentfernung und Volume-Erhalt wird getrennte private
Continuation-Evidence atomar persistiert.

Sie bindet alle IDs und Hashes, autorisierten Startzustand, ausgeführtes
Restbudget, erhaltenes Volume, getrennte Identitäten sowie UTC-Start und
Abschluss.

Sie lautet `runtime_removed_pending_finalization` und ist keine nachträglich
erzeugte LQ-339-Cleanup-Evidence.
Erst vollständig zurückgelesene Evidence erlaubt die Freigabe des exakten
Continuation-Claims. Der ursprüngliche Cleanup-Claim bleibt offen.

Ein Retry mit vorhandener exakter Evidence wiederholt nur eine gegebenenfalls
unbekannte Continuation-Claimfreigabe und führt kein Docker aus.

## Harte Verbote

Compose-Down, Stop, Start, Kill, Force, Disconnect, `--volumes`, Prune,
Wildcard-, Prefix-, Label- und Projektgruppencleanup bleiben verboten.

Der Operator entfernt kein Volume oder Image, führt kein SQL aus und liest
keine Docker-Events, Logs oder Volumeinhalte.

Er erzeugt keine Finalization-Evidence und gibt den LQ-339-Cleanup-Claim nicht
frei.

## Neutrale Ausgabe

Der spätere Command liefert ausschließlich:

- `runtime_removed_pending_finalization`;
- `rejected` bei lesbarem Zustandsmismatch vor Mutation;
- technisch unavailable ohne Ergebnisobjekt.

Die Ausgabe enthält nur Schema-Version, Operation
`disposable_postgres_runtime_cleanup_continuation` und Ausgang. Alle privaten
Details bleiben verborgen.

## Retention und Nichtwiederverwendung

Continuation-, Cleanup-Reconciliation-, Cleanup- und Run-ID, beide Claims,
Autorisierungen und Evidence bleiben mindestens so lange unterscheidbar, wie
Audit, Retry, Reconciliation oder Finalisierung sie benötigen.

Keine ID oder Evidence darf unter anderer Bindung wiederverwendet werden. Das
erhaltene Volume bleibt dem ursprünglichen Run zugeordnet.

Dieser Vertrag bestimmt keine konkrete Retentionfrist oder Ablagestrategie.

## Nichtziele

LQ-344 implementiert keinen Continuation-Operator, Entry Point, Test, Claim,
Evidencewriter oder Reconciliationoperator.

Es gibt keine Volume-Löschung, Schema-, Tabellen-, SQL-, Migration-, Port-,
Domainmodell-, Signatur-, Compose-, CLI- oder Production-Wiring-Entscheidung.

Bundle-Gates bleiben bei 37 Entry Points, 41 Operatormodulen, 27 Migrationen
und Head `20260819_0027`.

## Nächster Slice

LQ-345 sollte den owner-kontrollierten Continuation-Operator mit den drei
minimalen Restbudgets und Fake-basierten Tests implementieren.
Unknown-Outcome-Reconciliation der Continuation-Claims und jede
Volumenlöschung bleiben separate spätere Slices.
