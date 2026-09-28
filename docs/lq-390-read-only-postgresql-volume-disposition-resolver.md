# LQ-390 — Read-only PostgreSQL Volume Disposition Resolver

## Ergebnis

LQ-390 implementiert den in LQ-389 definierten lokalen read-only Resolver als
`liquent-disposable-postgres-volume-disposition`.

Die Grenze liefert ausschließlich `retain`, `deletion_review_eligible` oder
`investigation_required`.

Technische Nichtverfügbarkeit bleibt detailfrei ohne Ergebnisobjekt.

## Aktuelle owner-only Authority

Jeder Aufruf benötigt eine aktuelle private Volume-Disposition-Autorisierung.

Sie bindet Run, Source, Image, Compose, stabile Dispositions-ID, Operation,
Lineage-Manifest sowie Retention-, Legal-Hold- und Recoveryentscheidungen über
bytegenaue SHA-256-Werte.

Executor, Authorizer und Reviewer müssen drei verschiedene opake Identitäten
sein.

Das aktuelle Zeitfenster muss positiv und auf höchstens eine Stunde begrenzt
sein.

Gewünschter Ausgang, Delete-Boolean, Rolle und Volumename sind keine Eingaben.

## Geschlossenes Lineage-Manifest

Die Autorisierung bindet ein owner-only Lineage-Manifest bytegenau.

Das Manifest bindet Run, Phase, Source, Image, Compose, intern abgeleitetes
Volume, finalisierten Cleanupstatus und mögliche spätere Nutzung.

Es inventarisiert die tatsächlich entstandenen historischen Artefakte mit
eindeutigem Typ, absolutem privatem Pfad und SHA-256.

Mindestens Staging-Evidence, Recovery-Disposition, Cleanup-Autorisierung und
Cleanup-Finalization-Evidence müssen vorhanden sein.

Jedes referenzierte Artefakt wird erneut als private owner-only Datei gelesen
und bytegenau gehasht.

Das Manifest ist kein Löschrecht und wird vom Resolver nicht verändert.

## Aktuelle Entscheidungsfakten

Retention-, Legal-Hold- und Recoverydateien sind separate private
System-of-Record-Fakten.

Jede Datei muss denselben Run und das intern abgeleitete Volume binden, eine
stabile Entscheidungs-ID und einen eigenen Authorizer besitzen und aktuell
gültig sein.

Die Entscheideridentität darf mit keiner der drei Resolveridentitäten
zusammenfallen.

Retention liefert ausschließlich `retain` oder `cleared`.

Legal Hold liefert ausschließlich `clear`, `active` oder `conflict`.

Recovery bindet policyabhängige Backup- und Restorepflichten sowie ihre
geschlossenen Ausgänge.

## Backup- und Restoreabbildung

Nicht erforderliches Backup beziehungsweise Restore muss ausdrücklich
`not_required` lauten und darf keine scheinbare Objekt-ID tragen.

Erforderliches Backup benötigt `verified`, stabile Backup-ID und
Integritäts-SHA-256.

Erforderlicher Restore benötigt `verified` und eine stabile Restore-ID.

`pending` ist vollständig lesbar, aber nicht positiv und ergibt `retain`.

Der Resolver startet und repariert keinen Backup- oder Restoreprozess.

## Geschlossene Claims

Vor jeder Dockerbeobachtung öffnet der Resolver das private
Evidenceverzeichnis read-only und prüft auf offene PostgreSQL-Cleanup-Claims.

Ein offener Claim ist technische Nichtverfügbarkeit.

Der Resolver liest, löscht oder verändert den Claim nicht.

Unsicheres Evidenceverzeichnis oder breitere Group-/World-Rechte enden
ebenfalls fail-closed.

## Exakte Volumeableitung

Der Projektname muss exakt `liquent-<run-id>` entsprechen.

Der Volumename wird ausschließlich als
`<project-name>-postgres-data` abgeleitet und gegen das gebundene Manifest
geprüft.

Der Caller kann keinen alternativen Namen, Präfix, Scope oder Selector
angeben.

