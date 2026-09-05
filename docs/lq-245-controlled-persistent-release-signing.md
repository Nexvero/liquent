# LQ-245 — Controlled Persistent Release Signing

## Ergebnis

LQ-245 implementiert die kontrollierte persistente Signing-Entscheidung für
einen technisch vollständigen LQ-236-Release-Kandidaten.

Die Grenze bindet jede neue Signatur atomar an die aktuelle persistente
Release-Authority-Registry. Sie promotet, veröffentlicht und deployt nichts.

## Getrennte Identitäten

`ReleaseSigningExecutorId` bezeichnet stabil die kontrollierte ausführende
Signing-Identität. Der Typ ist repr-frei und wird beim Aufbau des Adapters
injiziert.

Executor-Identität, Signer-Authority und spätere Promotion-Verification-
Identität bleiben getrennte Fakten. Weder SessionPrincipal, Produktrolle,
Workspace-Mitgliedschaft noch Research-Permission gewährt Signing-Authority.

## Geschlossener Request

Ein Signing-Aufruf enthält ausschließlich:

- neue oder exakt wiederholte `ReleaseSigningDecisionId`;
- ausgewählte stabile `ReleaseSigningKeyId`;
- exakt erwartete `ReleaseRegistrySetRevisionId`;
- lokalen Pfad zum unveränderten LQ-236-Bundle.

Der Caller liefert keine Authority-ID, Policy, Rolle, Status, Public-Key-
Datei, Fingerprint-, Namespace-, Algorithmus-, Allow- oder Promotionangabe.

Key-Provider, Signaturverifier, Executor-Identität und Clock werden beim
Adapteraufbau kontrolliert injiziert.

## Ein Bundle-Snapshot

Die Grenze liest das Bundle einmal in Bytes und prüft eine private temporäre
Kopie mit dem vollständigen LQ-236-Verifier.

Die exakten `SHA256SUMS`-Bytes werden aus demselben In-Memory-Snapshot
extrahiert. Bundle-Hash, Checksum-Hash, Manifestdaten und Signaturnutzlast
beziehen sich deshalb auf denselben Kandidaten.

Ein ungültiges, umbenanntes, unvollständiges oder nicht reguläres Bundle endet
vor Providerzugriff detailarm technisch nicht verfügbar.

## Aktuelle Authority-Auflösung

Für jede neue Entscheidung löst dieselbe Datenbanktransaktion auf:

- den exakt erwarteten aktuellen Registry-Pointer;
- aktive Policy und gebundene Policy-Revision;
- genau den ausgewählten aktiven Key;
- seine unveränderliche Signer-Zuordnung;
- aktive Signer-Authority;
- Algorithmus `ssh-ed25519`;
- Namespace `liquent-operations-release-v1`;
- Registry-Fingerprint und Public Key.

Unbekannter Key, stale Revision, inaktive Authority, inaktiver, abgelaufener
oder widerrufener Key sowie inaktive Policy liefern neutral `None` und keinen
Providerzugriff.

## Providerbindung

`ReleaseSigningKeyProvider` gibt seinen aktuellen Public-Key-Fingerprint aus
und signiert ausschließlich explizite Payloadbytes unter explizitem
Namespace.

Der Provider erhält weder Registry-Snapshot noch Bundle, Datenbankzugang,
Authority-Entscheidung oder Promotionkontext.

Nur wenn sein Fingerprint exakt dem aktuellen persistenten Registry-Fakt
entspricht, erhält er die `SHA256SUMS`-Bytes. Abweichung endet neutral vor
Signierung.

Private Schlüssel, Provider-Credentials und Handles werden nie persistiert
oder in Evidence aufgenommen.

## Unabhängige lokale Verifikation

Das Providerergebnis gilt nicht allein als Erfolg.

Ein getrennt injizierter `ReleaseSignatureVerifier` prüft Public Key,
aufgelöste Signer-Authority, exakte Checksumbytes und Signatur. Nur ein
explizites `True` erlaubt die persistente Entscheidung.

Provider- oder Verifierfehler, leere Signatur und negatives Verify-Ergebnis
führen detailarm zur technischen Nichtverfügbarkeit und rollen die
Transaktion zurück.

