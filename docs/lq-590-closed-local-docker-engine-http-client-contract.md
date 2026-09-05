# LQ-590 — Closed Local Docker Engine HTTP Client Contract

## Ergebnis

LQ-590 definiert die konkrete processfähige Clientgrenze unterhalb des
LQ-462-Supervisor-Engineadapters.

Der Slice öffnet noch keinen Socket und aktiviert kein Production-Wiring.

## Genau ein lokaler Daemon

Der Client wird konstruktiv an genau einen absoluten Unix-Socketpfad gebunden.

TCP, TLS, SSH, Context, Remotehost und Environmentauflösung sind unzulässig.

`DOCKER_HOST`, Benutzerkonfiguration und aktueller CLI-Context werden nicht
ausgewertet.

Der Socketpfad ist kein Requestwert und erscheint in keinem Ergebnis.

## Feste API-Version

Die Docker-API-Version ist beim Aufbau eine feste unterstützte Konstante.

Es gibt keine automatische Versionsermittlung und keinen unversionierten
Fallback.

Ein Daemon mit inkompatibler API bleibt technisch unverfügbar.

## Geschlossene Operationen

Der Client implementiert ausschließlich Find, Create, Inspect, Start, Wait,
Stop und Kill für den LQ-462-Adapter.

Remove, Exec, Attach, Logs, Pull, Build, Network-, Volume- und Imageverwaltung
sind nicht Teil der Grenze.

Caller können weder HTTP-Methode noch Pfad oder Query frei bestimmen.

## Find

Find akzeptiert ausschließlich die vom Adapter gebildete exakte Labelmap.

Sie wird kanonisch als Docker-Filter codiert.

Die Antwort wird auf eine begrenzte Liste geschlossener Containeransichten
übersetzt.

Unbekannte, übergroße oder strukturell abweichende Antworten scheitern
fail-closed.

## Create

Create akzeptiert ausschließlich die geschlossene LQ-462-Spezifikation.

Der Client materialisiert daraus ein festes Writer- oder Recoveryprofil.

Entrypoint, Command, User, Mounts und Ressourcenpolicy stammen ausschließlich
aus der konstruktiven Clientkonfiguration.

Requestdaten können diese Werte weder hinzufügen noch überschreiben.

## Keine Imagebeschaffung

Create verwendet ausschließlich den bereits digestgebundenen Imagewert.

Der Client pullt, baut, taggt oder sucht kein Image.

Fehlender lokaler Imagebestand bleibt technische Unverfügbarkeit.

## Control-Directory-Mount

Die interne Directory-ID wird über den persistenten read-only Resolver auf
genau einen bereits aktivierten privaten Hostpfad gebunden.

Writer und Recovery erhalten nur ihr festes Control-Mountprofil.

Ein Caller liefert keinen Hostpfad, Zielmount oder Mountmodus.

Der Client erstellt, adoptiert oder retired kein Directory.

## Sicherheitsprofil

NetworkMode bleibt `none`, RestartPolicy `no` und AutoRemove false.

Rootfilesystem bleibt read-only, Privileged false und alle Capabilities werden
entzogen.

PID-, IPC- und Userpolicy sind feste profilbezogene Clientkonfiguration.

Unsichere oder unvollständige Werte werden nicht normalisiert.

## Antwortübersetzung

Rohantworten werden ausschließlich in die vom LQ-462-Adapter erwarteten
neutralen Maps übersetzt.

Container-ID, Image-Digest, interne Labels, geschlossener Zustand und exakt
die prüfbaren Sicherheitswerte werden rekonstruiert.

Namen, PID, Exitcode, Hostdetails und fremde Labels verlassen den Client nicht.

## Inspect und Wait

Inspect adressiert genau eine intern gebundene Container-ID.

Autoritatives HTTP-Not-Found darf ausschließlich als neutrales `None` an die
private Clientgrenze zurückkehren.

Wait besitzt eine feste positive Zeitgrenze und liefert nur eine vollständig
übersetzbare Terminalansicht.

Timeout ist technische Unverfügbarkeit und keine Terminalität.

## Start, Stop und Kill

Start, Stop und Kill adressieren ausschließlich dieselbe gebundene ID.

Stop verwendet eine feste positive Grace-Dauer.

Kill verwendet ein festes Signal und keinen caller-supplied Wert.

HTTP-Annahme behauptet weder Running noch Terminalität.

## Statusgrenzen

Jede Operation besitzt eine exakte kleine Allowlist akzeptierter HTTP-Status.

Andere Statuswerte, Redirects, Proxyantworten und Authchallenges scheitern
detailfrei.

Antwortbody und Header werden nicht in Fehler übernommen.

## Größen- und Zeitgrenzen

Connect, Read, Write und Pool besitzen feste positive Obergrenzen.

JSON- und Listenantworten besitzen feste Byte- und Elementgrenzen.

Eine Warteantwort darf diese Grenzen nicht durch Streaming umgehen.

## Ressourcenbesitz

Der process-eigene HTTP-Transport wird genau einmal vom Client besessen.

`close()` ist idempotent und verhindert spätere Operationen.

Jede Response wird auch bei Decode-, Status- oder Übersetzungsfehlern
geschlossen.

Factoryfehler nach Transporterzeugung schließen ihn sofort.

## Wirkungsloser Aufbau

Der Konstruktor öffnet keinen Socket und führt keinen Ping aus.

Es gibt keine API-Versionsermittlung, Directoryauflösung oder Imageprüfung beim
Aufbau.

Die erste explizite Clientoperation ist die erste mögliche I/O-Wirkung.

## Fehlergrenze

Transport-, Socket-, Timeout-, Status-, Größen-, Decode- und
Übersetzungsfehler werden über die bestehende detailfreie technische Grenze
vereinheitlicht.

LQ-590 benennt keinen neuen Exceptiontyp.

Fehler enthalten weder Socket, Container-ID, Digest, Label noch Daemontext.

## Keine Authority

Der Client akzeptiert keine Session, Nutzer-, Workspace-, Rollen-, Permission-
oder Allowentscheidung.

Enginezugriff ist Infrastrukturzugriff und erteilt keine fachliche
Supervisorauthority.

Journal-, Claim-, Owner- und Lifecycleprüfung bleiben vor dem Adapteraufruf.

## Keine Productionaktivierung

LQ-590 ergänzt keine Dependency, Quellimplementation, Settings, Appfactory,
Route, Composegruppe, Socketmount oder Environmentvariable.

Es ergänzt keine Migration, Tabelle, SQL-, Domain- oder Portsignatur.

Head bleibt `20260826_0042` mit 42 linearen Migrationen.

## Nächster Slice

LQ-591 implementiert den geschlossenen Unix-Socket-HTTP-Client gegen diesen
Vertrag mit injizierbarem Transport und vollständigen Übersetzungstests.
