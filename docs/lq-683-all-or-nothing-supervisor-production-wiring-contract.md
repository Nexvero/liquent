# LQ-683 — All-or-nothing Supervisor Production Wiring Contract

## Ziel

Dieser Vertrag begrenzt die spätere Productionauswahl des terminal vollständigen
Manifest-Handoff-Supervisorkandidaten.

Eine Settingsangabe allein, ein einzelner Adapter oder ein Compose-Mount darf
niemals Productionbereitschaft erzeugen.

## Exklusive Auswahl

Ein Prozess wählt entweder den vollständigen Kandidatenpfad oder keinen
Supervisorpfad.

Bei Kandidatenauswahl darf der ältere Parent-Capability-Executorgraph weder
komponiert noch als Fallback erreichbar sein.

Partielle Mischung von Prepare, Release, Child, Terminal oder Reconciliation
zwischen beiden Graphen ist verboten.

## Gemeinsame Eigentümerschaft

Die auswählende Prozesscomposition muss gemeinsam besitzen:

- genau einen lokalen Docker-Engine-Client
- genau eine persistente Journal-, Runtime- und Gate-Adapterfamilie
- genau einen Control-Directory-Resolver und dessen feste Hostwurzel
- genau den vollständigen Kandidatengraphen
- genau einen Healthbeitrag für diese Auswahl

Die Datenbank-Engine bleibt gemäß ihrer äußeren Appfactory-Eigentümerschaft
geteilt oder app-eigen, darf aber nicht unbemerkt dupliziert werden.

## Konstruktive Fähigkeiten

Der Docker-Socket, die Control-Wurzel und erforderliche Hostpfade stammen nur
aus kontrollierter Prozess- und Deploymentkonfiguration.

Requestdaten, frei gelieferte Pfade, Rollen oder Allowbooleans dürfen weder
Enginezugriff noch Mountfähigkeit erzeugen.

Die beiden Wrappercommands bleiben fest und profilgebunden.

## Readiness

Readiness darf erst nach erfolgreicher vollständiger Composition positiv sein.

Fehlt eine Abhängigkeit, ist die Auswahl unbekannt oder schlägt die Composition
fehl, startet kein teilweiser Kandidatengraph.

Ein später technisch unverfügbarer Supervisorbeitrag macht den Prozess
detailfrei not-ready; er öffnet keinen Kompatibilitätsfallback.

## Shutdown

Shutdown markiert Health zuerst als stopping und schließt danach den einmalig
besessenen Docker-Client.

Er beendet keine fremd besessene Datenbank-Engine und erzeugt keine neue
Capabilitywirkung.

Close ist höchstens einmal wirksam; Fehler bleiben detailfrei und ändern keine
bereits persistierten terminalen Fakten.

## Nicht Teil dieses Slices

Keine Settings-, Appfactory-, Compose-, Socket-, Schema-, SQL-, Port-, Modell-,
Signatur-, Migration-, CLI- oder Productionaktivierung wird umgesetzt.
