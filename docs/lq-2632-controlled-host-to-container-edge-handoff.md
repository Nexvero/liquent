# LQ-2632 — Controlled Host-to-Container Edge Handoff

## Problem

Der vorbereitete VPS betreibt noch den Ubuntu-nginx auf Port 80. Ein direkter
Start des Container-Edge würde deshalb an der Portbelegung scheitern. Zugleich
verwendet die ausgestellte Certbot-Lineage den vorhandenen HTTP-Webroot; ein
ungeprüfter Wechsel hätte spätere automatische Erneuerungen unterbrochen.

## Handoff

Der Initial-Bootstrap merkt sich Aktivierungs- und Enablementstatus des
Host-nginx. Erst nachdem PostgreSQL, Migration, Control Plane und ein
erfolgreicher isolierter `nginx -t` abgeschlossen sind, wird der Hostdienst mit
`disable --now` freigegeben. Danach startet der digestgebundene Container-Edge.

Scheitert eine spätere Stufe, stoppt der Fehlerpfad zuerst den Container-Edge,
stellt vorhandene Edge-Konfiguration und Imagezustand wieder her oder entfernt
die ausschließlich in diesem Lauf neu installierte Route. Anschließend werden
Enablement und Laufstatus des Host-nginx entsprechend dem beobachteten
Vorher-Zustand wiederhergestellt.

## ACME-Kontinuität

Der Container bindet `/var/www/html` read-only ein. Auf HTTP wird nur der
enge Pfad `/.well-known/acme-challenge/` aus diesem Webroot bedient; fehlende
Dateien enden mit 404. Alle anderen bisherigen Expositionsgrenzen bleiben
erhalten: HTTPS veröffentlicht nur `/health/live`, unbekannte HTTPS-Pfade
enden mit 404, und interne Readiness- oder Metrikpfade bleiben geschlossen.

## Grenze

Der Vertrag führt den Handoff nur im explizit bestätigten Initial-Bootstrap
aus. Dieser Slice stoppt den aktuell laufenden Host-nginx noch nicht und
startet keinen Container.
