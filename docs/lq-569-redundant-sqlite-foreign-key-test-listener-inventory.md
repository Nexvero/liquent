# LQ-569 — Redundant SQLite Foreign-key Test Listener Inventory

## Ergebnis

LQ-569 inventarisiert die nach LQ-558 verbliebenen testlokalen
SQLite-Fremdschlüssel-Listener vollständig.

16 Testmodule registrieren nach `build_engine` nochmals einen Connect-Listener
mit `PRAGMA foreign_keys=ON`. Seit der zentralen Aktivierung ist diese
Wiederholung idempotent, überdeckt aber, ob der jeweilige Test tatsächlich die
Produktions-Enginefactory verwendet.

## Betroffene Bereiche

Das Inventar umfasst:

- vier Manifest-Handoff-Registry-, Observation-, Execution- und
  Recovery-Module;
- Release-Authority-Foundation, Registry-Bootstrap und Registry-Projection;
- Release-Key-Activation und Release-Signing;
- sieben Release-Publication-Foundation-, Bootstrap-, Execution-, Attempt-,
  Handoff-, Artifact- und Recovery-Module.

Der bestehende LQ-557-Vertragsnachweis enthält den Pragmawert nur als Text und
ist kein redundanter Listener. Die fokussierte LQ-558-Regression führt das
Pragma bewusst aus, um die zentrale Wirkung direkt zu prüfen.

## Bereinigungsregel

Entfernt werden ausschließlich die 16 testlokalen Listenerfunktionen,
Dekoratoren und danach unbenutzten SQLAlchemy-`event`-Imports.

Fixtures, Seeds, Assertions, Constraintprüfungen, Migrationen und
Produktionscode bleiben unverändert. Kein Test darf das Pragma durch einen
anderen lokalen Mechanismus ersetzen.

## Erwartete Wirkung

Die betroffenen Tests öffnen ihre SQLite-Engines weiterhin ausschließlich über
`build_engine`. Bestehende Constraintabweisungen werden dadurch zu
Regressionen der zentralen LQ-558-Verbindungsvorbereitung.

## Abgrenzung

LQ-569 ändert keine Laufzeitsemantik, Migration, Tabelle, Constraintdefinition,
Portsignatur, Route, CLI oder Entry-Point-Grenze.

LQ-570 führt die mechanische Testbereinigung aus.
