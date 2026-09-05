# LQ-453 — Manifest Handoff Supervisor Journal Types and Ports

## Ergebnis

LQ-453 konkretisiert LQ-452 mit geschlossenen Journalwerten und getrennten
Writer-/Recoveryports.

Der Slice implementiert noch keine Journalpersistenz und keinen Prozess.

## Journalidentitäten

Drei neue repr-freie nicht leere IDs modellieren Launch-Commit, direkte
Gated-Observation und direkte Running-Observation.

Prepare-, Release-, Terminate-, Terminal-, Backend- und Handle-IDs werden aus
LQ-446/LQ-450 wiederverwendet.

Keine ID wird aus PID, Host, Zeit oder Pfad abgeleitet.

## Geschlossener Zustand

`ManifestHandoffSupervisorJournalState` enthält exakt:

- `prepare_registered`;
- `launch_committed`;
- `prepared_gated`;
- `release_committed`;
- `running`;
- `termination_requested`;
- `terminal_observed`.

Es gibt keinen freien Statusstring.

## Getrennte Registrierung

Writer- und Recoveryregistrierung sind verschiedene Typen.

Beide binden Backend, Prepare, Launch-Commit und Handle an den passenden
geschlossenen LQ-446-Prozessrequest.

Writer- und Recovery-Claim-/Owner-/Bindingtypen bleiben dadurch getrennt.

Es gibt keinen nullable generischen Capabilityrequest.

## Übergangsrequests

Launch, Gated, Release, Running und Terminate besitzen jeweils einen eigenen
Requesttyp aus stabiler Übergangs-ID und Handle.

Terminal besitzt getrennte Writer-/Recoveryrequests mit der passenden
geschlossenen LQ-446-Completion.

Jeder Request validiert exakte Domainklassen.

Terminalrequest und Completion müssen denselben Handle tragen.

## Journalviews

Writer und Recovery besitzen getrennte immutable Journalviews.

Jeder View bindet Registrierung, geschlossenen Zustand, serverseitige aware
UTC Beobachtungszeit und nur die für den Zustand zulässigen optionalen IDs.

Terminal verlangt Terminal-ID und exakt passenden geschlossenen Completiontyp.

Nichtterminale Views dürfen kein Resultat tragen.

## Release- und Terminationsmatrix

`release_committed` und `running` verlangen eine Release-ID.

`termination_requested` verlangt eine Terminate-ID und darf vor oder nach
Release liegen.

`terminal_observed` darf die historisch vorhandene Release- und Terminate-ID
tragen, verlangt aber immer Terminal-ID und Resultat.

Andere Zustände tragen keine Operations- oder Terminalresultate.

## Repr- und Fehlergrenze

Alle Identitäten, Prozessrequests, Registrierungen und Resultate bleiben
repr-frei.

Fehlermeldungen enthalten keine IDs, Claims, Owner, Pfade oder Prozessdetails.

`ManifestHandoffSupervisorJournalConflict` ist feldlos und detailfrei.

Technische Unverfügbarkeit bleibt separat.

## Writerjournalport

`ManifestHandoffWriterSupervisorJournal` besitzt genau acht Methoden:

- Writer registrieren;
- Launch committen;
- Gated beobachten;
- Release committen;
- Running beobachten;
- Terminierung anfordern;
- Terminal beobachten;
- Journal read-only inspizieren.

Jede Mutation akzeptiert genau einen geschlossenen Request.

## Recoveryjournalport

Der Recoveryport besitzt dieselben acht Übergangsrollen mit eigenen
Methodennamen und Recoverytypen.

Recoveryterminal akzeptiert keinen Writercompletiontyp.

Der Port erteilt keine Writer- oder Cleanupfähigkeit.

Writer- und Recoveryjournal sind nicht austauschbar.

## Read-only Inspect

Inspect akzeptiert ausschließlich den opaken Handle.

Es liefert den höchsten konsistenten View oder neutrales `None`.

Inspect mutiert, startet, released, signalisiert und adoptiert nichts.

`None` ist kein terminaler Endnachweis.

## Keine generische Mutation

Es gibt kein `set_state`, `append(kind,payload)`, `run` oder `execute`.

Kein Port akzeptiert Dict, JSON, Command, Args, Env, cwd, Shell, Timeout,
Signal oder Clock.

Caller können keine Transition umetikettieren.

Die Persistenzimplementation muss die Reihenfolge aus LQ-452 erzwingen.

## Keine Authority

Journalports akzeptieren keine Session, Actorentscheidung, Rolle, Permission,
Allowboolean oder Authoritysnapshot.

Claim und Owner werden nur über den bereits geschlossenen Prozessrequest
korreliert.

Das Journal entscheidet keine fachliche Start- oder Recoveryauthority.

Revocation bleibt an den Plattformgrenzen wirksam.

## Kein Prozessadapter

Das neue Domainmodul importiert keine Prozess-, Persistenz-, IPC-, Socket-
oder Produktbibliothek.

Die Ports beschreiben Journaling, nicht physische Spawn-, Gate- oder
Signalwirkung.

Direkte Beobachtungen dürfen später nur vom kontrollierten Service erzeugt
werden.

## Keine Persistenzentscheidung

LQ-453 ergänzt kein SQL, keine Tabelle, Migration, Datei- oder Logengine.

Head bleibt `20260824_0030` mit 30 linearen Migrationen.

Es gibt kein Seed und keinen Backfill.

Die Journalfoundation folgt separat.

## Kein Wiring

Es gibt keinen Serviceprozess, Clientadapter, Wrapper oder Gatekanal.

Kein CLI-, Operator-, Route-, Compose-, CI- oder Production-Wiring wird
ergänzt.

LQ-439 und LQ-451 bleiben unverändert.

## Tests

Fokussierte Tests belegen:

- drei repr-freie Journalidentitäten;
- exakt sieben geschlossene Zustände;
- getrennte Writer-/Recoveryregistrierungen und Terminalrequests;
- strikte Handle- und Completionbindung;
- Viewmatrix für Release, Terminate und Terminal;
- genau acht Writer- und acht Recoveryjournalmethoden;
- read-only Inspect ohne Mutation;
- keine freie Payload-, Prozess-, Authority- oder Clockgrenze;
- unveränderten Head 0030;
- Roadmap- und Folgeslicebindung.

## Nichtziele

LQ-453 implementiert keine Journaltransaktion, ID- oder Clockquelle,
Prozessprimitive oder Serviceauthentisierung.

Persistenzfoundation, Adapter, Serviceprozess, Plattformcomposition, Bestand,
Cleanup und Retention bleiben separat.

## Nächster Slice

LQ-454 sollte die additive persistente Foundation für Jobbindungen und
append-orientierte Journalübergänge definieren.

Journaladapter und Serviceimplementation folgen danach separat.
