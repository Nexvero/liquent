# LQ-482 — Controlled Supervisor Production Wiring Contract

## Ergebnis

LQ-482 definiert den verbindlichen opt-in Production-Wiring-Vertrag für den
persistenten Manifest-Handoff-Supervisorservice.

Der Slice aktiviert und verdrahtet den Service noch nicht.

## Standard bleibt geschlossen

Eine Datenbank, migriertes Schema oder vorhandene Supervisorrecords aktivieren
den Service nicht automatisch.

Ohne vollständige explizite Supervisor-Betriebsgruppe bleibt der Prozess
unverändert geschlossen.

Es gibt keinen lokalen, Preview- oder Productiondefault.

## Vollständige Aktivierungsgruppe

Opt-in verlangt gemeinsam eine stabile Backendinstanz, Writer- und Recovery-
Image-Digests, private Control-Root-Entscheidung, Engineclientpolicy,
Capabilityprimitive, Outcome-Waitpolicy und Ressourcenbesitzentscheidung.

Ein einzelner Wert oder eine partielle Gruppe ist ein fail-fast
Konfigurationsfehler.

Kein fehlender Wert wird aus Host, Request, Datenbank oder Dateisystem geraten.

## Interne Identitäten

Backendinstanz und alle Runtimeidentitäten sind stabile interne Fakten.

Der Prozess darf keine neue Backend-ID bei jedem Request erzeugen.

Eine Backendrotation ist keine Startup-Nebenwirkung und benötigt einen
separaten kontrollierten Ablauf.

## Eine Datenbankengine

Supervisorjournal, Runtime-/Artefaktkorrelation und Gatebinding verwenden
dieselbe App-Datenbankengine wie Readiness.

Es wird kein zweiter Pool und keine erneute DSN-Auswertung erzeugt.

Eine injizierte Engine bleibt extern besessen; eine aus Settings erzeugte
Engine bleibt App-eigen.

## Exakter Migrationshead

Supervisoraktivierung ist nur bei Readiness gegen exakt Head
`20260825_0033` zulässig.

Veraltetes, vorauslaufendes oder mehrdeutiges Schema bleibt not-ready.

Startup führt keine Migration, Reparatur, Adoption, Seed oder Backfill aus.

## Geschlossene Engine

Der Productionprozess konstruiert genau eine lokale geschlossene
Supervisor-Engine mit digestgebundenen Writer-/Recoveryimages.

Image-Tags, latest, Requestimages und Environment-Overrides sind unzulässig.

Netzwerk-, Mount-, Capability-, Restart- und Privilegienpolicy bleiben
konstruktiv festgelegt.

## Engineclient-Besitz

Ein vom Process erzeugter Engineclient ist process-eigen und wird beim
Lifespan-Ende geschlossen.

Ein explizit injizierter Client bleibt extern besessen und wird nicht
geschlossen.

Factoryfehler nach Clienterzeugung müssen den process-eigenen Client sofort
und genau einmal schließen.

## Private Control-Root

Das Control-Root muss absolut, process-eigen, nicht öffentlich bedient und von
Research-/Release-Artefaktroots getrennt sein.

Der Resolver darf nur bereits kontrolliert angelegte jobbezogene
Control-Directories zurückgeben.

Startup erstellt keine Jobdirectory und adoptiert keinen fremden Bestand.

## Directory-Lifecycle

Control-Directories entstehen ausschließlich im kontrollierten Prepare-
Vorlauf mit stabiler Directory-ID und sicherer Eigentümer-/Modusprüfung.

Die LQ-481-Factory selbst bleibt dateiwirkungsfrei.

Cleanup beim Shutdown ist verboten; Retention folgt persistierter
Terminalkorrelation und separater Policy.

## Capabilityprimitive

Writer- und Recoveryprimitive werden getrennt konstruktiv injiziert oder aus
explizit geschlossenen process-eigenen Implementierungen gebaut.

Es gibt keinen Command-, Modul-, Entry-Point- oder Importpfad aus Requests.

Recovery erhält keine Writer- oder Cleanupfähigkeit.

## Outcome-Policy

Inspect und bounded Wait verwenden eine positive feste Maximalzahl und eine
process-eigene Pausepolicy.

Requests können Versuche, Pause oder Timeout nicht erhöhen.

Wait-Ausschöpfung bleibt technische Unverfügbarkeit und löst keinen zweiten
Release oder Terminate aus.

## HTTP-Grenze

Production-Wiring allein fügt keine öffentliche Route hinzu.

