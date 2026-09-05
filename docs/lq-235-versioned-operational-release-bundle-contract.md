# LQ-235 — Versioned Operational Release Bundle Contract

## 1. Ergebnis

LQ-235 entscheidet den Vertrag für ein versioniertes operatives Release-Bundle
nach der in LQ-234 gefundenen Packaging-Lücke.

Das Bundle ist ein separates deterministisches Archiv. Es enthält das
deploybare Wheel, alle freigegebenen owner-only Runbooks, ausgewählte
Release-/Sicherheitsverträge, ein maschinenlesbares Manifest, Checksummen und
Verifikationsevidenz.

Das Runtime-Wheel bleibt schlank. Die Python-Source-Distribution ist weder das
Operationsbundle noch Voraussetzung für dessen Vollständigkeit.

Dieser Slice implementiert noch keinen Builder und erzeugt kein Release.

## 2. Zweck und Audience

Das Bundle richtet sich an kontrollierte Release-, Plattform- und
Security-Operatoren.

Es soll gemeinsam beantworten:

- welcher Source-Commit gebaut wurde;
- welches Wheel deployt werden soll;
- welcher Migration-Head erwartet wird;
- welche Console Entry Points verfügbar sind;
- welche Runbooks für Bootstrap und Management gelten;
- welche Tests und PostgreSQL-Gates bestanden wurden;
- ob Inhalt und Signatur unverändert sind.

Es ist keine öffentliche Endnutzerdokumentation.

## 3. Release-Kandidat versus promotable Bundle

Ein technisch gebautes, aber noch nicht signiertes Archiv ist ausschließlich
ein Release-Kandidat.

Ein Bundle darf erst als promotable bezeichnet werden, wenn:

- es aus einem vollständigen benannten Commit gebaut wurde;
- der Worktree clean war;
- alle Pflichtprüfungen bestanden wurden;
- die Checksummen vollständig verifiziert wurden;
- eine autorisierte Release-Signatur vorliegt;
- die unabhängige Signaturprüfung bestanden wurde.

LQ-235 definiert keine Signierschlüssel oder Personen.

## 4. Kein Build aus uncommitted Zustand

Das Bundle darf nicht aus dem aktuellen uncommitted LQ-233-Handoff erzeugt
werden.

Vor Build müssen Branch und vollständiger Commit existieren. Das Manifest
bindet den vollständigen 40-stelligen Source-Commit.

Untracked, modified oder staged-but-uncommitted Dateien machen den Builder
fail-closed. Es gibt kein `--allow-dirty`-Flag.

## 5. Bundle-Identität

Der Dateiname folgt exakt:

```text
liquent-operations-<package-version>-<short-source-commit>.tar.gz
```

Die Kurzform dient nur der Bedienbarkeit. Das Manifest enthält immer den
vollständigen Commit.

Ein Bundle-Format besitzt zusätzlich eine unabhängige ganzzahlige
`bundle_format_version`, beginnend mit `1`.

## 6. Top-Level-Struktur

Das Archiv besitzt genau einen Top-Level-Ordner mit demselben Namen ohne
`.tar.gz`.

Darunter sind ausschließlich zulässig:

```text
manifest.json
SHA256SUMS
artifacts/
runbooks/
contracts/
evidence/
examples/
```

Unbekannte Top-Level-Einträge machen die Bundle-Prüfung ungültig.

## 7. Deploybares Artefakt

`artifacts/` enthält genau ein Wheel:

```text
liquent-<package-version>-py3-none-any.whl
```

Das Wheel muss aus demselben Source-Commit im selben Release-Workflow gebaut
worden sein.

Eine sdist, ein Containerimage, ein fremdes Wheel oder mehrere
Versionsvarianten sind in Formatversion 1 nicht zulässig.

## 8. Runbook-Inventar

`runbooks/` enthält exakt die freigegebenen Betriebsanleitungen für:

