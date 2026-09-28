# LQ-457 — Docker Engine Supervisor Process and Gate Primitive Decision

## 1. Ergebnis

LQ-457 wählt für die lokale Productiongrenze einen dedizierten Linux-Docker-
Engine-Adapter mit einem Container je Journaljob.

Ein privates dauerhaftes Control-Directory bildet Gate- und Resultatprimitive.

Der Slice implementiert noch keinen Adapter oder Containerwrapper.

## 2. Warum Docker Engine

Die Engine besitzt Container unabhängig vom anfragenden Serviceclient.

Container können über eine runtime-eigene ID inspiziert, gestartet, gewartet
und beendet werden.

Damit wird kein `Popen`-Objekt oder PID zum stabilen Handle.

Enginebestand bleibt trotzdem technische Infrastruktur, nicht Authority.

## 3. Unterstützte Plattform

Die Productionentscheidung gilt ausschließlich für kontrollierte Linux-Hosts
mit lokalem Docker Engine Daemon.

Docker Desktop, Remote Daemons, Windows Container und rootlose Varianten sind
nicht automatisch freigegeben.

Außerhalb des belegten Profils scheitert Composition beim Aufbau.

Es gibt keinen Popen-, systemd- oder Threadfallback.

## 4. Lokaler Engine-Endpunkt

Nur ein konstruktiv konfigurierter lokaler Engine-Endpunkt ist zulässig.

Requests dürfen weder Socket, Host, Context noch TLS-Ziel auswählen.

Remote Daemons sind ausgeschlossen, weil Bind-Mount-Pfade auf dem Daemonhost
liegen und nicht auf dem Clienthost.

Enginezugriff bleibt ausschließlich beim Supervisorservice.

## 5. Engineprivileg

Zugriff auf die Docker Engine ist hochprivilegiert.

Nur der minimale Supervisorservice erhält ihn.

Kindcontainer erhalten weder Engine-Socket noch Dockercredentials.

Anwendungscontroller sprechen niemals direkt mit der Engine.

## 6. Runtime-Binding

Der Supervisor erzeugt genau einen Container und bindet dessen unveränderliche
Engine-Container-ID an Backendinstanz, Journalhandle und Launch-Commit.

Die Container-ID ist nicht der öffentliche LQ-446-Handle.

Diese Runtimebindung muss vor bestätigtem Spawnresultat durable sein.

Name oder Label allein ersetzen die Container-ID nicht.

## 7. Idempotente Containeranlage

Der Adapter verwendet eine deterministische intern kontrollierte
Creation-Identity aus der bereits persistenten Jobbindung.

Nach Create-Unknown wird ausschließlich nach dieser Identity und den festen
Labels inspiziert.

Ein passender Bestand muss exakt Image, Mounts, Netzwerk-, User- und
Capabilityprofil erfüllen.

Abweichung ist Konflikt; ein zweiter Container wird nicht erzeugt.

## 8. Kein automatischer Restart

Restartpolicy ist zwingend `no`.

`always`, `unless-stopped` und `on-failure` sind verboten, weil sie denselben
Capabilitycode nach Prozessende erneut ausführen könnten.

Der Supervisor startet einen erstellten Container genau einmal.

Daemon- oder Hostrestart autorisiert keinen Containerneustart.

## 9. Kein Auto-Remove

Container werden nicht mit Auto-Remove beziehungsweise `--rm` angelegt.

Der terminale Runtimezustand muss nach Client- und Serviceneustart inspizierbar
bleiben.

Entfernung ist erst nach persistierter Terminalkorrelation und separater
Cleanupentscheidung zulässig.

Containerabwesenheit eines erwarteten Jobs ist kein Endnachweis.

## 10. Gepinntes Image

Writer-/Recoverywrapper laufen aus einem kontrollierten unveränderlich per
Digest gebundenen Image.

Tags allein sind unzulässig.

Image-Digest und festes Prozessprofil werden beim Serviceaufbau validiert.

Ein Request kann Image oder Entrypoint nicht überschreiben.

## 11. Fester Entrypoint

Der Containerentrypoint ist ausschließlich der kontrollierte Gatewrapper.

Command und Args werden aus festen capabilityspezifischen Profilen aufgebaut.

Es gibt keine Shellinterpolation.

Writer und Recovery verwenden getrennte Profile.

## 12. Mountprofil Writer

