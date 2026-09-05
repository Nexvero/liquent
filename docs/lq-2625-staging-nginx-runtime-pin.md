# LQ-2625 — Staging nginx Runtime Pin

## Ergebnis

Der offizielle nginx-Stable-Kanal wurde auf dem x86_64-Staging-VPS geladen und
vor jeder Edge-Aktivierung als kurzlebiger Container geprüft. Beobachtet wurde
nginx `1.30.4` mit dem unveränderlichen Registry-Digest:

`nginx@sha256:d5792f71a9496b833bc08ea834a758c46e2b6a6306c10f4be926f38a656cdc1c`

Die Edge-Vorlage bindet nun genau diesen Digest. Tags bleiben durch den
bestehenden Preflight ausgeschlossen.

## Laufzeitkorrektur

Die erste statische Compose-Fassung verwendete `wget` für den lokalen
Healthcheck. Die reale Imageprüfung belegte, dass dieses Werkzeug im
ausgewählten offiziellen Image fehlt. `curl` und nginx selbst sind vorhanden.
Der Healthcheck verwendet deshalb jetzt `curl --fail` gegen den ausschließlich
containerlokalen Pfad `/healthz`.

Diese Korrektur beruht auf dem tatsächlichen Zielartefakt und verhindert, dass
ein gesunder Edge wegen eines nicht vorhandenen Diagnosewerkzeugs dauerhaft
als unhealthy markiert würde.

## Grenze

Das Image liegt lediglich im lokalen Docker-Cache des Ziel-VPS. Es wurde kein
Edge-Container gestartet, kein Hostport verändert und kein Zertifikat oder
Secret erzeugt. PostgreSQL-, Prometheus-, Grafana- und Backup-Imagefreigaben
bleiben getrennte offene Entscheidungen.