- initialen Identity- und Trust-Authority-Bootstrap;
- OIDC-Trust-Management;
- OIDC-Trust-Authority-Lifecycle;
- OIDC-Trust-Authority-Recovery;
- Workspace-Membership-Management;
- Workspace-Membership-Authority-Lifecycle;
- Workspace-Membership-Authority-Recovery;
- User-Lifecycle;
- Workspace-Lifecycle.

Die Pfade werden im Manifest einzeln mit SHA-256 und Größe aufgeführt.

## 9. Vertragsinventar

`contracts/` enthält keine beliebige Kopie des gesamten `docs/`-Baums.

Formatversion 1 verlangt mindestens:

- den aktuellen LQ-177-Abschlussstatus;
- LQ-197 für den OIDC-Prozessvertrag;
- LQ-211 für Authority-Lifecycle und Recovery;
- LQ-219 für User-/Workspace-Lifecycle;
- LQ-228 für Bootstrap-Revisionsbeobachtbarkeit;
- LQ-231 für PostgreSQL-Verifikation und Readiness;
- LQ-232 für den Release-Handoff-Audit;
- LQ-234 für den Artefakt-Preflight;
- LQ-235 für diesen Bundle-Vertrag.

Historische Slices können zusätzlich aufgenommen werden, müssen dann aber im
Manifest als `historical_context` klassifiziert sein.

## 10. Beispiele

`examples/` darf ausschließlich nicht geheime Vorlagen enthalten.

Formatversion 1 enthält die aktuelle `operations/compose/runtime.env.example`,
sofern der Secret-Scan bestätigt, dass sie nur Platzhalter und keine realen
Credentials enthält.

Private DSN-, Request-, Resultat-, User-ID- oder Recovery-Dateien sind
unzulässig, auch wenn sie aus einer Testumgebung stammen.

## 11. Manifest-Grundfelder

`manifest.json` ist UTF-8-JSON mit sortierten Schlüsseln und ohne
duplikative Keys.

Es enthält mindestens:

- `bundle_format_version`;
- `product_name`;
- `package_name`;
- `package_version`;
- `source_commit`;
- `source_tree_clean`;
- `source_date_epoch`;
- `python_requires`;
- `migration_head`;
- `wheel`;
- `console_entry_points`;
- `runbooks`;
- `contracts`;
- `examples`;
- `verification`;
- `signature_policy`.

Freie unbekannte Felder sind in Formatversion 1 nicht zulässig.

## 12. Wheel-Metadaten im Manifest

`wheel` enthält exakt:

- relativen Pfad;
- SHA-256;
- Bytegröße;
- Wheel-Dateiname;
- Paketversion;
- Anzahl enthaltener Migrationen;
- enthaltenen Migration-Head;
- Anzahl der Operatormodule.

Die Werte werden aus dem gebauten Wheel gelesen, nicht aus Annahmen oder
Quellbaumzählungen übernommen.

## 13. Console Entry Points

`console_entry_points` ist eine lexikografisch sortierte Liste aus Name und
Importziel.

Sie muss exakt mit den Wheel-Metadaten übereinstimmen. Formatversion 1 erwartet
die zwölf durch LQ-234 verifizierten Entry Points.

Fehlt ein Entry Point, existiert ein zusätzlicher oder lässt sich ein Ziel
nicht laden, schlägt der Bundle-Build fehl.

## 14. Migration-Head

`migration_head` muss sowohl aus dem installierten Wheel als auch aus dessen
Alembic-ScriptDirectory bestimmt werden.

Der jeweils im Builder fest gebundene Formatversion-1-Head muss exakt mit dem
aktuellen linearen Paket-Head übereinstimmen. Seit LQ-242 ist dies
`20260817_0019`.

Mehrere Heads, fehlende Migrationen, eine abweichende Manifestangabe oder ein
nicht linear auflösbarer Pfad machen das Bundle ungültig.

## 15. Verifikationsevidenz

`evidence/verification.json` enthält mindestens:

