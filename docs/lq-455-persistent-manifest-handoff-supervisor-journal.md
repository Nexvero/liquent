# LQ-455 — Persistent Manifest Handoff Supervisor Journal

## Ergebnis

LQ-455 implementiert die getrennten LQ-453-Journalports gegen Revision 0031.

`DatabaseManifestHandoffSupervisorJournal` persistiert Registrierungen,
Transitionen und read-only Views ohne Prozesswirkung.

## Feste Backendbindung

Der Adapter wird mit genau einer typisierten Backendinstanz konstruiert.

Registrierungen einer anderen Instanz scheitern fail-closed.

Die Backend-ID wird weder aus Requesttransport noch Hostzustand abgeleitet.

Der Adapter besitzt keinen umschaltbaren Backendselector.

## Idempotente Registrierung

Writer- und Recoveryregistrierung bleiben getrennte Methoden und Typen.

Handle, Prepare oder Launch-Commit adressieren gemeinsam denselben bestehenden
Job.

Ein exakter Retry liefert den rekonstruierten ursprünglichen View.

Jede Divergenz liefert den detailfreien Journalkonflikt.

## Unveränderliche Prozessbindung

Capability, Claim, Owner, Scope, Roots und Handoffname werden beim Retry exakt
verglichen.

Es gibt kein Rebind, Adopt oder Last-write-wins.

Persistente Werte werden erneut durch bestehende Domaintypen validiert.

Beschädigte Bindungen sind technische Unverfügbarkeit.

## Vorwärtszustandsmaschine

Der Adapter erlaubt ausschließlich:

- Registrierung zu Launch-Commit;
- Launch-Commit zu Prepared-gated;
- Prepared-gated zu Release-Commit;
- Release-Commit zu Running;
- Launch, Gated, Release oder Running zu Termination-requested;
- jeden Zustand ab Launch bis Termination-requested zu Terminal-observed.

Terminal und ungültige Vorgänger öffnen keine weitere Transition.

## Launch-Commit

Die Launchtransition muss exakt die bereits registrierte Launch-Commit-ID
verwenden.

Eine neue ID oder ein zweiter Launch ist Konflikt.

Der Append startet selbst keinen Prozess.

Ein unklarer Commit wird mit derselben ID aufgelöst.

## Gated und Running

Gated ist nur nach Launch zulässig.

Running ist nur nach Release zulässig.

Beide Observation-IDs sind global stabil und idempotent.

Der Adapter beobachtet keinen OS-Prozess und erfindet keine Observation.

## Release

Release-Commit ist nur nach Prepared-gated zulässig.

Je Handle kann genau eine Releaseart appendiert werden.

Ein gespeicherter Release-Commit behauptet keine physische Gatewirkung.

Der spätere Service muss Commit und Gateprimitive kontrolliert verbinden.

## Terminierung

Terminierung ist ab Launch vor oder nach Release möglich.

Der View bewahrt eine bereits vorhandene Release-ID.

Termination-requested ist nicht terminal.

Signalversand und Ende bleiben außerhalb dieses Adapters.

## Terminal

Terminalappend akzeptiert nur den passenden Writer- oder Recoverycompletiontyp.

Handle, Claim, Owner, Outcome, Filename und Manifestfakten werden geschlossen
rekonstruiert.

Terminal ist genau einmal appendierbar und beendet die Zustandsmaschine.

Der Adapter leitet Terminal nicht aus PID, Timeout oder Abwesenheit ab.

## Sequenzprüfung

Jede Inspection validiert lückenlose positive Sequenzen ab eins.

Capability muss in Job und jeder Transition übereinstimmen.

Jede Transitionart muss einen erlaubten direkten Vorgänger besitzen.

Lücken, unbekannte Arten und Rücksprünge sind technische Unverfügbarkeit.

## Views

Writer- und Recoveryviews werden ausschließlich aus Job und geordneter
Transitionhistorie aufgebaut.

Release-, Terminate- und Terminal-ID werden aus den jeweiligen stabilen
Transition-IDs rekonstruiert.

Die Viewzeit ist die letzte direkte Journalzeit.

Ohne Transition bleibt der Zustand `prepare_registered`.

## Read-only Inspection

Writer- und Recoveryinspection lesen ausschließlich den exakten Handle.

Ein Handle der anderen Capability oder fehlender Bestand liefert neutral
`None`.

Inspection mutiert, startet, released, terminiert oder adoptiert nichts.

`None` ist kein Prozessende.

## Transaktionen

Jeder Append läuft in einer Datenbanktransaktion.

PostgreSQL serialisiert Job- und Transitionstabellen über eine feste
Lockgrenze.

SQLite bleibt lokale Testgrenze; andere Dialekte scheitern fail-closed.

Die Clock wird konstruktiv injiziert und nie vom Request geliefert.

## Detailfreie Grenzen

Neutrale Abwesenheit bleibt `None`.

Divergente Wiederverwendung bleibt
`ManifestHandoffSupervisorJournalConflict`.

Persistenz-, Decode-, Clock- und Historienfehler werden als bestehende
detailfreie `ManifestHandoffRegistryUnavailable` vereinheitlicht.

Keine ID oder Infrastrukturangabe erscheint in Fehlertexten.

## Keine Authority

Der Adapter akzeptiert keine Session, Rolle, Permission oder Allowentscheidung.

Claim und Owner sind Korrelation, keine neue Autorisierung.

Die Plattform bleibt Quelle für claimed Start und Recoveryauthority.

Journalfortschritt kann Revocation nicht umgehen.

## Keine Prozesswirkung

Das Modul importiert weder subprocess noch Docker-, Socket- oder
Service-Manager-Bibliotheken.

Es erzeugt keinen Wrapper, Gatekanal, Signal oder Kindprozess.

Es gibt kein CLI-, Compose-, Route-, Operator- oder Production-Wiring.

LQ-439 bleibt unverändert.

## Migration und Bestand

LQ-455 ändert kein Schema und erzeugt keinen Seed oder Backfill.

Head bleibt `20260824_0031` mit 31 linearen Migrationen.

Altattempts ohne Journaljob bleiben unverändert fail-closed.

Service- und Bestandsverankerung folgen separat.

## Tests

Fokussierte Prüfungen belegen Backendbindung, exakte Registrierungsretry,
strikte Vorwärtszustände, Launch-ID-Bindung, einmalige Transitionarten,
geschlossene Terminalpayload, lückenlose Projektion, read-only Inspection und
prozess-/authorityfreie Grenzen.

## Nichtziele

LQ-455 implementiert keinen Supervisorservice, Prozessrunner, Gatewrapper,
Transportclient oder Plattformcomposer.

Serviceprozess, Integration, Bestand, Cleanup und Retention bleiben separat.

## Nächster Slice

LQ-456 sollte den kontrollierten Supervisor-Serviceprozess- und
Gateprimitive-Vertrag auf dem persistenten Journal definieren.

Konkreter Prozessadapter und Plattformintegration folgen danach separat.
