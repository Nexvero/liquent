# LQ-236 — Local Operational Release Bundle Builder and Verifier

## 1. Ergebnis

LQ-236 implementiert den lokalen, nicht publizierenden Builder und den
read-only Verifier für das in LQ-235 entschiedene Operationsbundle der
Formatversion 1.

Der Builder erzeugt ausschließlich einen unsignierten Release-Kandidaten. Der
Verifier bestätigt lokale Integrität, bezeichnet den Kandidaten aber immer als
nicht signaturgeprüft und nicht promotable.

Dieser Slice baut bewusst kein Bundle aus dem aktuellen Worktree: Der
kumulative LQ-183-bis-LQ-236-Stand ist noch uncommitted und muss deshalb am
normalen Clean-Source-Gate scheitern.

## 2. Lokales Werkzeug

`tools/operational_release_bundle.py` stellt zwei Operationen bereit:

```text
build
verify
```

Beide arbeiten ausschließlich auf lokalen Dateien. Es gibt keinen Upload,
keinen Registryzugriff, kein Signing, keinen Tag und kein Deployment.

Das Werkzeug benötigt nur die Python-Standardbibliothek.

## 3. Build-Eingaben

Der normale Build verlangt explizit:

- den Source-Root;
- genau ein Wheel;
- genau eine strukturierte Evidence-Datei;
- ein Output-Verzeichnis;
- den vollständigen 40-stelligen Source-Commit;
- einen nicht negativen `SOURCE_DATE_EPOCH`-Wert.

Es gibt keinen impliziten Commit, keine aktuelle Uhrzeit und kein
`--allow-dirty`.

## 4. Clean-Source-Gate

Vor jedem normalen Build liest das Werkzeug den aktuellen Git-Commit und den
vollständigen Porcelain-Status einschließlich untracked Dateien.

Der Build wird detailarm abgelehnt, wenn:

- der Root kein lesbares Git-Repository ist;
- `HEAD` nicht exakt dem übergebenen Commit entspricht;
- staged, modified oder untracked Inhalte vorhanden sind.

Damit kann der aktuelle kumulative Worktree keinen scheinbaren Release-
Kandidaten erzeugen.

## 5. Expliziter Test-Snapshot

Die Python-Funktion besitzt ausschließlich für Tests eine explizite
`enforce_clean_source=False`-Naht.

Sie ist kein CLI-Flag und deshalb kein Operator-Bypass. Tests geben einen
vollständig isolierten Source-Snapshot, ein strukturell echtes synthetisches
Wheel und Evidence desselben Fixture-Commits vor.

Der produktive CLI-Pfad aktiviert immer das Clean-Source-Gate.

## 6. Exaktes Payload-Inventar

Der Builder nimmt genau auf:

- ein Wheel unter `artifacts/`;
- die neun in LQ-235 benannten Runbooks;
- die neun erforderlichen Release- und Sicherheitsverträge;
- `runtime.env.example` unter `examples/`;
- `verification.json` unter `evidence/`;
- das erzeugte kanonische Manifest;
- `SHA256SUMS`.

Optionale historische Verträge werden in Formatversion 1 noch nicht
implementiert. Fehlende oder zusätzliche Archivdateien werden abgelehnt.

## 7. Wheel-Prüfung beim Build

Das Wheel wird direkt als ZIP gelesen. Der Builder bestätigt:

- Paketname `liquent`;
- gültige dreiteilige Paketversion;
- vorhandenes `Requires-Python`;
- exakt eine METADATA- und eine Entry-Point-Datei;
- exakt zwölf lexikografisch sortierte Console Entry Points;
- exakt neunzehn Migrationen;
- genau eine lineare Migration-Root und einen Head;
- vollständige Erreichbarkeit aller Migrationen vom Head;
- erwarteten Head `20260817_0019`;
- exakt zehn Operatormodule;
- exakten Wheel-Namen `liquent-<version>-py3-none-any.whl`.

Der Slice installiert oder führt das Wheel nicht erneut aus. Der gebundene
Importcheck bleibt Teil der strukturierten Release-Evidence aus dem
vorgelagerten Wheel-Workflow.

## 8. Evidence-Prüfung

`verification.json` besitzt in Formatversion 1 ein geschlossenes Schema.

Verlangt werden:

- Schema-Version 1;
- derselbe vollständige Source-Commit;
- ein nicht leerer Testcommand ohne DSN-Wert;
- positive Gesamt- und PostgreSQL-Testzahlen;
- eine nicht negative Warning-Zahl;
- Python-, pytest-, PostgreSQL-, SQLAlchemy- und psycopg-Versionen;
- `passed` für Wheel-Import, Migration, Secret-Scan und Diff-Gate.

Unbekannte oder fehlende Felder und eingebettete URL-/DSN-Werte werden
abgelehnt.

## 9. Secret- und Pfadprüfung

Vor Archivbau prüft der Builder alle Payloadnamen und Bytes auf die in LQ-235
relevanten offensichtlichen Geheimnis- und Hostbindungsmuster.

Unter anderem blockieren:

- Private-Key-Marker;
- bekannte Access-Token-Formen;
- absolute Nutzerverzeichnisse;
- Liquent-spezifische temporäre Pfade;
- absolute oder traversierende Archivpfade.

Ein Treffer wird nicht wiederholt und nicht automatisch geschwärzt.

## 10. Kanonisches Manifest

