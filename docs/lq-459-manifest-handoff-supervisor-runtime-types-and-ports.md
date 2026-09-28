# LQ-459 — Manifest Handoff Supervisor Runtime Types and Ports

## Ergebnis

LQ-459 konkretisiert Revision 0032 mit geschlossenen Runtimebinding- und
Control-Artefaktwerten sowie getrennten Store-/Lookupports.

Der Slice implementiert noch keinen Persistenz- oder Dockeradapter.

## Stabile Runtimeidentitäten

Vier neue repr-freie nicht leere IDs modellieren Creation, Runtimecontainer,
Control-Directory und Control-Artefakt.

Keine ID wird aus PID, Host, Pfad, Zeit oder Containername abgeleitet.

Der bestehende LQ-446-Handle bleibt die interne Jobkorrelation.

IDs erteilen keine Prozessfähigkeit.

## Image-Digest

`ManifestHandoffSupervisorImageDigest` akzeptiert ausschließlich
`sha256:` gefolgt von 64 kleingeschriebenen Hexzeichen.

Tags, Imagenamen und Großschreibung scheitern fail-closed.

Der Wert ist repr-frei.

Ein Request kann damit keinen Entrypoint auswählen.

## Artefaktfakten

Control-Artefaktfakten bestehen ausschließlich aus 64-stelligem
kleingeschriebenem SHA-256 und positiver Bytezahl.

Sie enthalten weder Bytes noch Pfad oder Dateiname.

Leere und übertypisierte Werte scheitern bei Konstruktion.

Die Fakten behaupten noch keine atomare Veröffentlichung.

## Geschlossene Rollen

Die Rollen-Enum enthält exakt Wrapper-ready, Release-token,
Release-consumed und Terminal-envelope.

Es gibt keinen freien Rollenstring.

Log-, PID-, Exitcode- und Diagnoseartefakte sind nicht Teil der Domain.

Jede Rolle bleibt einmalig je Handle gemäß LQ-458.

## Runtimebinding-Request

`BindManifestHandoffSupervisorRuntime` bindet ausschließlich Handle,
Creation-ID, Runtime-Container-ID, Control-Directory-ID und Image-Digest.

Der erfolgreiche Record ergänzt nur die serverseitige aware UTC Bindungszeit.

Alle Identitäten bleiben repr-frei.

Es gibt kein Host-, Socket-, Pfad- oder Runtimezustandsfeld.

## Getrennte Artefaktrequests

Ready, Release-token, Release-consumed und Terminal-envelope besitzen vier
verschiedene Requesttypen.

Ready verlangt eine Gated-Observation-ID.

Token und Consumed verlangen jeweils eine Release-ID.

Terminal-envelope verlangt eine terminale Observation-ID.

## Keine caller-gelieferte Rolle

Die vier Storemethoden bestimmen die Rolle durch Methode und Requesttyp.

Der Caller kann Ready nicht als Terminal oder Token umetikettieren.

Jeder Request bindet Artefakt-ID, Handle, exakt typisierte Korrelation und
Artefaktfakten.

Freie Payloads sind ausgeschlossen.

## Gespeicherter Artefaktrecord

Der gespeicherte Record enthält geschlossene Rolle, passende typisierte
Korrelations-ID, Fakten und serverseitige aware UTC Publikationszeit.

Eine Rollenmatrix validiert die Korrelationsklasse erneut.

Release-token und Consumed bleiben getrennte Rollen trotz gleicher ID-Art.

Der Record trägt keine Artefaktbytes.

## Runtimebinding-Store

`ManifestHandoffSupervisorRuntimeBindingStore.bind_runtime` akzeptiert genau
einen geschlossenen Request.

Erfolg liefert die persistente Binding, Divergenz den detailfreien Konflikt und
neutrale Abwesenheit `None`.

Der Port erzeugt keinen Container.

Technische Unverfügbarkeit bleibt separat.

## Runtime-Lookup

