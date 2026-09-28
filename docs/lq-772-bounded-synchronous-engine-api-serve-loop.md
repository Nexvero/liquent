# LQ-772 — Bounded Synchronous Engine API Serve Loop

## Umsetzung

`BoundedManifestHandoffSupervisorEngineApiServeLoop` bindet genau die konkrete
Single-Accept-Operation und eine positive Maximalzahl.

`run` prüft die Stopquelle am Schleifenanfang, ruft bei `False` genau einmal
`serve_one` auf und erhöht erst nach dessen erfolgreichem Abschluss den Zähler.

Bei `True` wird sofort ein `stopped`-Ergebnis ausgegeben. Nach Erreichen der
Grenze entsteht `exchange_limit`.

## Fail-closed

Nur echte boolesche Stopwerte sind gültig. Stop- und Acceptausnahmen werden auf
die bestehende detailfreie technische Nichtverfügbarkeit reduziert.

Ein fehlgeschlagener Einzelaustausch wird nicht gezählt und nicht wiederholt.

## Nicht umgesetzt

Kein Listener-Lifecycle, Signal, Acceptunterbrechung, Thread, Sleep,
Fehlerfortsetzung oder Prozessentrypoint wird ergänzt.