Das Manifest verwendet geschlossen validierte Felder und kanonisches JSON:

- sortierte Schlüssel;
- kompakte Separatoren;
- ASCII-sichere Kodierung;
- genau ein finales Newline.

Es bindet Commit, Paketversion, Python-Anforderung, Migration-Head,
Wheel-Inhalt, Entry Points, jedes Dokument, das Beispiel und die Evidence per
SHA-256 und Bytegröße.

`source_date_epoch` ist als reproduzierbarer Archivzeitpunkt explizit an das
Manifest gebunden.

## 11. Deterministisches Archiv

Der Builder schreibt einen Top-Level-Ordner und alle Einträge
lexikografisch sortiert.

Er setzt:

- UID und GID auf `0`;
- User- und Groupnamen auf leer;
- Verzeichnisse auf `0755`;
- reguläre Dateien auf `0644`;
- jede Mtime auf den übergebenen Epoch-Wert;
- gzip-Dateiname auf leer;
- gzip-Mtime auf denselben Epoch-Wert.

Der Test baut denselben Input in zwei getrennten Verzeichnissen und bestätigt
byteidentische Archive.

## 12. Kein Überschreiben

Das finale Archiv wird exklusiv erzeugt. Existiert der Zielname bereits, wird
der Build abgelehnt und der vorhandene Kandidat bleibt bytegenau unverändert.

Der Builder schreibt zuerst eine eindeutig benannte temporäre Datei im
Zielverzeichnis und ersetzt erst nach erfolgreichem Abschluss den noch nicht
existierenden finalen Pfad.

Bei Fehlern wird eigener temporärer Output entfernt.

## 13. Read-only Verification

Der Verifier liest das gzip/tar-Archiv vollständig ohne Extraktion in einen
Zielbaum.

Er bestätigt:

- genau einen zum Dateinamen passenden Top-Level-Ordner;
- nur erwartete Verzeichnisse und Dateien;
- keine Symlinks, Hardlinks oder Spezialdateien;
- sichere relative Pfade;
- exakte Modi und eine einheitliche gebundene Mtime;
- kanonische Manifestbytes;
- geschlossenes Manifest-Schema;
- sortierte und vollständige `SHA256SUMS`;
- alle Payload-Hashes und Größen;
- Wheel-, Migration-, Operator- und Entry-Point-Metadaten;
- Runbook-, Vertrags-, Beispiel- und Evidence-Inventar;
- dieselbe unsigned-candidate-Signaturpolicy.

Eine manipulierte Payload mit alter Checksumme und ein unbekanntes leeres
Verzeichnis werden in den Tests fail-closed abgelehnt.

## 14. Signatur- und Promotionsergebnis

Ein erfolgreicher lokaler Verify liefert ausdrücklich:

```text
integrity = verified
signature = not_verified
promotable = false
```

Der Verifier akzeptiert keine caller-supplied Signaturentscheidung und
behauptet keine externe Vertrauenskette.

Detached Signing und unabhängige Signaturprüfung bleiben ein eigener späterer
Slice.

## 15. Fehlergrenze

Alle Inhalts-, Struktur-, Git-, Hash- und Metadatenfehler werden an der CLI als
ein detailarmer Ablehnungsgrund mit Exitcode `2` sichtbar.

Dateiinhalte, Hashabweichungsdetails, lokale Pfade, DSNs und vermutete Secrets
werden nicht ausgegeben.

Programmatic callers erhalten ausschließlich `BundleRejected` mit derselben
neutralen Meldung.

## 16. Verifikation

LQ-236 ergänzt acht gezielte Tests für:

- deterministischen Doppelbuild;
- vollständige erfolgreiche lokale Integritätsprüfung;
- explizit nicht promotable unsigned Resultate;
- Hashmanipulation;
- unbekannte Archivverzeichnisse;
- Secret-förmige Payload;
- falschen Wheel-Namen und getrennte Migration-Roots;
- dirty Git-Source, Überschreibschutz und detailarme CLI-Ablehnung.

Ergebnis:

```text
8 passed
```

Die vollständige datenbankunabhängige Suite bleibt grün:

```text
2821 passed, 74 skipped, 53 warnings
```

Die PostgreSQL-Pflichtsuite wurde in diesem Slice nicht erneut gestartet. Ihre
letzte vollständige Readiness-Evidence bleibt die in LQ-231 dokumentierte
Prüfung; LQ-236 verändert keine Datenbank-, Runtime- oder Migrationslogik.

## 17. Bewusst nicht enthalten

LQ-236 entscheidet oder vollzieht keine:

- Signiertechnologie oder Signeridentität;
- Promotion eines Kandidaten;
- Erzeugung eines Bundles aus dirty Source;
- Paketversionssteigerung oder Release-Tag;
- Wheel-, sdist- oder Containerpublikation;
- SBOM oder Provenance-Attestation;
- Registry-, Environment- oder Deploymentbindung;
- Git-Staging-, Branch-, Commit-, Push- oder Pull-Request-Aktion.

## 18. Nächster Slice

LQ-237 sollte den unabhängigen detached-Signatur- und Promotion-Vertrag
entscheiden.

Er muss Signer-Autorität, Signaturformat, Key-Rotation, Revocation,
unabhängige Verification-Evidence und die Trennung zwischen technisch
integrem Kandidaten und autorisiert promotablem Release festlegen, ohne in
diesem Vertrag bereits Schlüssel oder Production-Publikation zu erzeugen.