Ein späterer Transport muss aktuelle Claim-/Owner-/Lifecyclevoraussetzungen
vor jeder Wirkung separat prüfen.

SessionPrincipal identifiziert den Actor, erteilt aber keine
Supervisorfähigkeit.

## Kein Authorityshortcut

Settings dürfen kein Allowboolean, Managementrole oder Researchpermission als
Supervisorauthority enthalten.

Persistente Handles, Artefakte und Backendinstanzen erteilen ebenfalls keine
allgemeine Authority.

Aktuelle Plattformauthority bleibt vor der Servicegrenze.

## All-or-nothing Composition

Automatisches Supervisor-Wiring darf nicht mit teilweise explizit injizierten
verwalteten Ports gemischt werden.

Entweder wird der vollständige LQ-481-Graph kontrolliert aufgebaut oder ein
vollständig expliziter Testgraph verwendet.

Halbe Persistenz-/Engine-/Filegraphen scheitern beim Factory-Aufbau.

## Aufbau bleibt wirkungsfrei

App- und Servicefactory führen keine Datenbankabfrage, Engineoperation,
Control-Dateianlage oder Capabilityausführung aus.

Readiness findet erst im Lifespan über die bestehende Probe statt.

Keine Supervisoroperation läuft beim Modulimport oder Startup automatisch.

## Readiness

Bei aktiviertem Supervisor verlangt Readiness zusätzlich zur Datenbankprobe
eine vollständig aufgebaute, aber weiterhin inerte Dependency-Composition.

Sie startet keinen Probecontainer und schreibt kein Ready-Artefakt.

Engine- oder Capability-Selbsttests mit Prozesswirkung gehören nicht in
Readiness.

## Liveness

Liveness bleibt reine Prozesslebendigkeit und hängt nicht von Datenbank,
Engine, Control-Root oder Capabilityprimitive ab.

Ein externer Ausfall darf keinen Restartsturm über die Livenessgrenze
erzwingen.

Readiness und Liveness bleiben getrennt.

## Geordneter Shutdown

Shutdown nimmt zuerst neue Supervisorwirkungen aus der Transportannahme.

Bereits persistierte Jobs werden nicht pauschal terminiert, gelöscht oder als
terminal markiert.

Danach werden nur process-eigene Clients und Pools in umgekehrter
Konstruktionsreihenfolge genau einmal geschlossen.

## Jobs über Prozessrestart

Journal, Runtimebinding, Gatebinding und Artefaktkorrelation bleiben über
Processrestart erhalten.

Startup reconciliiert Jobs nicht automatisch und erzeugt keinen Hintergrund-
Worker.

Ein späterer expliziter Request oder kontrollierter Reconciler verwendet die
LQ-475-bis-LQ-479-Restartpfade.

## Fehlergrenzen

Konfigurationsfehler nennen nur die unvollständige Feldgruppe, nie DSN, Pfad,
Digest, Backend-ID oder Engineendpoint.

Laufzeitfehler bleiben an der bestehenden detailfreien technischen Grenze.

Ein Wiringfehler aktiviert keinen Fallbackservice.

## Beobachtbarkeit

Öffentliche Startupmetadaten dürfen nur `supervisor_enabled=true|false` und
neutrale Readinessgründe enthalten.

Handles, Claims, Owner, Container-IDs, Controlpfade und Artefaktfakten werden
nicht geloggt.

Metriken dürfen keine ungebundenen Identitätslabels tragen.

## Kein Bootstrap oder Cleanup

Productionstartup erzeugt keinen Journaljob, Runtimehandle, Control-Directory,
Gatebinding oder Authorityfakt.

Shutdown löscht keinen Container oder persistenten Bestand.

Bootstrap, Recovery, Retention und Cleanup bleiben explizite getrennte
Operationen.

## Keine Implementation

LQ-482 ändert keine Settings, Appfactory, Entrypoint-, Compose- oder
Environmentdatei.

Es ergänzt keine Migration, Tabelle, SQL-, Domain- oder Portsignatur.

Head bleibt `20260825_0033` mit 33 linearen Migrationen.

## Tests

Fokussierte Vertragsprüfungen belegen opt-in All-or-nothing, Engine-/Control-
Besitz, Head-Readiness, wirkungsfreien Aufbau, getrennte Liveness, geordneten
Shutdown, Restartpersistenz, fehlende Authorityshortcuts und fehlende
Implementation.

## Nächster Slice

LQ-483 sollte die vollständige validierte Settingsgruppe und kontrollierte
Lifespan-Composition gegen diesen Vertrag implementieren.

Öffentliche Supervisorrouten bleiben weiterhin separat.
