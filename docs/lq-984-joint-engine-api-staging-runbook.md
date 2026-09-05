# LQ-984 — Joint Engine API Staging Runbook

Dieses Runbook ist vor Aktivierung des isolierten Overlays verpflichtend und
autorisiert keine Produktion.

1. Vier `engine-api-*.env.example` außerhalb Git kopieren, Fakten prüfen und
   alle Runtime-Dateien unter dem Laufzeitowner auf Modus `0600` setzen.
2. `supervisor-engine-api.env.example` außerhalb Git kopieren und alle acht
   absoluten Hostbindungen auf vorhandene Stagingpfade setzen.
3. Docker socket als Unix-Socket mit erwarteter UID/GID prüfen; Control und
   Target owner-writable, Source für die Serviceidentität immutable halten.
4. Den Vier-Dateien-Deployment-Preflight ausführen; nonzero blockiert.
5. Den Compose-Renderpreflight ausführen. Er darf nur `config --quiet`, nie
   `up`, `create`, `start`, `run` oder `exec` aufrufen.
6. Render auf immutable Digest, Profil, UID/GID, Gruppe, keine Capabilities,
   keine Ports, acht Mounts, tmpfs, Limits und Unix-Healthcheck prüfen.
7. Nur in isoliertem Staging-Daemon das Profil ausdrücklich starten und
   Image-, Inspect- und Zeitnachweise privat sichern.
8. `/live` und `/ready` gegen die tatsächlichen Prozessphasen prüfen; es darf
   kein TCP-Listener erscheinen.
9. Einen erlaubten und einen verweigerten Request prüfen; Peer-, Route-,
   Daemon- und Responsegrenzen müssen fail-closed bleiben.
10. Während idle Accept SIGTERM senden. Beide Sockets müssen innerhalb Join-
    und Grace-Frist verschwinden; kein Thread oder Child darf verbleiben.
11. Health- und Proxyfehler getrennt erzwingen (`forced Health failure` und
    `forced proxy failure`); jeder muss den Peer stoppen und extern
    ausschließlich detailfreie Fehler liefern.
12. Stagingservice entfernen und belegen, dass Hostdaten weder gelöscht noch
    in Ownership verändert wurden; Evidenz privat nach Retention halten.

Production readiness remains false, bis alle Schritte aktuelle
Umgebungsevidenz besitzen und ein finaler Audit sie ausdrücklich akzeptiert.