Damit bleiben Wildcard-, Labelgruppen-, Host- und Composeprojekt-Auswahl
unerreichbar.

## Einzige Dockerbeobachtung

Nach vollständiger Authority-, Hash-, Lineage-, Entscheidungs- und Claimprüfung
führt der Resolver genau `docker volume inspect <intern abgeleitetes volume>`
über die bestehende begrenzte Prozessgrenze aus.

Der Prozess erhält leere kontrollierte Umgebung bis auf `LANG=C` und
`LC_ALL=C`, ein temporäres Arbeitsverzeichnis, 60 Sekunden Timeout und
begrenzte Ausgabe.

Volumeabwesenheit oder fremde Composebindung ergibt
`investigation_required`.

Der Resolver mountet oder öffnet das Volume nicht und führt kein SQL aus.

## Ausgangsabbildung

`deletion_review_eligible` benötigt gemeinsam:

- gültige aktuelle Authority und bytegenaue Lineage;
- finalisierten Cleanup ohne spätere Nutzung;
- geschlossene Cleanup-Claims;
- vorhandenes exakt rungebundenes Volume;
- positive Retentionclearance;
- klare Hold-Freiheit;
- alle erforderlichen Backup-/Restoreverifikationen.

Fachlich negatives Retention, aktiver Hold, spätere Nutzung oder noch nicht
positive Recovery ergibt `retain`.

Holdkonflikt, Volumeabwesenheit oder fremde Volumebindung ergibt
`investigation_required`.

Malformed Dateien, Hashabweichung, offene Claims, abgelaufene Authority und
technische Prozessfehler ergeben kein Ergebnisobjekt.

## Detailarme CLI

Der neue Entry Point akzeptiert ausschließlich absolute Eingabepfade,
Projektname und Evidenceverzeichnis.

Bei Erfolg schreibt er nur Schemaversion, feste Operation
`disposable_postgres_volume_disposition` und den kanonischen Ausgang.

Technische Nichtverfügbarkeit endet mit Exitcode zwei ohne stdout oder stderr.

Interne IDs, Hashes, Pfade, Volume-, Backup-, Restore- und Holddetails bleiben
privat.

## Read-only- und Revocationgrenze

Jeder Aufruf liest sämtliche aktuellen Entscheidungen erneut.

Es gibt keinen positiven Cache und kein wiederverwendbares Entscheidungstoken.

Der Resolver schreibt keine Evidence, Claims, Locks, Marker oder Ressourcen.

`deletion_review_eligible` ist weiterhin nur die Zulässigkeit einer separaten
Löschautorisierungsprüfung und keine Mutationserlaubnis.

Eine spätere Löschgrenze muss alle aktuellen Fakten erneut auflösen.

## Tests

Vierzehn Tests prüfen:

- den vollständig positiven Ausgang und den exakten einzigen Docker-argv;
- Retain bei negativer Retention, aktivem Hold, pending Recovery und späterer
  Nutzung;
- Investigation bei Holdkonflikt, Volumeabwesenheit und Fremdbindung;
- fail-closed Hashabweichung, offenen Claim und doppelten JSON-Schlüssel;
- detailarme CLI und installierten Entry Point.

Kein Test mountet, liest oder entfernt ein Volume.

## Bundle und Nichtziele

LQ-390 ergänzt ein Operatormodul und einen Console Entry Point.

Der Bundle-Bestand steigt auf 50 Entry Points und 54 Operatormodule.

Migrationen bleiben 27 mit Head `20260819_0027`.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Domainmodell-,
Compose-, Service-, HTTP- oder Production-Wiring-Änderung.

Der Slice implementiert keine Dispositionspersistenz, Löschautorisierung,
Claimanlage, Reconciliation oder Volumeentfernung.

## Nächster Slice

LQ-391 sollte den separaten owner-only Autorisierungs- und Preflightvertrag für
eine mögliche Volumenlöschung definieren.

Er muss aktuelle Resolverentscheidung, Revocations, exakte Volumeidentität und
einen exklusiven Evidence-first-Claim binden, ohne bereits zu löschen.
