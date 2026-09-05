# LQ-731 — Engine API Gate Composition Contract

## Ziel

Die vier bisher getrennten reinen Sicherheitsgrenzen werden in eine feste,
I/O-freie Gatefolge gebunden. Kein Aufrufer darf eine spätere Stufe überspringen
oder die Responseoperation frei wählen.

## Requestfolge

Jeder rohe Request durchläuft exakt HTTP/1.1-Framing und anschließend die
geschlossene Routenpolicy.

Nur bei klassifiziertem Create folgt zwingend die semantische Createpolicy.
Eine reine Create-Routenklassifikation erzeugt keine Requestautorität.

Das Ergebnis bindet Route, Container- oder Creationfakten und gegebenenfalls das
vollständige Createprofil an genau die ausgebende Gateinstanz.

## Responsefolge

Eine rohe Response wird nur zusammen mit einem Requestnachweis derselben
Gateinstanz akzeptiert. Nach dem Framing wird die Responsepolicy ausschließlich
mit der im Nachweis gebundenen Operation aufgerufen.

Ein caller-supplied Operationswert, Status-allow-Boolean oder rekonstruierter
Nachweis ist keine Autorität.

## Fehlergrenze

Jeder Fehler in Framing, Route, Create-Semantik, Nachweisbindung oder
Responsepolicy endet in derselben bestehenden detailfreien technischen
Nichtverfügbarkeit.

## Grenzen

Die Komposition besitzt keine Host-, Socket-, Stream-, Listener-, Transport-,
Retry- oder Forwardingfähigkeit. Hostpreflight bleibt eine getrennte aktuelle
Readinessvoraussetzung für den späteren aktiven Prozess.
