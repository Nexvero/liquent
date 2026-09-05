# LQ-810 — Engine API Real Run Status Completion Audit

## Ergebnis

LQ-807 bis LQ-810 schließen die objektidentische Statusinstrumentierung des
realen privaten Engine-API-Proxy-Runs.

## Geschlossene Eigenschaften

- eine Statusinstanz pro komponiertem Graph
- starting vor jeder Hostwirkung
- serving erst nach vollständigem Listenerpreflight
- stopping erst nach typisiertem Serve-Abschluss
- stopped erst nach sicherem Listener-Retire
- failed auf allen realen Run-Fehlerpfaden
- unverändertes Listenercleanup
- keine Wiederverwendung terminaler Runs
- detailfreie Fehler
- kein globaler Status

## Offene Blocker

Signal-Install- und Restorefehler liegen außerhalb des Owned Process Run und sind
noch nicht an denselben Status gebunden. Ebenso fehlen Healthtransport und
Deployment.

## Productionstatus

Instrumentierung allein öffnet keine Deploymentfähigkeit;
`production_ready=false` bleibt korrekt.

## Verifikation

Die fokussierte Engine-API-Kette besteht mit 410 Tests. Die vollständige
nicht-PostgreSQL-Suite besteht mit 5.760 Tests und 108 erwarteten Skips; als
Fehler behandelte Deprecation-Warnungen und die Diff-Prüfung bleiben sauber.

## Nächster Strang

Als Nächstes ist die äußere Signal-Run-Grenze an dieselbe Statusinstanz zu binden,
insbesondere für Install- und Restorefehler ohne falsches `stopped`.
