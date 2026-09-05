# LQ-301 — Controlled Research Worker Compose Wiring

## Ergebnis

LQ-301 schließt den statischen Compose-Wiring-Blocker des persistenten
Research Workers.

Der vorhandene Service startet jetzt den installierten
`liquent-research-worker` mit den beiden expliziten Argumenten für
Processkonfiguration und Datenbank-URL-Datei.

Diese Änderung ist Deployment-Composition. Sie erweitert weder Domainmodell
noch Persistenz und behauptet noch keinen erfolgreichen Produktionslauf.

## Kontrollierte Eingaben

Die Datenbank-URL bleibt das bestehende dateigemountete Compose-Secret unter
`/run/secrets/database_url`. Sie erscheint weder in `runtime.env` noch als
Commandwert.

Der Worker überschreibt den gemeinsamen Secret-Mount gezielt mit Runtime-UID
und -GID `10001` sowie Modus `0400`, passend zum unveränderlichen Imageuser und
zur owner-only Prüfung des Entry-Points.

Die Worker-Konfiguration wird aus einem expliziten absoluten Hostpfad nach
`/run/liquent/research-worker.json` read-only gemountet.

Die stabile Worker-ID wird unabhängig davon aus einem zweiten expliziten
absoluten Hostpfad nach `/run/liquent/research-worker-id` read-only gemountet.

Beide Dateien müssen aus Sicht der Runtime-UID regulär, owner-only, nicht
verlinkt und im erlaubten Größenbereich sein. Der LQ-299-/LQ-300-Loader prüft
diese Eigenschaften erneut und scheitert andernfalls detailfrei.

Compose erzeugt, korrigiert oder rotiert keine dieser Dateien.

## Daten- und Artifactgrenze

Der explizite Research-Datenpfad wird ausschließlich read-only nach
`/var/lib/liquent/research-data` gemountet.

Nur das bestehende benannte Artifactvolume ist für den Worker beschreibbar und
liegt unter `/var/lib/liquent/artifacts`.

Die Beispielkonfiguration referenziert exakt diese festen Containerpfade. Sie
setzt weiterhin Maximalkonkurrenz eins und deaktivierte Trading-Konnektivität.

Das Beispiel ist kein aktives Secret und keine automatisch verwendete
Konfiguration. Betreiber kopieren es außerhalb von Git, prüfen die Werte und
setzen owner-only Dateirechte.

## Hostpfad-Interpolation

`runtime.env.example` dokumentiert drei nicht geheime absolute Hostpfade für
Konfiguration, Worker-ID und Researchdaten.

Die reale `runtime.env` muss beim Compose-Rendern explizit als Environmentquelle
übergeben werden, damit diese Werte für Interpolation zur Verfügung stehen.

Fehlende Variablen brechen bereits das Rendern über die verpflichtenden
Compose-Ausdrücke ab. Fehlende oder ungeeignete Dateien brechen spätestens die
owner-only Entry-Point-Prüfung ab.

Es gibt keinen Environmentfallback für Dateiinhalte, Worker-ID oder DSN.

## Start- und Stopreihenfolge

Der Worker bleibt vom erfolgreichen Abschluss des Migration-Gates abhängig.

Danach prüft der Entry-Point selbst eine Datenbankverbindung und den exakten
Migration-Head, bevor Resolver, ArtifactStore, Claim oder Loop erreichbar sind.

Die bestehende `stop_grace_period` von 60 Sekunden bleibt explizit erhalten.
SIGTERM setzt nur das Stop-Event; danach wird kein neuer Job geclaimt.

Ein bereits laufender synchroner Job darf innerhalb dieser Frist seinen
claimgebundenen Abschluss versuchen. Compose fügt keinen zweiten
Abbruchmechanismus innerhalb des Prozesses hinzu.

## Netzwerk- und Prozessgrenze

Der Worker bleibt ohne veröffentlichten Port und ohne Verbindung zum
öffentlichen Netzwerk.

Er nutzt ausschließlich Application-, Data- und Observability-Netz sowie die
bereits gesetzten Read-only-, Capability-, Resource- und Logging-Grenzen.

Der Slice fügt keinen Sidecar, Supervisor, zweiten Workerprozess, Healthport
oder automatische Skalierung hinzu.

## Bewusste Nichtziele

LQ-301 erzeugt keine Researchjobs, Benutzer, Workspaces, Memberships,
Capabilities, Datensätze, Worker-Identitäten oder Secrets.

Es gibt keine Schema-, Tabellen-, SQL-, Migrations-, Port-, Modell- oder
Signaturänderung.

Es gibt keine Image-Erstellung, Registry-Veröffentlichung, externe
Netzfreigabe, Providerfreigabe oder Produktionsinbetriebnahme.

Reguläre Research-Job-Erzeugung und jede fachliche Mutation bleiben an ihren
bestehenden autorisierten Grenzen.

## Audit

Der statische Test bindet Commandargumente, Secretpfad, read-only Inputs,
beschreibbares Artifactvolume, feste Containerpfade, Migration-Gate und Grace
Period zusammen.

Er prüft außerdem, dass kein Datenbankwert in die nicht geheime Runtimevorlage
wandert und dass der Worker nicht am öffentlichen Netzwerk hängt.

Die vorhandenen Slice-0- und LQ-288-Audits bleiben kompatibel; der historische
Hinweis auf fehlendes Worker-Wiring wird durch diesen späteren Slice abgelöst.

## Verbleibende Evidenz

Statisches Wiring beweist nicht, dass Host-UID, Dateirechte, Imageinhalt,
PostgreSQL, Migrationen, Dataset und Artifactvolume in einer realen Umgebung
zusammen funktionieren.

LQ-302 sollte deshalb den verpflichtenden PostgreSQL-Mehrprozess- und
End-to-End-Nachweis erbringen: Migration-Gate, Workerstart, Claim, Heartbeat,
Artifactpersistenz, Finalisierung, Konkurrenz und kontrollierter SIGTERM-Stop.

Bis dieser Nachweis vorliegt, ist die Compose-Grenze vollständig beschrieben
und fail-closed verdrahtet, aber nicht als produktionsbereit attestiert.
