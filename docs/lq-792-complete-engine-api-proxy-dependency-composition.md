# LQ-792 — Complete Engine API Proxy Dependency Composition

## Umsetzung

`compose_manifest_handoff_supervisor_engine_api_proxy` akzeptiert ausschließlich
die exakte geschlossene Settingsklasse und erzeugt einen
`SignalOwnedManifestHandoffSupervisorEngineApiRun`.

Die Composition baut jede konkrete Dependency einmal auf und übergibt dieselben
Settingspfade und Identitätsfakten durch alle zusammengehörigen Prüf- und
Ownershipgrenzen.

Der lokale Client wird an Host-Owner-UID und Client-GID gebunden. Der Proxypfad
gehört Proxy-UID und Client-GID; sein Elternverzeichnis bleibt an Host-Owner
gebunden. Containerwrapper und Daemonidentität bleiben davon getrennt.

## Fehlergrenze

Falsche Settingsobjekte und jeder Konstruktorfehler werden als bestehende
detailfreie technische Nichtverfügbarkeit zurückgegeben.

## Nicht umgesetzt

Kein Environmentread, keine PlatformSettings-Erweiterung, CLI, Appfactory,
Ausführung, Socketwirkung, Signalinstallation oder Deploymentänderung.
