# LQ-460 — Persistent Manifest Handoff Supervisor Runtime

## Ergebnis

LQ-460 implementiert die LQ-459-Ports gegen Revision 0032.

`DatabaseManifestHandoffSupervisorRuntime` persistiert ausschließlich
Runtime- und Artefaktkorrelationen, ohne Docker- oder Dateizugriff.

## Runtimebinding

Eine neue Binding verlangt einen bestehenden Journaljob.

Handle, Creation, Runtimecontainer, Control-Directory und Image-Digest werden
atomar und einmalig gebunden.

Exakter Retry liefert den ursprünglichen Record und seine Zeit.

Divergenz oder belegte IDs liefern detailfreien Konflikt.

## Create-Unknown

Read-only Auflösung ist nach Handle oder Creation-ID möglich.

Sie erzeugt keine neue Creation-ID und adoptiert keinen Enginebestand.

Fehlender Bestand liefert neutral `None`.

`None` beweist keine Container-Nichtwirkung.

## Ready

Ready verlangt Runtimebinding und einen vorhandenen Launch-Commit desselben
Handles.

Die Gated-Observation-ID ist die Korrelation des Artefakts, nicht die ID des
vorherigen Launch-Commits.

Ready schreibt keine Datei und appendiert noch keinen Gated-Journalfakt.

Jede Rolle ist je Handle einmalig.

## Release-Token

Release-token verlangt einen vorhandenen Release-Commit mit exakt derselben
Release-ID.

Ein Release-Commit anderer ID ist keine Freigabe.

Der Adapter veröffentlicht keine Tokenbytes.

Die persistierte Korrelation behauptet keinen Gatekonsum.

## Release-consumed

Consumed verlangt Runtimebinding, exakt korrelierten Release-Commit und ein
bereits persistiertes Release-token derselben Release-ID.

Token und Ack bleiben getrennte Rollen und Artefaktfakten.

Ein fehlendes oder abweichendes Token endet neutral ohne Append.

Running wird durch diesen Adapter nicht erzeugt.

## Terminal-envelope

Terminal-envelope verlangt eine bestehende Runtimebinding und seine typisierte
terminale Observation-ID.

Es ist Vorstufe der späteren Journalterminalisierung und benötigt daher noch
keine vorhandene Terminaltransition.

Der Adapter interpretiert Envelope nicht als Runtime-Ende.

Docker-Terminalbeobachtung bleibt separat.

## Idempotente Artefakte

Exakter Retry vergleicht Artefakt-ID, Handle, Rolle, Korrelations-ID, Digest und
Bytezahl vollständig.

Eine andere ID derselben Handle-/Rolle oder divergente Wiederverwendung ist
Konflikt.

Es gibt kein Überschreiben und keine zweite Rollenwirkung.

Ursprüngliche Publikationszeit bleibt erhalten.

## Read-only Artefaktauflösung

Lookup erfolgt exakt nach Artefakt-ID oder Handle plus geschlossener Rolle.

Persistente Rollen werden auf die passende Gated-, Release- oder
Terminal-ID-Klasse rekonstruiert.

Beschädigte Rollen oder Fakten bleiben technische Unverfügbarkeit.

Lookup liest keine Artefaktdatei.

## Transaktionen

Jeder Append läuft in einer Datenbanktransaktion.

PostgreSQL serialisiert Journal-, Runtime- und Artefakttabellen über eine feste
Lockgrenze.

SQLite bleibt lokale Testgrenze; andere Dialekte scheitern fail-closed.

Die Clock ist konstruktiv injiziert und kein Requestparameter.

## Detailfreie Grenzen

Neutrale fehlende Voraussetzungen liefern `None`.

Divergente Eindeutigkeiten liefern
`ManifestHandoffSupervisorRuntimeConflict`.

Decode-, Clock-, SQL- und Strukturfehler werden über die bestehende detailfreie
Registry-Unverfügbarkeit vereinheitlicht.

Keine Infrastrukturdetails verlassen die Grenze.

## Keine Authority oder Prozesswirkung

Der Adapter akzeptiert keine Session, Rolle, Allowentscheidung oder
Prozesssteuerung.

Er importiert weder Docker-, Socket-, subprocess- noch Dateibibliotheken.

Er erstellt, startet, inspiziert oder beendet keinen Container und schreibt
kein Control-Artefakt.

Korrelationen erteilen keine Capability.

## Migration und Bestand

LQ-460 ändert kein Schema und erzeugt keinen Seed oder Backfill.

Head bleibt `20260824_0032` mit 32 linearen Migrationen.

Bestehende Container oder Dateien werden nicht adoptiert.

Es gibt kein CLI-, Compose-, Route-, Operator- oder Production-Wiring.

## Tests

Fokussierte Prüfungen belegen idempotente Runtimebinding, Handle-/Creation-
Lookup, Launch-vor-Ready, Release-ID-vor-Token, Token-vor-Consumed, getrennte
Terminalvorstufe, Rollenrekonstruktion und prozessfreie Grenzen.

## Nichtziele

LQ-460 implementiert keinen Engineclient, Artefaktcodec, atomaren Filepublisher,
Wrapper, Service oder Plattformcomposer.

Engine- und Dateiprimitiven, Integration, Bestand und Cleanup bleiben separat.

## Nächster Slice

LQ-461 sollte den geschlossenen Docker-Engine-Adaptervertrag für Create,
Inspect, Start, Wait und Terminate definieren.

Control-Artefaktcodec und Fileprimitive folgen separat.
