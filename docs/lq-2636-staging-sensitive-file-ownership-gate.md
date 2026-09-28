# LQ-2636 — Staging Sensitive File Ownership Gate

## Problem

Owner-only Modusbits verhindern keinen Austausch einer Datei durch ihren
aktuellen Eigentümer. Auf dem realen Staging-Host sollen die sensitiven
Bootstrap-Eingaben deshalb nicht nur privat, sondern eindeutig der
administrativen Vertrauensgrenze zugeordnet sein.

## Vertrag

Der Online-Preflight verlangt UID 0 für Image-Environment, Runtime-Environment,
Initialkonfiguration, Edge-Environment, privaten TLS-Schlüssel und beide
für diesen Lauf benötigten Datenbank-Secretdateien. Die Eigentümerprüfung erfolgt zusätzlich zu
Existenz-, Symlink-, Inhalts- und Modusprüfungen. Eine nicht lesbare
Eigentümerinformation oder eine abweichende UID beendet den Gate geschlossen.

Der lokale `--offline`-Modus erzwingt keine Root-Eigentümerschaft, damit
isolierte Vertragsfixtures ohne erhöhte Rechte ausführbar bleiben. Dieser
Modus ist weiterhin ausdrücklich keine Autorisierung für einen realen
Bootstrap.

## Grenze

Der Slice ändert keine Eigentümer oder Rechte und liest keine Secretwerte aus.
Öffentliche Zertifikatsketten und nicht-sensitive Compose-Dateien benötigen
keine Root-Eigentümerprüfung in diesem Gate. Es wird weder ein Container noch
ein Hostdienst verändert.
