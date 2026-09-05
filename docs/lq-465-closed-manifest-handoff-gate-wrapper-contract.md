# LQ-465 — Closed Manifest Handoff Gate Wrapper Contract

## Ergebnis

LQ-465 definiert eine geschlossene typisierte Zustandskette für den
Container-Gatewrapper.

Der Slice implementiert noch keinen Wrapperprozess und führt keinen Writer oder
Reconciler aus.

## Zustandskette

Die einzige reguläre Freigabefolge ist Startbindung, Ready, akzeptiertes
Release-Token und dauerhaft publiziertes Consumed-Ack.

Jede Stufe trägt die vorherige typisierte Stufe unverändert weiter.

Caller können keine Stufe überspringen oder einen freien Status angeben.

## Startbindung

Die Startbindung enthält Handle, Control-Directory-ID und festes Writer- oder
Recoveryprofil.

Sie bindet vorab Ready-, Consumed- und Terminal-Artefakt-IDs sowie Gated- und
Terminal-Observation-ID.

Die drei lokalen Artefakt-IDs müssen verschieden sein.

Release-ID und Token-Artefakt-ID sind noch nicht vorhanden und werden nicht
vom Startcaller erfunden.

## Kein Infrastrukturinput

Die Startbindung enthält keinen Hostpfad, Dateinamen, Socket, PID, Command,
Entrypoint oder Timeout.

Control-Directory-ID ist weiterhin nur eine stabile Korrelation.

Engine- und Fileadapter werden später konstruktiv komponiert.

## Ready

`publish_ready` akzeptiert ausschließlich die geschlossene Startbindung.

Der Ready-Zustand verlangt einen bereits dauerhaft publizierten
wrapper_ready-Record.

Control-Directory-ID und Artefakt-ID müssen exakt der Bindung entsprechen.

Ready behauptet weder Release noch Capabilityausführung.

## Ready vor Code

Der spätere Wrapper darf vor Ready keinen Writer- oder Recoverycode laden.

Ready bestätigt nur validierte Jobbindung und erreichbare Gateprimitive.

Engine-Running allein erzeugt keinen Ready-Zustand.

Die Plattform persistiert Gated erst nach separater Korrelation.

## Await Release

`await_release` akzeptiert ausschließlich einen typisierten Ready-Zustand.

Neutrale Tokenabwesenheit liefert `None` und lässt den Wrapper gated.

Beschädigter, divergenter oder technisch unlesbarer Bestand ist nicht neutral.

Der Wrapper pollt nur die feste release_token-Rolle seines Control-Directory.

## Akzeptiertes Token

Ein akzeptiertes Token bindet Ready, Token-Artefakt-ID und Release-ID.

Die Token-ID muss von Ready-, Consumed- und Terminal-ID verschieden sein.

Die spätere Implementation muss Dokumenthandle und Control-Directory sowie
persistenten Release-Commit derselben Release-ID korrelieren.

Ein anderes Token wird niemals normalisiert oder konsumiert.

## Consumed-Ack

`publish_consumed` akzeptiert nur ein bereits akzeptiertes Token.

Der Released-Zustand verlangt einen dauerhaft publizierten
release_consumed-Record unter der vorab gebundenen Consumed-ID.

Control-Directory-ID und Rolle werden erneut geprüft.

Token und Ack bleiben getrennte unveränderliche Artefakte.

## Einziger Ausführungsmarker

`ReleasedManifestHandoffSupervisorGateWrapper` ist der einzige Typ, der den
Gateabschluss für Capabilityausführung belegt.

Es gibt kein `allowed`, `authorized` oder caller-geliefertes Boolean.

Die Wrapperimplementation darf Capabilitycode erst nach Konstruktion dieses
Markers importieren oder aufrufen.

Ready oder Token allein genügen nicht.

## Release-Unknown

Nach Wrapper- oder Serviceneustart werden Ready, persistenter Release-Commit,
Token und Ack über dieselben IDs read-only korreliert.

Byteidentische Publikationsretries behalten dieselbe Zustandsstufe.

Es wird keine neue Release-ID und kein zweites Ack erzeugt.

Mehrdeutigkeit bleibt fail-closed.

## Terminal vor Release

