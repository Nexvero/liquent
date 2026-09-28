# LQ-571 — Central SQLite Foreign-key Adoption Regression

## Ergebnis

LQ-571 belegt die vollständige Übernahme der zentralen
SQLite-Fremdschlüsselaktivierung durch die bereinigten Testbereiche.

## Statisches Inventar

Keines der 16 inventarisierten Module enthält noch
`PRAGMA foreign_keys=ON`, `event.listens_for` oder einen SQLAlchemy-`event`-
Import.

Der statische Nachweis benennt die Module ausdrücklich. Dadurch kann ein
später wieder eingeführter lokaler Listener die zentrale Regression nicht
unbemerkt überdecken.

## Laufender Nachweis

Alle 16 bereinigten Module und die fokussierte zentrale LQ-558-Regression
bestehen gemeinsam mit 265 Tests unter
`-W error::DeprecationWarning`.

Abgedeckt sind Manifest-Handoff, Release-Authority und -Registry,
Key-Activation, Signing sowie die Publication-Kette einschließlich
tatsächlicher Constraintabweisungen.

## Semantik

Die grünen Tests belegen Testadoption, keine neue Produktionswirkung. Die
Verbindungsvorbereitung bleibt ausschließlich in `build_engine`; Migrationen
definieren weiterhin die Constraints.

## Abgrenzung

LQ-571 entfernt keine fachliche Assertion, lockert keinen Constraint und
ergänzt keinen Fallback oder SQLite-Sonderhelper.

LQ-572 führt den vollständigen Normal-, PostgreSQL-, Wheel-, Inventar- und
Diffaudit aus.