Der read-only Lookup löst exakt nach Handle oder Creation-ID auf.

Damit kann Create-Unknown ohne neue Creation-ID reconciliert werden.

Lookup mutiert und adoptiert keinen Enginebestand.

`None` ist weder Create-Nichtwirkung noch Terminalnachweis.

## Artefakt-Store

Der Store besitzt genau vier explizite Methoden für die vier Rollen.

Er persistiert nur Korrelation und Fakten eines bereits kontrolliert
veröffentlichten Artefakts.

Er schreibt keine Datei und erzeugt keine Tokenbytes.

Exakte Retry-/Konfliktsemantik implementiert der spätere Adapter.

## Artefakt-Lookup

Read-only Auflösung erfolgt nach Artefakt-ID oder nach Handle plus geschlossener
Rolle.

Der Lookup liest keine Datei und berechnet keinen Digest.

Fehlender Bestand liefert neutral `None`.

Eine erwartete fehlende Rolle bleibt in der Composition fail-closed.

## Konflikt

`ManifestHandoffSupervisorRuntimeConflict` ist feldlos und detailfrei.

Er vereinheitlicht divergente Wiederverwendung von Creation, Container,
Control-Directory, Artefakt-ID oder Handle/Rolle.

Es gibt kein Rebind oder Last-write-wins.

Konflikt erzeugt keine Engine- oder Dateiwirkung.

## Keine Authority

Kein Typ oder Port akzeptiert SessionPrincipal, Actor, Rolle im
Autorisierungssinn, Permission oder Allowboolean.

Runtime- und Artefaktkorrelationen erteilen keine Writer-/Recoveryfähigkeit.

Claimed Start und Recoveryauthority bleiben außerhalb.

Revocation wird nicht aus Containerbestand abgeleitet.

## Keine Prozesssteuerung

Ports akzeptieren kein Command, Args, Env, cwd, Shell, Timeout, Signal,
Restartpolicy oder Clock.

Es gibt keine Create-, Start-, Inspect-, Stop- oder Remove-Engineoperation.

Das Domainmodul importiert keine Docker-, Socket-, Prozess- oder
Persistenzbibliothek.

## Repr- und Fehlergrenze

Alle IDs, Digests, Requests, Bindings und Fakten sind repr-frei, soweit sie
interne Werte tragen.

Validierungsfehler enthalten keine konkreten IDs oder Infrastrukturdetails.

Host-, Socket-, Container- und Pfaddetails verlassen die Grenze nicht.

Es wird kein neuer technischer Exceptiontyp benannt.

## Keine Migration

LQ-459 ändert keine Tabelle, Spalte oder Migration.

Head bleibt `20260824_0032` mit 32 linearen Migrationen.

Es gibt keinen Seed oder Backfill.

Der persistente Adapter folgt separat.

## Kein Wiring

Es gibt keinen Engineclient, Dateicodec, Wrapper, Service oder Composer.

Kein CLI-, Route-, Operator-, Compose-, CI- oder Production-Wiring wird
ergänzt.

LQ-439 und LQ-455 bleiben unverändert.

## Tests

Fokussierte Tests belegen vier repr-freie IDs, strikten Image-Digest,
Artefaktfakten, vier Rollen, getrennte typisierte Requests, Rollenmatrix,
minimale Store-/Lookupports und fehlende Prozess-/Authoritygrenzen.

## Nichtziele

LQ-459 implementiert keine ID-/Clockquelle, Persistenztransaktion,
Artefaktveröffentlichung, Engineprimitive oder Servicecomposition.

Adapter, Engineclient, Wrapper, Integration, Bestand und Cleanup bleiben
separate Slices.

## Nächster Slice

LQ-460 sollte den persistenten Runtimebinding- und Artefaktkorrelationsadapter
mit idempotenten Appends und exakten read-only Auflösungen implementieren.

Engine- und Dateiprimitiven folgen danach separat.
