# LQ-307 — Owner-controlled Staging Process Adapter Contract

## Zweck

LQ-307 definiert den lokalen Prozessadapter zwischen der injizierten
LQ-306-Phasengrenze und einer ausdrücklich autorisierten Docker-Compose-
Stagingumgebung.

Der Adapter erhebt genau ein redigiertes `StagingPhaseEvidence` pro Aufruf. Er
entscheidet weder die Reihenfolge noch Fortsetzung, Retry, Gesamtstatus oder
Readiness; diese Zuständigkeiten bleiben bei LQ-306 beziehungsweise LQ-304.

Dieser Slice startet noch keinen Unterprozess und verändert keine externe
Umgebung.

## Konstruktion

Der Adapter wird einmal pro autorisiertem Run aus vollständig expliziten,
absoluten Pfaden und injizierten Fähigkeiten aufgebaut.

Er erhält:

- Compose-Binary als fester absoluter Executable-Pfad;
- geprüftes Composefile;
- owner-only Runtime- und Image-Environmentdateien;
- owner-only Worker-Konfiguration, Worker-ID und Datenbank-URL;
- read-only synthetisches Dataset und privates Artifactvolumeziel;
- feste Compose-Projekt-ID aus der validierten Run-ID;
- injizierten Prozessaufruf, monotone Clock und begrenzten Output-Digester;
- ausschließlich opake Evidence-Referenzgeneratoren.

Kein Wert wird aus Arbeitsverzeichnis, PATH, HOME, Benutzerprofil, Gitconfig,
Dockercontext, Default-Composefile oder Prozessumgebung abgeleitet.

## Geschlossene Prozessumgebung

Jeder Unterprozess erhält eine neu aufgebaute allowlistete Umgebung.

Erlaubt sind nur notwendige locale-neutrale Werte und die explizit gebundene
Docker-Verbindungsidentität. Secret-, DSN-, Proxy-, Registry-Credential-,
Python-, Shell-, Git-, SSH-, Cloud- und Compose-Overridevariablen werden nicht
geerbt.

Environmentdateien werden ausschließlich über feste Argumente an Compose
gereicht. Ihre Inhalte werden weder in die Prozessumgebung kopiert noch vom
Adapter geparst oder protokolliert.

## Prozessaufruf

Kommandos sind unveränderliche Argumentlisten. `shell=True`, Shellstrings,
Commandsubstitution, Pipes, Redirects, Globs und dynamisch erzeugte
Executable-Namen sind verboten.

stdin ist geschlossen. stdout und stderr sind getrennte begrenzte Bytekanäle.
Der Prozess startet in einem festen leeren owner-kontrollierten
Arbeitsverzeichnis und erhält pro Phase eine feste Timeoutpolicy.

Timeout beendet zuerst kontrolliert genau den gestarteten Prozess. Unklarer
Effekt, verlorener Output oder notwendiger harter Kill ergibt `unavailable`,
niemals `passed`.

## Run-Bindung

Jeder Compose-Aufruf enthält explizit:

- beide `--env-file`-Argumente;
- `--file` mit dem gebundenen Composefile;
- `--project-name` mit einer ausschließlich aus der validierten Run-ID
  abgeleiteten opaken Projekt-ID;
- den festen Subcommand und eine feste Service-Allowlist.

Der Adapter akzeptiert keine zusätzlichen caller-gelieferten Composeargumente,
Profile, Services, Scale-Werte, Buildoptionen oder Pullpolicy.

Container-, Netzwerk- und Volume-Namen außerhalb der Projekt-ID sind kein
zulässiges Ziel.

## Phasenabbildung

Der Adapter besitzt eine totale geschlossene Abbildung für exakt die 29
LQ-306-Phasennamen.

Read-only Phasen verwenden ausschließlich Imageinspect, Compose-Render,
Containerinspect oder fest definierte detailarme Prüfkommandos.

Mutierende Phasen sind auf die in LQ-305 erlaubten Aktionen beschränkt:
gebundene Images pullen, dedizierte Datenbank bereitstellen, Migration-Gate
einmal starten, genau einen Worker starten, synthetische bestehende
Control-Plane-Grenzen auslösen, genau eine Testpermission entziehen und
dedizierte Prozesse kontrolliert stoppen.

