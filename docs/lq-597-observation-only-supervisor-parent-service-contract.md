# LQ-597 — Observation-only Supervisor Parent Service Contract

## Ergebnis

LQ-597 korrigiert die Verantwortungsgrenze zwischen Parentservice und
kindprozess-eigenem LQ-596-Wrapper.

Der Slice ändert noch keine bestehende Serviceimplementation.

## Prepare

Der Parent registriert Job, Launch und Runtimebinding vor Prozesswirkung.

Er startet genau den digestgebundenen Container.

Danach liest er das direkt vom Wrapper publizierte Ready-Artefakt.

Er publiziert Ready niemals selbst.

Erst der validierte und persistent gebundene direkte Nachweis öffnet
`prepared_gated`.

## Release

Der Parent commitet zuerst dieselbe stabile Release-ID im Journal.

Danach publiziert er ausschließlich das Release-Token.

Das Consumed-Artefakt wird ausschließlich vom Wrapper erzeugt.

Der Parent liest, validiert und persistiert dessen Fakten, bevor Running
festgehalten wird.

## Keine Parent-Capability

Nach Consumed ruft der Parent keinen zweiten Writer-/Recovery-Supervisor auf.

LQ-468 darf in diesem Productionpfad nicht verdrahtet werden.

Der Parent schreibt kein Manifest und führt keinen Reconciler aus.

Die Capability wirkt ausschließlich im bereits gebundenen Container.

## Inspect und Wait

Der Parent korreliert Journal, Runtimebinding, Enginezustand und vorhandene
Wrapperartefakte read-only.

Running ohne Terminal-Envelope bleibt nichtterminal.

Terminal-Envelope ohne direkt terminale Enginebeobachtung bleibt gesperrt.

Engine-Terminalität ohne valides Envelope wird konservativ als bestehender
Unknown-/Unavailable-Ausgang behandelt, nie als Erfolg.

## Terminalisierung

Nur derselbe Handle, dieselbe Runtime, dasselbe Profil und dieselbe
Releasebindung dürfen gemeinsam terminalisiert werden.

Der Parent validiert das Wrapper-Envelope kanonisch und appendiert genau eine
stabile Terminalobservation.

Er erzeugt keine Outcomefelder aus Exitcode, Logs oder Settings.

## Release-Unknown

Nach Kommunikationsverlust wird dieselbe Release-ID aufgelöst.

Der Parent publiziert kein zweites Token, wenn Konsum möglich war.

Consumed und Terminal werden ausschließlich read-only rekonstruiert.

Mehrdeutigkeit bleibt fail-closed.

## Terminate

Vor Enginewirkung wird der stabile Terminate-Fakt appendiert.

Stop oder Kill adressiert nur die gebundene Runtime.

Signalannahme ist kein Terminalnachweis.

Der Parent beobachtet weiter bis Engineende und Wrapperoutcome korreliert sind.

## Restart

Startup führt keine automatische Wiederfreigabe oder Capabilityausführung aus.

Ein expliziter Inspect-/Recoverypfad liest den aktuellen System-of-Record-
Bestand und dieselben Control-Artefakte.

Consumed ohne Terminal verbietet einen zweiten Start.

## LQ-468-Disposition

Der LQ-468-Kompatibilitätsadapter bleibt für isolierte ältere Porttests
vorhanden.

Er ist kein Bestandteil des korrigierten Docker-Productiongraphs.

Eine spätere Bereinigung oder Deprecation benötigt einen eigenen Slice und
darf bestehende Signaturen nicht beiläufig entfernen.

## Readiness

Readiness darf den vollständigen Graphen erst melden, wenn Wrapperentrypoints,
Codecrollen, Parentbeobachtung und Engineclient konstruktiv vollständig sind.

Sie startet keinen Probecontainer und erzeugt keine Control-Datei.

Liveness bleibt reine Prozesslebendigkeit.

## Authority

SessionPrincipal identifiziert weiterhin nur einen Actor.

Researchpermission, Membership, Rolle oder Settings-Allow erteilen keine
Supervisorauthority.

Claim, Owner, Lifecycle und aktuelle Sperren stammen aus dem System of Record.

## Ressourcenbesitz

Der Parent besitzt process-eigene Engineclients und schließt sie genau einmal.

Er beendet bei Shutdown keine laufenden Jobs pauschal und löscht keine
Control-Directories oder Container.

Retention und Cleanup bleiben getrennte owner-kontrollierte Operationen.

## Keine Implementation

LQ-597 ändert keine Domain-, Port-, Service-, Settings-, Appfactory-, Compose-
oder Deploymentquelle.

Es ergänzt keine Migration oder Tabelle.

## Nächster Slice

LQ-598 schließt die Blockerentscheidung ab und legt die sichere
Implementierungsreihenfolge für Wrapper, Parentservice und erneutes
Production-Wiring fest.
