# LQ-689 — Supervisor Settings Validation Evidence

## Ergebnis

Ausführbare Evidenz deckt den geschlossenen und den vollständig konfigurierten
Settingszustand ab.

## All-or-nothing

Für jeden der acht Werte wird separat belegt, dass sein Fehlen bei ansonsten
vollständiger Gruppe fail-fast scheitert.

Der Aktivzustand entsteht ausschließlich aus der vollständigen Gruppe.

## Negative Evidenz

Abgelehnt werden:

- unbekannter Modus
- relative, Root- und Traversalpfade
- identische Socket-/Controlpfade
- Nullidentität
- identische Host-/Wrapper-UID
- abweichende Reader-/Wrapper-GID
- aktive Gruppe ohne Datenbankkonfiguration

## Geheimnisfreiheit

Weder Pfade noch numerische Identitäten erscheinen in der öffentlichen
Settingszusammenfassung.

Das Runtimebeispiel enthält jeden Namen, aktiviert jedoch keinen Wert.

## Geschlossene Laufzeit

Entrypoint, Appfactory, Lifecycle und Compose lesen die neue Gruppe noch nicht.

Damit ist Settingsvollständigkeit notwendig, aber ausdrücklich nicht
hinreichend für Productionbereitschaft.