- vollständigen Testcommand ohne DSN-Wert;
- Gesamtzahl bestandener Tests;
- Zahl der PostgreSQL-Integrationstests;
- Warning-Zahl;
- verwendete Python-, pytest-, PostgreSQL-, SQLAlchemy- und psycopg-Version;
- Ergebnis des Wheel-Importchecks;
- Ergebnis des Migration-Checks;
- Ergebnis des Secret-Scans;
- Ergebnis des `git diff --check` vor Commit beziehungsweise staged Gate;
- geprüften Source-Commit.

Hostnamen, Usernamen, Socketpfade, DSNs und Credentials werden nicht erfasst.

## 16. Testevidenz ist kein frei editierter Claim

Der Builder darf Zahlen nicht aus Roadmap oder manueller Eingabe übernehmen.

Die Evidence-Datei muss aus strukturierten Ergebnissen desselben Release-
Workflows entstehen. Ein fehlender Pflichtlauf oder nicht erfolgreiches
Ergebnis blockiert den Kandidaten.

Formatversion 1 verlangt mindestens die LQ-231-Gates: vollständige Suite und
verpflichtende PostgreSQL-Integrationen.

## 17. Checksummen

`SHA256SUMS` enthält für jede reguläre Payload-Datei außer sich selbst und der
externen Signatur genau eine SHA-256-Zeile.

Pfade sind relativ zum Top-Level-Ordner, lexikografisch sortiert und dürfen
keine Symlinks, `..`, absoluten Komponenten oder Unicode-Normalisierungs-
Mehrdeutigkeiten enthalten.

Die Manifestwerte und `SHA256SUMS` müssen für alle gemeinsam erfassten Dateien
übereinstimmen.

## 18. Signaturvertrag

Die autorisierte Release-Signatur wird detached über die exakten Bytes von
`SHA256SUMS` erzeugt.

Signaturdatei und verifizierbare Signeridentität werden neben dem Archiv im
Releasekanal veröffentlicht, nicht als selbstbeglaubigter Inhalt im Archiv.

Das Manifest benennt nur die verlangte Signaturpolicy und den erwarteten
Verifiertyp, niemals private Schlüssel oder geheime Key-Handles.

Ohne erfolgreiche unabhängige Verifikation bleibt das Bundle ein Kandidat.

## 19. Deterministischer Archivbau

Bei identischem Commit, Wheel und Evidence-Input muss der Bundle-Builder
byteidentische Archive erzeugen.

Dafür gelten mindestens:

- lexikografisch sortierte Einträge;
- feste UID und GID `0`;
- leere User- und Groupnamen;
- feste Modi für Verzeichnisse und reguläre Dateien;
- keine Symlinks;
- Mtime aus einem expliziten commitgebundenen `SOURCE_DATE_EPOCH`;
- gzip ohne aktuellen Zeitstempel und Originalpfad;
- kanonisches JSON mit finalem Newline.

Zwei unabhängige Builds müssen denselben SHA-256 liefern.

## 20. Dateimodi

Das Bundle enthält keine Secrets und benötigt deshalb keine eingebetteten
owner-only Credentialmodi.

Verzeichnisse verwenden `0755`, reguläre Dokumente und Artefakte `0644`.

Runbooks verlangen weiterhin, dass reale DSN-, Request- und Resultatdateien
erst im Zielsystem explizit owner-only mit `0600` erzeugt werden.

## 21. Secret- und Datenschutzgrenze

Vor Archivbau wird jeder aufzunehmende Textinhalt und Dateiname gescannt.

Unzulässig sind insbesondere:

- reale DSNs oder Passwörter;
- Access-, API- oder Refresh-Tokens;
- private Schlüssel oder Zertifikatschlüssel;
- Cookie-, Session-, CSRF-, Change- oder Recovery-Werte aus realen Läufen;
- interne Hostnamen, Nutzerverzeichnisse oder temporäre Socketpfade;
- private Operatorresultate;
- Echtdaten oder Research-Datasets.

