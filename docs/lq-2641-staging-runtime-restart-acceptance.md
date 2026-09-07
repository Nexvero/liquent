# LQ-2641 — Staging Runtime Restart Acceptance

## Ziel

Dieser Slice belegt den kontrollierten Wiederanlauf des initialen
Staging-Systems nach dem erfolgreichen Bootstrap. Er prüft, dass die
persistente Datenbank, die Control Plane und der Container-Edge unabhängig
nacheinander neu starten können, ohne auf den abgelösten Host-nginx
zurückzufallen.

Die Prüfung ist eine Staging-Abnahme. Sie ist weder eine Production-Freigabe
noch eine allgemeine Verfügbarkeits- oder Wiederherstellungsgarantie.

## Gebundener Ausgangsstand

Der geprüfte Repository-Stand ist der gemergte Commit
`37aa9d4e16ffec115c0e68dd98fe2c72bac3169a` auf `main`.

Die laufende Control Plane verwendet Release `0.1.1` mit dem unveränderlichen
Image-Digest
`sha256:80154c0da57fc4c832a4cf8fe2a8250f25b6c85c61de06d317f88c3f07801a67`.
PostgreSQL und nginx sind ebenfalls über vollständige Digests gebunden.

Vor der Mutation waren PostgreSQL, Control Plane und Edge gesund. Der externe
Liveness-Endpunkt antwortete über TLS mit HTTP `200`. Beide regulären
Backup-Timer waren aktiv und ihre letzten Service-Ergebnisse erfolgreich.

## Kontrollierter Wiederanlauf

Am 7. September 2026 wurden die drei Container auf dem Staging-VPS einzeln in
Abhängigkeitsreihenfolge neu gestartet:

1. PostgreSQL,
2. Control Plane,
3. Container-Edge.

Jeder nachfolgende Schritt wartete auf den erfolgreichen Healthcheck des
vorherigen Dienstes. Ein fehlendes `healthy` innerhalb der begrenzten Wartezeit
hätte den Ablauf beendet und die späteren Neustarts verhindert.

## Beobachtetes Ergebnis

Alle drei Container erreichten nach dem jeweiligen Neustart wieder den Zustand
`healthy`. Der öffentliche Endpunkt
`https://staging.liquent.ai/health/live` antwortete danach mit HTTP `200`.

Die persistente Datenbank meldete weiterhin den Alembic-Stand
`20260826_0042`. Damit blieb der angewendete Migrationsstand über den
PostgreSQL-Neustart erhalten.

Der frühere Host-nginx blieb `inactive`; Port 80 und 443 werden weiterhin nur
vom geprüften Container-Edge übernommen. Es wurde kein Rückfall auf eine zweite
Edge-Instanz beobachtet.

`liquent-backup.timer` und `liquent-backup-age.timer` blieben aktiv. Der
Wiederanlauf veränderte weder ihre Aktivierung noch die bereits eingerichtete
Backup- und Altersüberwachung.

## Lokale Vertragsprüfung

Die fokussierte lokale Suite für Initial-Bootstrap, Edge und Promotion wurde
auf dem gemergten Stand erneut ausgeführt. Alle 20 ausgewählten Tests waren
erfolgreich.

## Grenze und nächster Schritt

Der Slice erzeugt kein neues Release, führt keine Migration aus und verändert
keine Secrets, DNS-Einträge, Zertifikate, Backup-Aufbewahrung oder
Produktionssysteme. Er behauptet weder einen Restore-Test während dieses
Neustarts noch eine längerfristige Staging-Stabilität.

Als nächster separater Strang folgt die authentifizierte Staging-Abnahme des
Benutzer- und OIDC-Flusses. Eine Production-Freigabe benötigt danach eigene
Beobachtungs-, Rollback- und Autoritätsentscheidungen.