Ein unbekannter Phasenname erzeugt vor Prozessstart `unavailable`.

Der Adapter führt keine Phase implizit als Voraussetzung einer anderen aus.

## Output-Reduktion

Rohoutput wird nie persistiert und nie an LQ-306 zurückgegeben.

Jede Phase besitzt ein geschlossenes Ausgabeschema mit maximaler Bytegröße.
Parser akzeptieren nur die benötigten neutralen Fakten, beispielsweise
Exitcode, Digestgleichheit, UID/GID, Modusklasse, Migration-Head,
Zählerrelation oder kontrollierten Stopstatus.

Unbekannte Schlüssel, zusätzliche Zeilen, ungültiges Encoding, abgeschnittener
Output, private Werte oder nicht kanonische Darstellung ergeben
`unavailable`.

Ein beobachteter eindeutiger Invariantenbruch ergibt `failed`. Technische
Mehrdeutigkeit ergibt `unavailable`.

## Evidence-Objekte

Nach erfolgreicher Reduktion erzeugt der Adapter ein separates kanonisches
Evidenceobjekt mit ausschließlich phasenspezifischen neutralen Fakten.

Das Objekt wird privat und atomar unter dem rungebundenen Evidenceziel
gespeichert. Erst nach Fsync und SHA-256-Read-back liefert der Adapter
`passed` oder `failed` mit opaker Referenz und Digest.

`unavailable` erzeugt kein scheinbares Evidenceobjekt und liefert Referenz
sowie Digest exakt `None`.

Bestehende Objekte werden niemals ersetzt. Derselbe Phasenaufruf ist nicht
automatisch wiederholbar.

## Secret- und Detailgrenze

Der Adapter darf niemals DSN, Datenbank-URL-Dateipfad, Secretinhalt,
Environmentinhalt, Hostpfad, Containerinspect-Rohdaten, Datasetpfad,
Job-/Claim-/Actor-/Workspace-ID, Artifactinhalt oder Unterprozessfehler in
Evidence, Exception, `repr`, stdout oder stderr aufnehmen.

Öffentlich beobachtbar bleiben ausschließlich stabiler Exceptioncode oder das
detailarme `StagingPhaseEvidence`.

## Signalgrenze

Die Phasen `idle_sigterm` und `running_sigterm` senden genau ein SIGTERM an den
rungebundenen Workercontainer.

Der Adapter prüft Stopzeit und Exitstatus read-only. Er sendet kein zweites
SIGTERM und wertet SIGKILL niemals erfolgreich.

Ein erforderlicher Recovery- oder Cleanupschritt wird nicht innerhalb dieser
Phasen erfunden. Unbekannter Stopstatus bleibt `unavailable`.

## Ressourcenbesitz

Der Adapter besitzt nur selbst gestartete kurzlebige Prüfprozesse und von ihm
neu erzeugte Evidenceobjekte.

Docker-Daemon, Stagingdatenbank, Images, Compose-Ressourcen, Dataset,
Artifactvolume und Inputdateien bleiben extern besessen.

Es gibt kein automatisches `compose down`, Volume-/Netzwerkprune,
Imageentfernen, Datenbankdrop oder Artifactcleanup.

## Nichtziele

LQ-307 entscheidet keine konkrete Subprocessklasse, Docker-API-Bibliothek,
plattformabhängige Secret-Mount-Implementierung, SQL-Abfrage, HTTP-Testclient-
Implementierung, Timeoutzahl oder Evidence-Dateinamen.

Es gibt keine CLI, kein Production-Wiring und keine Schema-, Tabellen-, SQL-,
Migration-, Port-, Domainmodell- oder Composeänderung.

Es werden keine realen Unterprozesse, Container, Datenbanken, Jobs, Signale
oder Netzwerkzugriffe ausgeführt.

## Implementierungsfolge

LQ-308 sollte den Adapter mit einer injizierten argv-basierten ProcessRunner-
Grenze, geschlossener Umgebung, begrenztem Capture und neutralen
phasenspezifischen Parsern implementieren.

Ein realer Run bleibt auch danach eine separate ausdrücklich autorisierte
Operation und darf nicht als Nebeneffekt der Tests gestartet werden.
