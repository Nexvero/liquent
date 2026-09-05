# LQ-269 — Owner-only Package-Index Credential and Local Composition

## Ergebnis

LQ-269 implementiert die lokale, vollständig besessene Dependency-Gruppe für
den in LQ-267 und LQ-268 eingefrorenen Package-Index-Provider.

Der Slice liest genau ein lokales Credential aus einer abgesicherten Datei,
erzeugt genau einen kontrollierten synchronen HTTP-Client und komponiert daraus
den bestehenden HTTPS-Transport und Publication-Adapter.

Es erfolgt keine Verdrahtung in CLI, Worker oder Production-Startup.

## Credential-Quelle

`OwnerOnlyPackageIndexCredentialSource` erhält ausschließlich einen absoluten
lokalen Pfad.

Der Pfad und das geladene Credential sind private Werte und erscheinen weder
in `repr` noch in Fehlern oder Resultaten.

Die Quelle besitzt genau eine Operation: `load_credential`.

Sie kann keine Credentials erzeugen, erneuern, rotieren, widerrufen oder an
einen Provider übertragen.

## Sicheres Öffnen

Die Datei wird read-only mit `O_NOFOLLOW` und `O_CLOEXEC` geöffnet.

Fehlt auf der Laufzeitplattform eine dieser Sicherheitsoptionen, scheitert das
Laden fail-closed.

`O_NOFOLLOW` verhindert, dass die finale Pfadkomponente als symbolischer Link
auf ein anderes Ziel aufgelöst wird.

Die Prüfung erfolgt anhand des geöffneten File-Descriptors über `fstat`, nicht
anhand separater vorangestellter Pfadmetadaten.

Damit bindet sich die Entscheidung an genau das tatsächlich geöffnete Objekt.

## Zulässiges Dateiobjekt

Akzeptiert wird ausschließlich eine reguläre Datei.

Verzeichnisse, Symlinks, Geräte, Pipes, Sockets und andere Dateitypen werden
abgelehnt.

Die Datei muss dem effektiven Prozessnutzer gehören und genau einen Hardlink
besitzen.

Damit kann ein zweiter Dateiname nicht unbemerkt dasselbe Credential-Material
adressieren.

## Owner-only Modus

Zulässig sind ausschließlich die Modi `0400` und `0600`.

Der Eigentümer darf das Credential lesen und optional schreiben. Gruppen- und
sonstige Rechte sowie Execute-Rechte sind immer unzulässig.

Eine großzügigere Prozess-Umask ersetzt diese Prüfung nicht; entscheidend sind
die aktuellen Rechte des geöffneten Dateiobjekts.

## Begrenzter Inhalt

Das eigentliche Credential ist auf 4096 UTF-8-Bytes begrenzt.

Die Datei darf zusätzlich genau ein abschließendes LF für übliche Secret-File-
Bereitstellung enthalten. Dieses LF wird entfernt und ist kein Bestandteil des
Credentials.

Leerer Inhalt, zusätzliche Zeilen, CRLF, führender oder nachlaufender
Whitespace, Steuerzeichen, ungültiges UTF-8 und Oversize werden abgelehnt.

Danach wird das Credential erneut durch die bestehende
`PackageIndexProviderConfiguration` validiert.

Es gibt keine Normalisierung, Trimmung oder Teilverwendung anderer Inhalte.

## Descriptor-Lebenszyklus

Der File-Descriptor wird nach jedem Ladeversuch geschlossen.

Das gilt für Erfolg ebenso wie für Metadaten-, Größen-, Decode- und
Validierungsfehler.

Ein Fehler beim abschließenden Close legt weder Pfad noch Credential offen.

## Vollständige lokale Composition

`compose_package_index_publication` erhält explizit:

- den kanonischen HTTPS-Origin;
- den festen Zielnamen;
- den absoluten Credential-Pfad;
- die bestehende begrenzte HTTP-Policy;
- optional eine Monotonie-Uhr und eine testbare Client-Factory.

