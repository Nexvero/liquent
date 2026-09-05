# LQ-800 — Owner-controlled Engine API Proxy Entrypoint

## Umsetzung

`run_manifest_handoff_supervisor_engine_api_proxy` nimmt genau einen Path,
lädt die privaten Settings, komponiert den vollständigen Graphen und ruft dessen
parameterlosen signalbesessenen Run auf.

Das Ergebnis wird erneut an Typ, Grund und die konfigurierte harte Laufgrenze
gebunden. `exchange_limit` ist nur bei exakt erreichter Grenze gültig.

`main` verwendet einen geschlossenen Parser mit genau `--settings-file` und
übersetzt ausschließlich vollständigen Erfolg in Exitcode 0. Jede andere
Situation endet ohne Detailausgabe mit Exitcode 2.

## Modulgrenze

Das separate Transport-Entrypoint-Modul ist direkt ausführbar. Eine Paketscriptregistrierung
würde das kontrollierte Releaseinventar verändern und bleibt deshalb gemeinsam
mit Packaging separat. Bestehende Web- und Supervisorprozesse werden nicht
verändert.

## Nicht umgesetzt

Kein Compose-Service, Mount, Environmentwert, Healthcheck, Logging oder
Production-Readinessclaim.
