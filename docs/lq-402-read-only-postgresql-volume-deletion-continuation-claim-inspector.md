# LQ-402 — Read-only PostgreSQL Volume Deletion Continuation Claim Inspector

## Ergebnis

LQ-402 installiert
`liquent-disposable-postgres-volume-delete-continue-reconcile` als strikt
read-only Grenze für offene LQ-400-Continuation-Claims.

Der Inspector klassifiziert private Evidence, beide Claims und das exakte
lokale Volume, ohne einen Write auszuführen.

## Separate Inspectorauthority

Eine neue aktuelle owner-only Autorisierung bindet die stabile
Continuation-Reconciliation-ID an Continuation, Finalization,
Reconciliation, Löschung, Disposition und alle Clearancefakten.

Operation ist exakt
`inspect_disposable_postgres_volume_deletion_continuation`, Scope exakt
`data_volume_only` und das UTC-Fenster höchstens eine Stunde.

Executor, Authorizer und Reviewer sind getrennt. Historische Autorisierungen
werden in ihrem ursprünglichen Zeitkontext validiert; die neue Autorisierung
muss aktuell und bytegenau an LQ-400 gebunden sein.

## Evidencepriorität

Der Evidencepfad wird aus dem vollständigen SHA-256 der gebundenen
Continuation-ID abgeleitet und vor Claims oder Docker geprüft.

Vollständig gebundene LQ-400-Evidence ergibt
`continuation_evidence_present`, unabhängig davon, ob der Unterclaim noch
vorhanden ist.

Malformed oder fremde Evidence bleibt technisch unavailable und wird nicht
überschrieben oder ignoriert.

## Neutrale Abwesenheit

Fehlen Continuation-Evidence und der exakt abgeleitete Unterclaim gemeinsam,
liefert der Inspector `not_found` ohne Dockerzugriff.

Dieser Ausgang sagt nichts über das Volume oder den ursprünglichen Claim aus
und erzeugt keinen Claim nachträglich.

## Vollständiger Doppelclaim

Ein vorhandener Unterclaim wird owner-only, regulär, einfach verlinkt und
vollständig gegen die LQ-400-Bindung geprüft.

Danach muss auch der ursprüngliche LQ-394-Claim kanonisch und exakt gebunden
offen sein.

Ein fehlender ursprünglicher Claim oder widersprechende gültige Lösch- oder
Finalization-Evidence ergibt `conflict`. Malformed Claims bleiben technisch
unavailable.

Beide Claims bleiben in jedem Ausgang unverändert.

## Exakte Volumebeobachtung

Nur ein vollständig gebundener offener Doppelclaim ohne Continuation-Evidence
erreicht Docker.

Der Inspector liest zuerst eine exakt verankerte Namensliste für das intern
abgeleitete Volume.

Bei genau einem Treffer folgt ein einzelnes exaktes Inspect der rungebundenen
Compose-Zuordnung.

Andere Dockerobjekte, Events, Logs, Mounts, Inhalte und SQL bleiben
unerreichbar.

## Geschlossene Zustände

Die read-only Klassifikation liefert:

- `volume_present` für das exakt vorhandene, korrekt gebundene Volume;
- `volume_absent_evidence_missing` für exakt bestätigte Abwesenheit;
- `conflict` für lesbare widersprüchliche Claims, Evidence oder
  Volumebindungen;
- `continuation_evidence_present` oder `not_found` vor Docker;
- technisch unavailable ohne Ergebnisobjekt.

Kein Zustand autorisiert einen weiteren Remove oder behauptet vollständige
Datenentsorgung.

## Technische Fehler

Nonzero, stderr, Timeout, Truncation, Hard Kill, ungültiges UTF-8, doppelte
JSON-Schlüssel und uneindeutige Namenslisten bleiben detailfrei unavailable.

Sie werden nicht als Abwesenheit, Konflikt oder Erfolg umgedeutet.

## Strikte Writefreiheit

Der Inspector führt weder Claim-, Evidence- noch Ressourcenwrites aus.

Volume-Remove, Force, Prune, Compose-Down, Mount, Export, Container- und
Networkmutation sowie SQL sind nicht erreichbar.

LQ-398 und LQ-400 werden nicht gestartet. Auch bei bestätigter Abwesenheit
bleiben ursprünglicher und untergeordneter Claim offen.

## Öffentliche Ausgabe

Die CLI gibt nur Schemaversion, Operation
`disposable_postgres_volume_deletion_continuation_reconciliation` und den
geschlossenen Ausgang aus.

Private IDs, Hashes, Pfade, Ressourcen, Identitäten, Zeiten und technische
Fehlerdetails werden nicht ausgegeben.

## Tests

Vierzehn Fake-basierte Tests belegen Evidencepriorität, neutrales `not_found`,
vollständige Doppelclaimbindung, Volumeanwesenheit, -abwesenheit und Conflict.

Weitere Fälle prüfen malformed Claims, mehrdeutige Dockerantworten,
Hashabweichung, exakte read-only argv, CLI und Entry Point.

Kein Test verändert echte Dockerressourcen.

## Bundle und Nichtziele

Entry Point und Operatormodul erhöhen die Gates auf 56 Entry Points und 60
Operatormodule. Migrationen bleiben bei 27 mit Head `20260819_0027`.

LQ-402 implementiert keine Claimfinalisierung, neue Continuation,
Evidenceerzeugung oder Freigabe des ursprünglichen LQ-394-Claims.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Domainmodell-,
Compose- oder Production-Wiring-Änderung.

## Nächster Slice

LQ-403 sollte den Evidence-first Finalisierungsvertrag für die geschlossenen
LQ-402-Zustände definieren.

Er muss Continuation-Evidence und bestätigte Volumeabwesenheit terminal
auflösen, den Unterclaim erst nach eigener Evidence freigeben und den
ursprünglichen Claim für eine spätere frische LQ-398-Finalisierung offen
lassen.
