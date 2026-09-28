# LQ-2623 — Staging Edge Compose Enablement

## Ergebnis

Der bisher nur als Zielpfad referenzierte Edge-Compose-Vertrag ist nun als
geprüftes Repository-Artefakt vorhanden. Er startet ausschließlich den
öffentlichen nginx-Edge und verbindet ihn mit dem bestehenden externen
`liquent_public`-Netzwerk.

## Sicherheitsgrenze

- Das nginx-Image muss als unveränderlicher Digest übergeben werden.
- Nur der Edge veröffentlicht die Hostports 80 und 443.
- Konfiguration und Zertifikate werden ausschließlich read-only eingebunden.
- Root-Dateisystem, Capability-Satz und Privilegien sind begrenzt.
- Temporäre nginx-Pfade liegen auf größenbegrenzten `tmpfs`-Mounts.
- Healthcheck, Neustartverhalten und lokale Logrotation sind begrenzt.

Der bestehende Routingvertrag bleibt unverändert: HTTP leitet auf HTTPS um,
öffentlich erreichbar ist nur `/health/live`, und alle übrigen HTTPS-Pfade
enden mit 404. Datenbank, Control Plane und Beobachtungsdienste erhalten durch
diesen Slice keine zusätzlichen Hostports.

## Betreiberwerte

`edge.env.example` enthält nur den Namen des erforderlichen Werts. Ein realer,
freigegebener nginx-Digest bleibt eine externe Betreiberentscheidung. Der
Slice erzeugt weder Zertifikate noch Secrets, DNS-Einträge, Release-Manifeste
oder Backup-Nachweise und behauptet keinen erfolgreichen Staging-Start.
Der bestehende Initial-Preflight lehnt Tags, andere Repositories, verkürzte
Digests und fehlende Edge-Imagewerte vor jeder Mutation detailarm ab.

## Verbleibende Bootstrap-Gates

Vor dem realen Bootstrap müssen der Edge-Digest und die übrigen
Infrastruktur-Digests freigegeben, das Release-Artefakt übernommen, echte
owner-only Laufzeitwerte bereitgestellt, TLS ausgestellt und ein frischer
verifizierter Backup-Nachweis gebunden werden. Erst dann darf der bestehende
Online-Preflight die bereits separat erteilte Initialisierungsfreigabe nutzen.
