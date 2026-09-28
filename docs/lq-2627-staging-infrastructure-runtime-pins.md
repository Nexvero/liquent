# LQ-2627 — Staging Infrastructure Runtime Pins

## Ergebnis

Die drei allgemeinen Infrastruktur-Images des Staging-Compose-Vertrags wurden
auf dem x86_64-Ziel-VPS aus ihren offiziellen Registries geladen. Version und
unveränderlicher Registry-Digest wurden jeweils mit einem kurzlebigen
Container beziehungsweise der lokalen Image-Metadatenansicht bestätigt.

## Freigegebene Pins

- PostgreSQL `18.6`:
  `postgres@sha256:4ef4dbc939d61acea57712655ddb4b4ab27419c913f94cca0cd57cb3ea3c2280`
- Prometheus `3.14.0`:
  `prom/prometheus@sha256:5ce7540c3c00ef4ab0c9d2c995c6a5b9c421f44b4a115d97a2c7af3b1c21cbb0`
- Grafana `13.1.0`:
  `grafana/grafana@sha256:121a7a9ece6dc10b969f1f96eed64b4f07dfac0d0b8abc070f7cb83bbde86f63`

Die bisher wertoffenen Platzhalter in `images.env.example` tragen nun diese
vollständigen Digests. Eine Regression bindet Repository und Digest exakt und
verhindert die unbemerkte Rückkehr zu Tags oder unvollständigen Werten.

## Anwendungsimage

Das separat veröffentlichte Liquent-Image wurde ebenfalls auf dem Ziel-VPS
geladen. Sein Digest entspricht dem Release-Manifest, und das eingebettete
OCI-Revisionslabel entspricht dem gebundenen Commit
`b2a277d763618a6bb51929375c9397f720f764a9`.

## Grenze

Keines dieser Images wurde dauerhaft als Dienst gestartet. Der nicht
veröffentlichte separate Backup-Imagevertrag bleibt offen und wird nicht durch
einen beliebigen Ersatzdigest umgangen. Laufzeitwerte und echter
Backup-Nachweis bleiben weitere Bootstrap-Gates.