Der Writer erhält Source ausschließlich read-only.

Target erhält nur die für LQ-426 erforderliche Schreibfähigkeit.

Das private Control-Directory wird an einen festen internen Pfad gemountet.

Andere Hostpfade und der Engine-Socket bleiben ungemountet.

## 13. Mountprofil Recovery

Recovery erhält Target ausschließlich read-only und kein Source-Mount.

Das Control-Directory darf nur seine Gate- und Resultatartefakte verändern.

Der Reconciler erhält keine Writer- oder Cleanupfähigkeit.

Mountprofile sind nicht caller-konfigurierbar.

## 14. Privates Control-Directory

Jeder Job besitzt ein nicht wiederverwendbares privates Control-Directory auf
dem Dockerhost.

Es ist an Backendinstanz, Handle und Runtimebinding gekoppelt.

Der Pfad wird nicht aus untrusted Namen zusammengesetzt und nicht ausgegeben.

Verzeichnis und Artefakte benötigen sichere Eigentümer- und Modusprüfung.

## 15. Gateartefakte

Das Control-Directory enthält ausschließlich geschlossene versionierte
Artefaktrollen:

- Wrapper-ready mit Jobbinding;
- unveränderliches Release-Token mit Release-ID;
- unveränderliches Release-consumed-Ack;
- begrenztes terminales Resultatenvelope.

Temporäre Schreibdateien sind keine gültigen Fakten.

## 16. Durable Writes

Jedes gültige Artefakt wird über private temporäre Datei, vollständigen Write,
Dateisynchronisation, atomare No-replace-Veröffentlichung und
Verzeichnissynchronisation gesichert.

Eine vorhandene Zielrolle wird nie überschrieben.

Exakter Retry vergleicht vollständige Bytes.

Divergenz bleibt Konflikt.

## 17. Wrapper-ready

Nach Containerstart validiert der Wrapper seine feste Jobbinding und
veröffentlicht Wrapper-ready.

Der Supervisor bestätigt `prepared_gated` erst nach Engine-Running und exakt
passendem Ready-Artefakt.

Engine-Running allein genügt nicht.

Vor Ready lädt der Wrapper keinen Capabilitycode.

## 18. Release-Token

Nach persistentem LQ-455-Release-Commit veröffentlicht der Service genau ein
Token mit derselben Release-ID.

Der Wrapper akzeptiert ausschließlich diese geschlossene Rolle und seine
eigene Jobbinding.

Ein anderes oder beschädigtes Token wird nicht konsumiert.

Tokenabwesenheit lässt den Wrapper gated.

## 19. Consumed-Ack

Vor Capabilitycode veröffentlicht der Wrapper ein unveränderliches
Consumed-Ack für dieselbe Release-ID.

Erst danach importiert oder startet er Writer beziehungsweise Reconciler.

Der Supervisor appendiert Running erst nach Token-/Ack-Übereinstimmung und
direkter Engine-Running-Beobachtung.

Ein Ack ohne passenden Release-Commit ist technische Unverfügbarkeit.

## 20. Release-Unknown

Nach Servicecrash werden Journal-Release, Token, Ack und Enginezustand
read-only korreliert.

Dasselbe Token darf mit identischen Bytes idempotent wieder aufgelöst werden.

Es gibt weder zweite Release-ID noch zweiten Container.

Mehrdeutiger Artefaktbestand bleibt fail-closed.

## 21. Terminalbeobachtung

Docker Engine `exited` oder `dead` für die exakt gebundene Container-ID belegt,
dass dieser Containerprozess nicht weiterwirkt.

Ein valides Resultatenvelope liefert das geschlossene direkte Outcome.

Runtime-Terminalzustand plus fehlendes oder ungültiges Envelope wird
konservativ terminal unknown/unavailable.

Exitcode allein erzeugt keinen fachlichen Erfolg.

## 22. Erwarteter Container fehlt

Kann die Engine die persistierte Container-ID nicht auflösen, ist der Ausgang
technisch unverfügbar.

Der Service erfindet weder Terminalität noch nie erfolgten Start.

Name, Label, PID oder Dateiartefakte dürfen keinen Ersatzcontainer adoptieren.

Recovery bleibt gesperrt.

## 23. Engineausfall

Nicht erreichbare Engine ist detailfreie technische Unverfügbarkeit.

Service und Plattform starten keinen Ersatzprozess außerhalb der Engine.