## Persistente Entscheidung

Die bereits in LQ-240 angelegte Tabelle `release_signing_decisions` speichert
atomar:

- Decision-, Bundle-, Checksum- und Signaturbindung;
- Source-Commit und Paketversion;
- Signer-Authority, Key und Fingerprint;
- Registry- und Policy-Revision;
- Signaturformat und Namespace;
- Executor-Identität und UTC-Zeit;
- verifizierte Signaturbytes;
- kanonische detailarme Evidence-Bytes.

LQ-245 benötigt keine neue Tabelle und keine Migration. Der lineare Head
bleibt `20260817_0019`.

## Kanonische Evidence

Evidence ist kanonisches kompaktes JSON mit sortierten Schlüsseln und genau
einem finalen Newline.

Sie enthält nur gebundene öffentliche Entscheidungsfakten und das Ergebnis
`signed`. Sie enthält keine privaten Keys, Providerdaten, DSN, SQL,
Hostpfade, Registry-Inventare oder ursprünglichen Fehlerdetails.

## Exakter Retry

Eine bereits persistierte Decision-ID wird vor aktuellem Authority- oder
Providerzugriff aufgelöst.

Stimmen Bundle-Hash, Key-ID und erwartete Registry-Revision exakt überein,
liefert der Adapter dieselben persistierten Signatur- und Evidence-Bytes.
Provider, Verifier und Clock werden nicht erneut verwendet.

Abweichende Wiederverwendung derselben Decision-ID ist
`ReleaseSigningConflict` und erzeugt keine zweite Entscheidung.

Spätere Revocation ändert historische Signing-Evidence nicht, sperrt aber
neue Signing- und über LQ-244 auch neue Promotionentscheidungen.

## Konkurrenz und Commit

PostgreSQL sperrt Current-Registry, Revision, Signer-, Key- und Decision-
Bestände in einer festen Transaktionsreihenfolge.

Damit gewinnt eine konkurrierende Statusmutation entweder vor dem Signing und
sperrt es oder nach dem vollständig committeten Signing. SQLite bleibt für
lokale Nachweise auf seiner serialisierten Schreibtransaktion begrenzt.

## Rückgabewert und Fehlergrenzen

`SignedReleaseCandidate` enthält ausschließlich Decision-ID, Signaturbytes
und Evidence-Bytes.

Fachliche fehlende aktuelle Authority liefert neutral `None`. Abweichende
ID-Wiederverwendung ist ein detailarmer Konflikt. Bundle-, Registry-,
Transaktions-, Provider-, Verifier-, Clock- und Strukturfehler sind
detailarme technische Nichtverfügbarkeit.

Keine Fehlerkette transportiert interne Provider-, Datei-, Datenbank- oder
Registrydetails nach außen.

## Nachweis

Gezielte Tests belegen aktuelle Authority-Auflösung, Snapshotbindung,
Provider-Fingerprint, unabhängige Verifikation, persistente kanonische
Evidence, neutralen stale-/Fingerprint-Fail-Closed-Pfad, exakten Retry,
Decision-ID-Konflikt und rollback-sichere technische Fehler.

Die vollständige Pflichtsuite besteht mit echtem PostgreSQL 16:

```text
3027 passed, 56 warnings
```

Der temporäre PostgreSQL-Cluster wurde kontrolliert gestoppt und entfernt.

## Bewusst nicht enthalten

LQ-245 materialisiert keine Signatur- oder Evidence-Datei und implementiert
keine CLI. Damit wird keine nicht vorhandene Atomarität zwischen Datenbank und
Dateisystem behauptet.

Es gibt keine Registry- oder Key-Mutation, Lifecycle-Operation, private
Key-Technologie, Promotion, Veröffentlichung, Deployment, Git-Aktion oder
automatische CI-/Production-Verdrahtung.

## Nächster Slice

LQ-246 sollte den kontrollierten owner-only Signing-Operator und die exklusive
Dateimaterialisierung implementieren. Er muss einen exakten Retry aus der
persistierten Entscheidung wiederherstellen, vorhandene Zielpfade niemals
überschreiben und halbe Filesystemausgaben sicher bereinigen, ohne Promotion
oder Veröffentlichung auszuführen.