Die Composition liest das Credential einmal und baut daraus genau eine
`PackageIndexProviderConfiguration`.

Sie erzeugt anschließend genau einen `HttpPackageIndexProviderTransport` und
genau einen `PackageIndexReleasePublicationAdapter`.

Origin, Ziel und Credential stammen damit aus derselben lokalen
Dependency-Gruppe und können nicht pro Publication-Aufruf ausgetauscht werden.

## Kontrollierter HTTP-Client

Der Client wird mit deaktivierter Environment-Auswertung
(`trust_env=False`) erzeugt.

Proxy-, Zertifikats- oder Authentication-Werte aus ungeprüften
Prozessvariablen verändern dadurch nicht unbemerkt die Providergrenze.

Automatische Redirects sind auch auf Clientebene deaktiviert.

Die Connection-Pool-Grenze ist auf eine Verbindung und eine Keep-alive-
Verbindung begrenzt. Die Keep-alive-Frist beträgt fünf Sekunden.

Requestbezogene Timeouts, Größen, Authentisierung, Cookie-Entfernung und
Einzelversuch-Semantik bleiben weiterhin Aufgabe des LQ-268-Transports.

## Ressourcenbesitz

`PackageIndexPublicationComposition` besitzt den erzeugten HTTP-Client.

Sie stellt nach außen ausschließlich den fertig konfigurierten Publication-
Adapter und einen idempotenten `close`-Lebenszyklus bereit.

Die Composition kann als Context Manager verwendet werden. Beim Verlassen wird
der Client auch nach einem Fehler geschlossen.

Scheitert der Aufbau nach der Client-Erzeugung, wird der teilweise erzeugte
Client ebenfalls geschlossen.

Der Adapter selbst besitzt oder schließt keine Ressource.

## Kein Netzwerk beim Aufbau

Der Aufbau liest ausschließlich die lokale Credential-Datei.

Er führt keinen DNS-, TLS-, Provider-, Datenbank- oder Discovery-Zugriff aus.

Ein Providerzugriff entsteht erst durch einen späteren expliziten Aufruf des
komponierten Adapters.

## Fehlergrenze

Datei-, Rechte-, Eigentümer-, Link-, Größen-, Decode-, Credential- und
Client-Aufbaufehler erscheinen als bestehende detailfreie
`ReleasePublicationProviderUnavailable`.

Der Slice führt keinen neuen Exception-Typ ein.

Statische ungültige Origin-, Ziel- und Policywerte bleiben lokale
Konfigurationsfehler und werden nicht als Providerantwort interpretiert.

Keine Exception enthält Credential, Pfad, Provider-Origin oder interne
Clientdetails.

## Bewusst nicht enthalten

LQ-269 ergänzt insbesondere keine:

- CLI- oder Worker-Aktivierung;
- Production-Startup- oder App-Verdrahtung;
- Environment-Variable für Credential, Origin oder Ziel;
- Credential-Erzeugung, Rotation oder Remote-Secret-Integration;
- Provider-Discovery, Mirror-Auswahl oder Fallbacklogik;
- fachliche Publication-, Retry- oder Reconciliation-Entscheidung;
- Datenbank-, Schema-, SQL-, Migration- oder Portänderung;
- echte Provider-, Git- oder Deploymentmutation.

Der Migration-Head bleibt `20260819_0024` mit 24 Migrationen.

## Verifikation

Die Tests verwenden ausschließlich lokale Dateien und `MockTransport`.

Sie decken sichere Modi, Symlink- und Dateitypablehnung, Inhalt- und
Größenbegrenzung, detailfreie Fehler, eingeschränkte Client-Erzeugung,
I/O-freien Aufbau und vollständigen Clientabschluss ab.

Die bestehenden Adapter- und HTTPS-Transporttests bleiben unverändert gültig.

## Nächster Slice

LQ-270 definiert die kontrollierte Offline-Worker-Grenze, welche die
Composition explizit öffnet, genau eine persistente Publication-Arbeitseinheit
bearbeitet und sie in jedem Pfad wieder schließt.
