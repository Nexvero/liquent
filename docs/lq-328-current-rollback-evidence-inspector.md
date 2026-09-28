# LQ-328 — Current Rollback Evidence Inspector

## Ergebnis

LQ-328 installiert `liquent-rollback-evidence-inspect` als lokalen strikt
read-only Inspector für die LQ-303-Phase `rollback`.

Der Command vergleicht eine private autorisierte Erwartungsbindung mit einer
privaten unveränderlichen Backup-/Restore-/Application-Rollback-Evidence und
gibt ausschließlich das Boolean-Faktum `rollback_current` aus.

Er führt keinen Application- oder Datenbankrollback, kein Restore und keinen
Dockerzugriff aus.

## Zwei private Eingaben

Der Inspector akzeptiert ausschließlich:

- `--expectation-file`;
- `--evidence-file`.

Beide Dateien laufen durch die bestehende owner-only Grenze: regulär, kein
Symlink, aktueller Owner, Linkcount eins, Modus 0400 oder 0600 und feste
Größenlimits.

Es gibt keinen Environmentfallback, stdin-Payload, freien Digest, Pfadwert im
JSON oder caller-gelieferten Allow-Boolean.

## Autorisierte Erwartungsbindung

Die geschlossene Erwartungsdatei bindet:

- Schema-Version, Run-ID und Environment exakt `staging`;
- Source-Commit und unveränderlichen Kandidaten-Image-Digest;
- SHA-256 der vollständigen Rollback-Evidence-Datei;
- getrennte Executor- und Autorisiereridentitäten;
- aktuelles UTC-Gültigkeitsfenster.

Unbekannte Felder, doppelte Schlüssel, mutable Images, ungültige IDs, gleiche
Identitäten oder strukturell ungültige Zeitwerte sind technisch unavailable.

Eine abgelaufene oder noch nicht gültige, aber strukturell korrekte Erwartung
ergibt neutrales `false`.

## Geschlossene Rollback-Evidence

Die Evidence bindet exakt:

- staging Environment und Source-Commit;
- Kandidaten-Image-Digest;
- vorherigen gesunden Application-Digest;
- identischen expliziten Rollback-Zieldigest;
- opake Backup-/Snapshotreferenz;
- lowercase SHA-256 der Backup- und Restore-Evidence;
- Erzeugungs-, Verifikations- und Gültigkeitszeit in UTC;
- getrennte vorbereitende und prüfende Identitäten;
- Status exakt `verified`.

Der vorherige gesunde Digest muss sich vom Kandidaten unterscheiden. Ein
Rollback auf denselben Kandidaten ist keine gültige Rückfalloption.

## Hash-first und Strukturprüfung

Zuerst muss der SHA-256 der exakten Evidencebytes mit der autorisierten
Erwartung übereinstimmen. Eine byteweise Änderung ergibt neutrales `false`.

Bei passendem Hash wird das JSON mit Duplikatschlüsselerkennung und exakt
geschlossener Feldmenge dekodiert.

Malformed JSON, unbekannte Felder, falsche Typen, ungültige ID-/Digestformen
oder technisch nicht lesbare Dateien sind unavailable und erzeugen kein
Boolean-Evidenceobjekt.

## Frische- und Bindungsentscheidung

`rollback_current=true` verlangt gemeinsam:

- aktuelle Erwartungsautorisierung;
- bytegenau gebundene Evidence;
- Environment, Source und Kandidat passend zur Erwartung;
- Status `verified`;
- vorheriger gesunder Digest gleich explizitem Rollbackziel;
- unterschiedliche Evidence-Identitäten;
- `created_at <= verified_at <= now <= evidence.valid_until`;
- Evidence-Gültigkeit nicht länger als die Erwartungsautorisierung.

Ein eindeutig veralteter Status, abgelaufene Evidence, Bindungsmismatch,
gleiche Identitäten oder unbrauchbares Rollbackziel ergibt neutrales `false`.

Der Inspector prüft keine reale Registry, kein Backupziel, keine Datenbank und
keinen laufenden Stagingdienst. Er bewertet ausschließlich die autorisierten
unveränderlichen Evidencebytes.

## Neutrale Ausgabe

Erfolg schreibt exakt das kanonische LQ-310-Phasenschema mit:

- `schema_version: 1`;
- `phase: rollback`;
- `facts.rollback_current: true | false`.

Run-, Snapshot-, Image-, Evidence-, Digest-, Zeit-, Identitäts- und Pfadwerte
werden nicht ausgegeben.

Technische Nichtverfügbarkeit endet still mit Exitcode zwei und ohne
stdout/stderr.

## Keine Rollbackwirkung

Der Command besitzt keine Prozess-, Docker-, Compose-, Netzwerk-, SQL-,
Filesystem-Write- oder Signalfähigkeit.

Insbesondere gibt es kein `alembic downgrade`, Restore, Datenbankdrop,
Volumeaustausch, Imagewechsel oder Promotion.

`rollback_current=true` bedeutet nur, dass aktuelle gebundene Evidence für
einen späteren kontrollierten Application-Rollback vorhanden ist. Es führt ihn
nicht aus und autorisiert keine Productionaktion.

## Tests

Lokale Tests prüfen gültige aktuelle Evidence, exakten kanonischen Output,
stale Status, Source-Mismatch, unbrauchbares Ziel, gleiche Identitäten,
abgelaufene Evidence und Evidence-Hashabweichung.

Doppelte JSON-Schlüssel und breite Dateirechte enden unavailable. Alle Uhren
sind injiziert; es gibt keinen realen Backup-, Docker- oder Datenbankzugriff.

## Bundle und Nichtziele

Der neue Entry Point und das Operatormodul erhöhen die Gates auf 30 Entry
Points und 33 Operatormodule. Migrationen bleiben 27 mit Head
`20260819_0027`.

LQ-328 enthält noch keine Composition in `liquent-staging-phase-probe`, keine
Änderung der LQ-305-Run-Autorisierung, keine Signaturprüfung, keine konkrete
Frischepolicy außerhalb der gebundenen Zeiten und keine Schema-, SQL-,
Migration-, Port-, Compose- oder Production-Wiring-Änderung.

## Nächster Slice

LQ-329 sollte den Inspector kontrolliert in die Staging-Probe komponieren. Die
Composition muss Erwartung und Evidence als zusätzliche owner-only gebundene
Inputs erhalten, darf keinen Dockerprozess starten und muss den neutralen
LQ-328-Output über LQ-308 reduzieren.