Ein Treffer blockiert den Build; automatische Schwärzung ist nicht zulässig.

## 22. Keine Environment-Bindung

Das Bundle beschreibt Produkt- und Operatorverträge, aber keine konkrete
Staging- oder Productioninstanz.

Origins, Callback-Ziele, IdP-Endpunkte, Client-IDs, DSNs, Secrets und
Deploymentnamen werden erst in einem separat autorisierten environment-
spezifischen Verfahren gebunden.

Ein Operationsbundle ist deshalb wiederverwendbar, aber nicht selbst
deploybar ohne diese kontrollierten Entscheidungen.

## 23. Verification Command

Ein späterer read-only Verifier muss mindestens:

1. Archivpfad sicher normalisieren;
2. genau einen erwarteten Top-Level-Ordner bestätigen;
3. Symlinks und unbekannte Dateien ablehnen;
4. kanonisches Manifest validieren;
5. alle SHA-256-Werte prüfen;
6. Wheel-Metadaten, Migrationen und Entry Points vergleichen;
7. Runbook- und Vertragsinventar bestätigen;
8. detached Signatur extern prüfen;
9. nur einen detailarmen Erfolg oder Fehler liefern.

Der Verifier extrahiert niemals über das geprüfte Zielverzeichnis hinaus.

## 24. Retention und Nichtüberschreiben

Ein Bundle-Dateiname wird in einem Releasekanal niemals überschrieben.

Änderung irgendeiner Payload, Evidence oder Policy erfordert einen neuen
Source-Commit und ein neues Bundle.

Archiv, `SHA256SUMS`, Signatur und Verification-Evidence werden mindestens so
lange bewahrt, wie irgendein Deployment oder Audit auf diese Version Bezug
nehmen kann.

## 25. Verhältnis zur Source-Distribution

Die sdist bleibt ein Python-Quellartefakt und darf unabhängig verbessert
werden.

Formatversion 1 nimmt sie bewusst nicht in das Operationsbundle auf, weil sie
in LQ-234 weder deterministisch noch operationsvollständig war und für die
Runtimeinstallation nicht benötigt wird.

Ein späterer Vertrag kann sie ergänzen, muss dann eigene Hash-, Inhalts- und
Reproduzierbarkeitsregeln definieren.

## 26. Fehlergrenze

Fehlende Dateien, unbekannte Shapes, Hashabweichung, dirty Source, falscher
Commit, Buildfehler, nicht reproduzierbares Archiv, Secret-Treffer oder
fehlende Pflichtprüfung lassen keinen promotable Output zurück.

Temporäre Dateien werden nur in einem eindeutig besessenen Buildverzeichnis
erzeugt und bei Fehler kontrolliert entfernt.

Fehlerausgaben dürfen keine gescannten Secretwerte, DSNs oder privaten
Dateiinhalte wiederholen.

## 27. Bewusst nicht enthalten

LQ-235 entscheidet keine:

- konkrete Builder- oder Verifier-Sprache;
- Signiertechnologie, Key-ID oder verantwortliche Person;
- Versionssteigerung oder Release-Tag;
- Containerimage-, Helm- oder Deploymentbundle-Struktur;
- SBOM für ein konkretes Runtimeimage;
- Source-Distribution-Änderung;
- Branch-, Staging-, Commit-, Push- oder PR-Aktion;
- Registry-, Release- oder Deployment-Publikation.

## 28. Nächster Slice

LQ-236 soll einen lokalen, nicht publizierenden Builder und read-only Verifier
für Bundle-Formatversion 1 implementieren.

Er muss in temporären Verzeichnissen arbeiten, dirty Worktrees standardmäßig
ablehnen, für Tests einen expliziten injizierten Source-Snapshot verwenden,
deterministische Doppelbuilds belegen und keine Signatur oder Production-
Promotion vortäuschen.
