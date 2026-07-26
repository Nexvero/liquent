# LQ-061 — Backup, Restore and Recovery Contract

## Status

- Restic-/PostgreSQL-Backupablauf und getrennte Retention implementiert.
- Restore-Verifikation verweigert bestehende Ziele und prüft Dumpintegrität.
- Compose-Operations-Profil und dateibasierte Secretgrenzen ergänzt.
- Recovery-Runbook mit Freigaben, RPO/RTO und Fehlerpfaden dokumentiert.
- Lokale Konfigurations-/Sicherheitstests bestanden.
- Echter OVH-Offsite-Backup- und isolierter Restore-Nachweis noch offen.

## 1. Sicherungseinheit

Ein erfolgreicher Snapshot enthält gemeinsam:

- PostgreSQL-Custom-Format-Dump,
- SHA-256 und Migrationsrevision im Manifest,
- unveränderliches Artefaktvolume,
- feste Host- und Production-Tags.

Die Datenbank wird nicht durch Kopieren ihres laufenden Volumes gesichert.
`pg_dump` erzeugt einen logischen, versionsgeeigneten Export. Das Passwort liegt
in einer owner-only `.pgpass`-Datei und erscheint nicht als Kommandoargument.

## 2. Secret- und Repositorygrenze

- Restic-Passwort, S3 Access Key, S3 Secret und `.pgpass` sind getrennte
  dateibasierte Secrets.
- Secretdateien dürfen keine Symlinks sein und keine Group-/Other-Rechte haben.
- Das Repository muss `s3:https://` verwenden.
- Credentials werden erst unmittelbar vor Restic in den kurzlebigen
  Backup-Prozess geladen und niemals ausgegeben.
- Backupidentität erhält nur erforderliche Bucketrechte, keine OVH-Adminrechte.

Restic verschlüsselt clientseitig. Der Restic-Schlüssel wird getrennt vom Bucket
verwahrt; ohne ihn ist das Backup nicht wiederherstellbar.

## 3. Ablauf und Retention

```text
pg_dump → SHA-256/Manifest → gemeinsamer Restic Snapshot → restic check
                                                       ↓
                         separater Retention-Job mit explizitem --apply
```

Retention: 7 tägliche, 4 wöchentliche und 6 monatliche Snapshots. `forget` und
`prune` laufen nicht implizit im täglichen Backup. Bei einem Repositoryfehler
wird keine Retention ausgeführt.

## 4. Restore-Sicherheitsmodell

`restore-verify.sh` akzeptiert nur einen absoluten, noch nicht existierenden
Zielpfad außerhalb `/`. Nach dem Restore werden Manifest, Dump-SHA-256 und
`pg_restore --list` geprüft. Es importiert niemals automatisch in eine
Datenbank und verändert keine Production-Volumes.

Ein vollständiger Nachweis benötigt danach eine isolierte PostgreSQL-18-Instanz,
das passende Application-Artefakt, deaktivierten Egress und fachliche
Stichproben. Erst diese Prüfung belegt RPO und RTO.

## 5. Noch offenes Go-live-Gate

Die Implementierung ist lokal verifiziert, aber kein echter Recovery-Nachweis.
Vor Slice-1-Production sind zwingend:

1. privaten OVH-S3-Bucket und Least-Privilege-Identität anlegen,
2. Restic-Repository initialisieren und Schlüsselverwahrung verifizieren,
3. freigegebenes Backupimage bauen und scannen,
4. ersten echten Snapshot mit protokollierter ID erzeugen,
5. Snapshot in isolierte Umgebung zurückspielen,
6. Datenbank importieren und App-/Referenz-/Berechtigungsstichproben bestehen,
7. tatsächliches RPO/RTO und Abweichungen dokumentieren,
8. Alarm für Backupalter über 24 Stunden aktivieren.

## 6. Definition of Done dieser Repository-Phase

- Backup-, Retention- und Restorepfad sind getrennt und fail-closed.
- Secrets sind außerhalb Git und nicht in Argumenten/Logs.
- Restore kann Production nicht implizit überschreiben.
- Retention entspricht LQ-054.
- Runbook benennt vollständigen praktischen Nachweis.
- Gesamte Testsuite bleibt grün.
- Slice 0 bleibt bis zum realen Offsite-/Restore-Test noch nicht go-live-fähig.
