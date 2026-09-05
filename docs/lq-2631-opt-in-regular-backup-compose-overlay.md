# LQ-2631 — Opt-in Regular Backup Compose Overlay

## Ergebnis

Der noch nicht veröffentlichte reguläre Backup-Container ist nicht länger Teil
des Basis-Compose-Vertrags für den initialen Staging-Start. Dienst, vier
Backup-Secrets und der separate Imagewert liegen jetzt vollständig in
`compose.backup.yaml` und `backup-images.env.example`.

Das Overlay bleibt doppelt opt-in: Der Betreiber muss es ausdrücklich als
zweite Compose-Datei angeben und zusätzlich das Profil `operations` aktivieren.
Ohne beides kann weder ein fehlender Backup-Digest die Basiskonfiguration
blockieren noch ein Backup-Prozess versehentlich starten.

## Erhaltener Backup-Vertrag

Die Auslagerung verändert den Dienst selbst nicht. Er bleibt ohne Hostport,
read-only, ohne Linux-Capabilities, auf das interne Datennetz begrenzt und von
gesundem PostgreSQL abhängig. Datenbank-Staging und `/tmp` bleiben
größenbegrenzte `tmpfs`-Mounts; Artefakte werden read-only eingebunden.

## Initialstart

Der Initial-Preflight validiert nur die Images, die der Basisvertrag tatsächlich
auflösen muss: App, PostgreSQL, Prometheus und Grafana. Der bereits real
verifizierte OVH-Vorher-Zustand bleibt der erforderliche Pre-Bootstrap-
Backupnachweis. Er wird nicht als Ersatz für den späteren regulären
Datenbank- und Artefaktbackupbetrieb ausgegeben.

## Grenze

Dieser Slice baut oder veröffentlicht kein Backup-Image und erzeugt keine
Object-Storage-Zugangsdaten. Das Overlay darf erst nach eigener Imagefreigabe,
Konfiguration, Restore-Probe und Betreiberaktivierung verwendet werden.