Ein kontrolliertes technisches oder fachliches Ende kann nach Ready, aber vor
Capabilityfreigabe auftreten.

Deshalb akzeptiert Terminalisierung entweder Ready oder Released als
geschlossene Gatebasis.

Ein Zustand vor dauerhaftem Ready kann kein valides Envelope publizieren.

Vor-Release-Terminalität erteilt rückwirkend keine Capability.

## Terminal nach Release

Nach Capabilityausführung trägt Terminalisierung den vollständigen Released-
Marker einschließlich Token und Consumed-Ack weiter.

Der Outcome ersetzt diese Gatebelege nicht.

Engine-Terminalität bleibt eine weitere getrennte Voraussetzung der späteren
Supervisorcomposition.

## Profilgebundener Outcome

Writerprofil akzeptiert ausschließlich einen geschlossenen Writerabschluss.

Recoveryprofil akzeptiert ausschließlich einen geschlossenen
Recoveryabschluss.

Der Outcome-Handle muss exakt dem gebundenen Supervisorhandle entsprechen.

Cross-Profile- und Cross-Handle-Outcomes scheitern bei Konstruktion.

## Terminal-Envelope

`publish_terminal` verlangt einen geschlossenen Terminalrequest.

Der Completed-Zustand verlangt die vorab gebundene Terminal-Artefakt-ID,
terminal_envelope-Rolle und dasselbe Control-Directory.

Die Terminal-Observation-ID bleibt Teil der Startbindung und des später
kodierten Envelopes.

Envelope-Publikation allein behauptet kein Runtime-Ende.

## Publikationsbelege

Ready, Consumed und Terminal akzeptieren ausschließlich den bestehenden
`PublishedManifestHandoffSupervisorControlArtifact`.

Damit sind Digest und Bytezahl bereits an dauerhaft publizierte Bytes gebunden.

Die Zustandswerte tragen keine Artefaktbytes oder Pfade.

Persistente LQ-460-Korrelation folgt separat im Supervisorservice.

## Konflikt

`ManifestHandoffSupervisorGateWrapperConflict` ist feldlos und detailfrei.

Er vereinheitlicht divergente immutable Artefaktpublikation an der
Wrappergrenze.

Er enthält keine ID, Rolle, Datei- oder Prozessdetails.

Technische Unverfügbarkeit bleibt separat an der bestehenden Grenze.

## Keine Authority

Kein Gatewert und keine Methode akzeptiert SessionPrincipal, User-ID,
Permission, Managementrolle oder Allowentscheidung.

Das Release-Token ist ein persistenter Commitbeleg, keine allgemeine
Plattformauthority.

Aktuelle Claim-/Owner- und Terminate-Voraussetzungen bleiben in der
Supervisorcomposition.

## Keine Enginewirkung

Der Port erstellt, startet, wartet oder beendet keinen Container.

Engine-Running und Engine-Terminal werden nicht aus Artefakten abgeleitet.

Der Wrapper besitzt keinen Engine-Socket.

Ein Artefaktkonflikt startet keinen Ersatzprozess.

## Keine Fileimplementation

Der Vertrag schreibt oder liest selbst keine Datei.

LQ-464-Codec, Publisher und Reader werden erst durch die Implementation
verwendet.

Es gibt keinen Pfad-, Modus-, fsync- oder Dateinamenparameter.

## Kein Schema oder Wiring

LQ-465 ändert keine Tabelle, Migration oder Persistenzsignatur.

Head bleibt `20260824_0032` mit 32 linearen Migrationen.

Es gibt keinen Seed, Backfill, Wrapperentrypoint, CLI-, Route-, Compose-,
Service- oder Production-Wiring.

## Tests

Fokussierte Tests belegen unterschiedliche Artefakt-IDs, feste Rollen,
stufenweise Portsignaturen, Token-ID-Separation, Released als einzigen
Ausführungsmarker, Ready-/Released-Terminalpfade und Profil-/Handlebindung.

## Nächster Slice

LQ-466 sollte den Gatewrapper gegen LQ-464 implementieren, ohne bereits den
Supervisorservice oder Productionentrypoint zu verdrahten.

Servicecomposition und Recovery folgen separat.
