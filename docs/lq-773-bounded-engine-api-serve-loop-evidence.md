# LQ-773 — Bounded Engine API Serve Loop Evidence

## Stoppevidenz

Stop vor dem ersten Austausch erzeugt null Acceptwirkungen. Stop nach zwei
erfolgreichen Austauschen wird exakt in der Folge Stop, Exchange, Stop, Exchange,
Stop beobachtet.

Nicht-callable, None, Integer und eine fehlschlagende Stopquelle werden vor
Accept detailfrei abgelehnt.

## Grenze und Fehler

Die harte Grenze beendet nach exakt der konfigurierten Zahl ohne zusätzliche
Stop- oder Acceptausführung.

Ein Fehler in `serve_one` beendet nach genau einem Versuch, zählt den Austausch
nicht und löst keinen Retry aus.

Ungültige Acceptoperation sowie null oder boolesche Maximalzahl scheitern beim
Aufbau.

## Fähigkeitsgrenze

Die Oberfläche enthält kein Open, Listen, Bind, Signal, Thread oder Close. Die
Tests patchen ausschließlich die konkrete Einmaloperation und öffnen keinen
Listener.
