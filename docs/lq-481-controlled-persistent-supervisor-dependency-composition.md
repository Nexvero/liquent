# LQ-481 — Controlled Persistent Supervisor Dependency Composition

## Ergebnis

LQ-481 implementiert eine explizite Factory für den vollständigen persistenten
Manifest-Handoff-Supervisorservice.

Die Composition ist nach Aufbau inert und wird nicht automatisch aktiviert.

## Explizite Eingänge

Die Factory verlangt eine bereits konfigurierte SQLAlchemy-Engine, stabile
Backendinstanz, geschlossene Supervisor-Engine, private Control-Artefaktgrenze,
Capabilityexecutor und Capability-Outcomebeobachtung.

Keine Abhängigkeit wird aus globalem Zustand oder Umgebungsvariablen gelesen.

## Datenbankeigentum

Die injizierte Datenbankengine bleibt Eigentum des Callers.

Die Factory öffnet beim Aufbau keine Verbindung und führt keine Abfrage aus.

Sie migriert, erstellt oder seedet kein Schema.

## Backendbindung

Die Backendinstanz muss bereits als geschlossener interner ID-Typ vorliegen.

Sie wird unverändert an das Journal gebunden.

Die Factory erzeugt oder rotiert keine Backendidentität.

## Persistenzadapter

Aus derselben Datenbankengine werden Journal, Runtime-/Artefaktpersistenz und
Gatebinding-Adapter konstruiert.

Damit verwenden alle Teilservices dieselbe persistente System-of-Record-
Grenze.

Es gibt keinen In-Memory- oder Productionfallback.

## Gemeinsame Runtimegrenze

`DatabaseManifestHandoffSupervisorRuntime` erfüllt Runtimebinding-,
Artefaktstore- und Artefaktlookupports für alle Teilservices.

Es wird genau eine Instanz geteilt.

Ready, Token, Consumed und Terminal sehen dadurch denselben aktuellen Bestand.

## Codec und Wrapper

Die Factory konstruiert genau einen kanonischen Control-Artefaktcodec.

Der File-Gatewrapper verwendet denselben Codec und dieselbe injizierte private
Control-Artefaktgrenze als Publisher und Reader.

Requests können weder Codec noch Filegrenze ersetzen.

## Private Artefaktgrenze

Control-Artefakte werden bereits vollständig konfiguriert injiziert.

Die Factory erhält keinen Rootpfad, Resolver, Dateimodus oder
Verzeichnisnamen.

Sie erstellt oder verändert beim Aufbau kein Verzeichnis und keine Datei.

## Supervisor-Engine

Die Engine wird bereits geschlossen und konstruktiv konfiguriert injiziert.

Die Factory kennt keinen Dockerclient, Socket, Image-Tag oder freien
Engineparameter.

Beim Aufbau findet kein Create, Inspect, Start, Wait oder Terminate statt.

## Capabilitygrenzen

Executor und Outcome-Beobachtung werden getrennt injiziert.

Damit bleiben erstmalige Capabilitywirkung und spätere read-only/bounded
Outcome-Reconciliation getrennte Verantwortlichkeiten.

Die Factory führt keine Capability aus.

## Teilservices

LQ-475 Prepare, LQ-476 Release, LQ-477 Inspect, LQ-478 Terminal und LQ-479
Terminate werden mit denselben Adapterinstanzen konstruiert.

Inspect wird zusätzlich als gemeinsame read-only Terminal-Retry-Grenze geteilt.

Es gibt keinen alternativen Teilservicegraphen.

## Servicefassade

Die fünf Teilservices werden abschließend in die LQ-480-Fassade eingesetzt.

Die Factory gibt ausschließlich
`PersistentManifestHandoffSupervisorService` zurück.

Low-Level-Adapter werden nicht separat exportiert.

## Clock

Eine optionale konstruktive Clock kann für Journal, Runtime, Gatebinding und
Terminate-Unknown geteilt werden.

Sie ist kein Command- oder Callerparameter.

Eine ungültige Clockwirkung bleibt an den bestehenden Adaptergrenzen
detailfrei gesperrt.

## Aufbaufehler

Fehlende Abhängigkeiten, falsche Engine-/Backendtypen und ungültige Clock
scheitern vor Rückgabe detailfrei.

Bestehende technische Unverfügbarkeit wird unverändert weitergereicht.

Andere unerwartete Aufbaufehler werden über dieselbe bestehende
`ManifestHandoffRegistryUnavailable`-Grenze vereinheitlicht.

## Keine Authority

Die Factory akzeptiert keine Session, Nutzer-, Workspace-, Rollen-, Permission-
oder Allowentscheidung.

Sie löst keine aktuelle Authority auf und cached keine Entscheidung.

Servicecomposition erteilt selbst keine fachliche Fähigkeit.

## Keine automatische Aktivierung

Die Factory wird nicht aus `create_app`, Lifespan, Modulimport oder globalem
Singleton aufgerufen.

Sie registriert keine Route, CLI, Worker, Thread, Scheduler oder Signalhandler.

Erst ein späterer expliziter Caller kann die zurückgegebene Fassade verwenden.

## Ressourcenbesitz

Databaseengine, Supervisor-Engine, Control-Artefaktgrenze, Executor und
Outcomeadapter bleiben extern besessen.

Die Fassade besitzt keine Close-, Dispose- oder Shutdownoperation.

Lifecycle und geordneter Shutdown bleiben Aufgabe der späteren Composition.

## Kein Schema oder Deployment

LQ-481 ergänzt keine Migration, Tabelle, SQL-, Domain- oder Portsignatur.

Head bleibt `20260825_0033` mit 33 linearen Migrationen.

Es gibt keinen Seed, Backfill, Compose-, Container- oder Production-Wiring-
Entscheid.

## Tests

Fokussierte Prüfungen belegen explizite Eingänge, gemeinsame Persistenzadapter,
einen Codec/Wrapper, vollständige Teilserviceverdrahtung, Fassadenrückgabe,
geteilte Clock und fehlende Aufbauwirkung oder automatische Aktivierung.

## Nächster Slice

LQ-482 sollte den kontrollierten Production-Wiring-Vertrag für opt-in
Aktivierung, Ressourcenbesitz, Readiness und geordneten Shutdown definieren,
ohne ihn bereits zu aktivieren.
