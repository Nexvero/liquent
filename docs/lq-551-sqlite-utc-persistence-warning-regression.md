# LQ-551 — SQLite UTC Persistence Warning Regression

## Ergebnis

LQ-551 belegt die expliziten Adapter über repräsentative persistente
Produktpfade statt nur über einen direkten SQLite-Bindetest.

## Abdeckung

Die strikte Suite umfasst Browser-Sessions, OIDC-Logintransaktionen,
Research-Jobs und Finalisierung, Manifest-Handoff-Registry, Execution-
Ownership und Recovery.

Damit werden nullable und verpflichtende Zeitspalten, Leasezeiten,
Lifecyclezeiten, Retryrekonstruktion und mehrere Migrationsepochen abgedeckt.

## Strikte Warnungsgrenze

`DeprecationWarning` wird als Testfehler behandelt.

Alle 48 fokussierten Tests bestehen ohne Warnung. Die zuvor an denselben
Pfaden erzeugten SQLite-Datetime-Warnungen treten nicht mehr auf.

## Unveränderte Fakten

Aware UTC-Werte rekonstruieren weiterhin dieselben Zeitpunkte.

Retryergebnisse behalten ursprüngliche Serverzeiten. Nullable Zeitwerte und
fail-closed technische Fehler bleiben unverändert.

PostgreSQL-Semantik und Migrationen werden nicht verändert.

## Nächster Slice

LQ-552 führt normale und PostgreSQL-Gesamtsuite, Wheel-, Inventar-,
Migrations- und Diffaudit unter der neuen Warnungsgrenze aus.