Live-Restore kann Verfügbarkeit verbessern, ist aber keine Sicherheitsannahme.

Nach Wiederkehr wird dieselbe Container-ID inspiziert.

## 24. Daemonrestart

Automatische Containerrestartpolicy bleibt deaktiviert.

Ein weiterhin laufender Container kann nur anhand derselben Runtimebinding
weiter beobachtet werden.

Kann die Engine ihre Bindung nicht wiederherstellen, bleibt der Job fail-closed.

Der Service ruft nicht blind `start` erneut auf.

## 25. Netzwerk

Writer- und Recoverycontainer erhalten standardmäßig kein Netzwerk.

Sie benötigen weder Registry-, Datenbank-, OIDC- noch Providerzugriff.

DNS- und Portfreigaben sind nicht Teil des Requests.

Eine spätere Ausnahme wäre ein eigener Vertrag.

## 26. Benutzer und Privilegien

Container laufen als feste nicht-root Useridentität.

Linux-Capabilities werden vollständig entfernt, soweit das belegte Profil
keine einzelne feste Ausnahme erfordert.

Privileged, Host-PID, Host-Network und zusätzliche Devices sind verboten.

Rootfilesystem ist read-only außer explizit begrenzten Mounts.

## 27. Ressourcenlimits

CPU, Speicher, PIDs, Output und Laufzeit besitzen feste Servicepolicygrenzen.

Containerlogging wird begrenzt und ist kein Resultatkanal.

Limitüberschreitung löst kontrollierte Terminierung aus.

Sie beweist erst mit Runtime-Terminalzustand das Ende.

## 28. Terminierung

Nach durablem Terminate-Journalfakt adressiert der Service ausschließlich die
persistierte Container-ID.

Stop/Kill-Annahme ist nicht terminal.

Der Service wartet weiter auf direkten Runtime-Terminalzustand.

Ein neuer Containerstart bleibt verboten.

## 29. Retention und Cleanup

Container, Runtimebinding und Control-Artefakte bleiben mindestens bis zur
persistierten Plattform-Terminalkorrelation erhalten.

Entfernung ist ein separater owner-kontrollierter Cleanup-Slice.

IDs und Terminalfakten werden nicht wiederverwendet.

Eine konkrete Frist bleibt separat.

## 30. Neutrale Abwesenheit

Eine nie angelegte Creation-Identity kann neutral fehlen, wenn die Engine ihre
Nichtwirkung autoritativ bestätigt.

Ein erwarteter fehlender Container oder beschädigtes Control-Directory ist
nicht neutral.

Neutralität autorisiert keinen zweiten Create mit neuer ID.

Fremder Bestand wird ohne Details abgelehnt.

## 31. Detailfreie Fehler

Engine-, Mount-, Image-, Runtimebinding-, Artefakt- und Terminaldivergenz bleibt
detailfreie technische Unverfügbarkeit oder detailfreier Konflikt gemäß
bestehender Grenze.

Socket-, Host-, Container-, Image-, Pfad- und PIDdetails verlassen die Grenze
nicht.

LQ-457 benennt keinen neuen Exceptiontyp.

## 32. Keine Implementation

LQ-457 ergänzt keine Typen, Ports, Tabellen, Migrationen oder Adapter.

Head bleibt `20260824_0031` mit 31 linearen Migrationen.

Es erstellt kein Image, Verzeichnis oder Container und spricht keine Engine an.

Es gibt kein CLI-, Compose-, CI-, Deployment- oder Production-Wiring.

## 33. Tests

Fokussierte statische Tests belegen lokale Linux-Enginebindung, keine
Restartpolicy/Auto-Remove, digest-gepinntes Image, getrennte Mountprofile,
durable Token-/Ack-Gatefolge, Runtime-Terminalbeobachtung, fail-closed fehlenden
Container und fehlende Implementation.

## 34. Nichtziele

LQ-457 implementiert keinen Engineclient, Wrapper, Artefaktcodec,
Runtimebindingstore oder Serviceprozess.

Plattformintegration, Bestand, Cleanup und Retention bleiben separat.

## 35. Nächster Slice

LQ-458 sollte die persistente Foundation für Engine-Runtimebinding und private
Control-Artefaktidentitäten schaffen.

Geschlossene Runtime-/Artefakttypen und Adapter folgen danach separat.
