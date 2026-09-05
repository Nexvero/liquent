# LQ-691 — Process-owned Supervisor Composition Contract

## Ziel

Die vollständige LQ-687-Settingsgruppe wird in genau einen inert aufgebauten,
exklusiven Kandidatenprozess übersetzt.

## Eingaben

Die Composition akzeptiert ausschließlich validierte `PlatformSettings`, eine
extern besessene SQLAlchemy-Engine, eine typisierte Backend-Instanz-ID und
kontrollierte Clocks.

Unvollständige Settings oder falsche Abhängigkeitstypen scheitern detailfrei vor
operativem I/O.

## Einmalige Abhängigkeiten

Je Prozess entstehen genau einmal:

- persistentes Journal
- persistente Runtime- und Gate-Bindings
- persistente Control-Directory-Registry
- sicherer lokaler Directoryresolver
- atomare Control-Artefaktgrenze
- numerische Launch-Identitypolicy
- lokaler Docker-Engine-Client
- exklusiver Kandidatengraph

## Eigentümerschaft

Das zurückgegebene Prozessobjekt besitzt ausschließlich den neu erzeugten
Docker-Client.

Die Datenbank-Engine bleibt beim äußeren Appfactorybesitzer und wird weder bei
normalem Close noch nach Compositionfehler disponiert.

## Exklusivität

Der Docker-Client ist nur Parent-Engine des Kandidaten.

Der Compatibilitygraph, Parent-Capability-Executor und Parent-Outcomes werden
nicht importiert oder komponiert.

## Inertheit

Konstruktion öffnet keinen Socket, liest keine Datei und greift nicht auf die
Datenbank zu.

Dateisystem- und Persistenzvalidierung erfolgen erst bei einer späteren
fachlichen Operation.

## Productionstatus

Das Prozessobjekt bleibt unveränderlich `production_ready=false`.

Keine Appfactory-, Lifecycle- oder Deploymentauswahl wird getroffen.
