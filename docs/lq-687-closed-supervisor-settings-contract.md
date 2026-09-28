# LQ-687 — Closed Supervisor Settings Contract

## Ziel

Der Manifest-Handoff-Supervisorkandidat erhält genau einen geschlossenen,
all-or-nothing Prozesssettingsvertrag.

Settings eröffnen noch keine Composition oder Productionfähigkeit.

## Atomare Gruppe

Die Gruppe bindet gemeinsam acht Werte:

- den einzigen Modus `candidate`
- eine stabile, geschlossene Backendinstanz-ID
- einen absoluten Docker-Socketpfad
- eine absolute Control-Directory-Hostwurzel
- Host-Owner-UID
- gemeinsame Reader-/Wrapper-GID
- abweichende Wrapper-UID
- Wrapper-GID

Fehlt genau ein Wert, wird die gesamte Gruppe beim Settings-Aufbau abgelehnt.

## Pfadgrenzen

Socket und Control-Wurzel müssen absolut, geschlossen und voneinander
verschieden sein.

Root, relative Pfade und explizite Parent-Traversierung sind verboten.

Existenz, Dateityp, Eigentümer und Modus werden erst an der späteren
process-eigenen Composition gegen den aktuellen Hostzustand geprüft.

## Identitätsgrenzen

Alle IDs liegen im positiven 32-Bit-Systembereich.

Wrapper- und Reader-GID sind identisch; Wrapper- und Host-Owner-UID müssen
verschieden sein.

Damit kann der spätere Launchanker seine bestehende geschlossene Identitypolicy
ohne freie Benutzerzeichenfolge rekonstruieren.

## Persistenzbindung

Eine aktive Gruppe verlangt bereits eine konfigurierte Datenbank-URL, da der
Kandidat ohne persistente Journal-, Runtime- und Gate-Fakten nicht komponierbar
ist.

Es wird keine zweite Engine oder Verbindung erzeugt.

## Beobachtbarkeit

Die öffentliche Zusammenfassung zeigt ausschließlich aktiv oder inaktiv.

Pfade, IDs und Datenbankmaterial werden nicht ausgegeben.

## Nicht Teil dieses Slices

Keine Processcomposition, Appfactory-, Lifecycle-, Socket-, Compose-, Schema-,
SQL-, Port-, Modell-, Migrations-, CLI- oder Productionaktivierung.
