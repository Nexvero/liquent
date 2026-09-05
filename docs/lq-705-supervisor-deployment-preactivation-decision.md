# LQ-705 — Supervisor Deployment Preactivation Decision

## Entscheidung

Eine direkte Composebindung des rohen Docker-Sockets wird in diesem Strang nicht
freigegeben.

Zuerst müssen vier getrennte Voraussetzungen geschlossen werden.

## 1. Launchpublisher

Die process-eigene Composition erhält einen atomaren Parent-Launchpublisher,
der dieselbe Registry, Control-Wurzel, Identitypolicy und denselben kanonischen
Codec verwendet.

Prepare muss Publikation vor Create verlangen und divergente Wiederverwendung
als Konflikt behandeln.

## 2. Eingeschränkte Engine-API

Eine lokale Proxy- oder gleichwertige Policygrenze beschränkt den erreichbaren
Daemonvertrag auf die bereits geschlossenen Supervisoroperationen.

Die konkrete Implementierung, Installation und Ownership folgen einem eigenen
Slice; ein bloßer read-only Socketmount erfüllt diese Anforderung nicht.

## 3. Hostpfad und Identität

Ein Deployment-Preflight bestätigt absoluten identischen Host-/Containerpfad,
dedizierte 0700-Control-Wurzel, feste Parent-UID, Reader-Zusatzgruppe und
getrennte Engine-API-Gruppe.

Fehler führen zu not-ready vor fachlicher Wirkung.

## 4. End-to-End-Evidenz

Erst danach müssen reales Create, Start, Ready, Release, Writer, Recovery,
Terminal, Crash, Restart, not-ready und Shutdown gegen die eingeschränkte
Grenze belegt werden.

## Aktivierungsregel

Compose darf erst nach Abschluss aller vier Voraussetzungen geändert werden.

`production_ready=true` bleibt bis zum vollständigen Nachweis verboten.

## Keine Teilfreigabe

Ein Settingswert, Socketmount, Controlvolume, Userfeld oder Healthprobe allein
ist keine sichere Zwischenstufe und darf nicht aktiviert werden.
