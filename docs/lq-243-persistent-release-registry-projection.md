# LQ-243 — Persistent Release Registry Projection

## Ergebnis

LQ-243 implementiert eine parameterlose read-only Projektion der aktuellen
persistent gespeicherten Release-Authority-Registry in das geschlossene
LQ-238-JSON-Format.

Die Projektion mutiert keine Registry und gewährt selbst keine Authority.

## Kontrollierte Verification-Identität

`ReleasePromotionVerifierId` ist ein eigener stabiler, repr-freier ID-Typ und
wird beim Aufbau des Adapters injiziert.

Der Aufruf `project()` akzeptiert keine Parameter. Caller können deshalb weder
Verification-Identität noch Authority, Key, Status, Rolle oder Allow-Wert pro
Entscheidung überschreiben.

Die sichere Materialerzeugung unterstützt den neuen ID-Typ mit einem
unabhängigen Zufallszug.

## Aktueller System-of-Record-Snapshot

Jeder Aufruf liest neu:

- Current-Pointer;
- Registry- und Policy-Revision;
- vollständige Signer-Authority-Member;
- vollständige Lifecycle-Authority-Member;
- vollständige Key-Member;
- unveränderliche Public-Key-Fakten.

Es gibt keinen positiven Cache. Eine committierte Aktivierung, Deaktivierung,
Expiry oder Revocation wirkt auf den nächsten Export.

## Konsistente Lesetransaktion

PostgreSQL verwendet `REPEATABLE READ`, SQLite `SERIALIZABLE`.

Current-Pointer, Member, Public Keys und Inventarzahlen stammen damit aus
derselben Lesesicht. Ein paralleler Lifecycle-Commit kann keine gemischte
Projektion aus alter Revision und neuen Membern erzeugen.

## Vollständigkeitsprüfung

Die Projektion vergleicht die Anzahl aller stabilen Signer-, Lifecycle- und
Key-Fakten mit den Membern der aktuellen Revision.

Zusätzlich prüft sie:

- eindeutige Authority- und Key-IDs;
- eindeutige Fingerprints;
- gültige Authority-, Key- und Policy-Status;
- exakte Key-/Signer-Zuordnung;
- festen Ed25519-Algorithmus;
- Namespace `liquent-operations-release-v1`;
- kanonischen Fingerprint und einzeiligen Public Key;
- mindestens eine bekannte Signer- und Lifecycle-Authority.

Teilbestand oder beschädigte Struktur wird nicht stillschweigend ausgelassen.

## Geschlossenes Ausgabeformat

Die Ausgabe enthält exakt:

- `schema_version`;
- `policy_revision`;
- `policy_status`;
- `verification_identity`;
- sortierte `authorities` mit Status und sortierten Keys.

Jeder Key bindet Key-ID, Status, Fingerprint, Algorithmus, Namespace-Liste und
Public Key.

Lifecycle-Authorities werden zur Vollständigkeitsprüfung gelesen, aber nicht
in den für Signaturprüfung minimalen LQ-238-Trust-Root exportiert.

## Kanonische Bytes

JSON-Schlüssel und Inventare sind deterministisch sortiert. Die Ausgabe
verwendet kompakte Separatoren, ASCII-sichere Kodierung und genau ein finales
Newline.

Die Bytes werden vom bestehenden geschlossenen LQ-238-Registryparser direkt
akzeptiert.

## Interne ID-Kompatibilität

Sicher erzeugte URL-safe IDs können Großbuchstaben enthalten. Der
LQ-238-Identifier-Parser akzeptiert deshalb nun denselben begrenzten URL-safe
Zeichensatz wie die persistenten internen IDs.

IDs werden weder kleingeschrieben noch gehasht, umgedeutet oder unter einer
zweiten externen Identität wiederverwendet.

## Abwesenheit und Fehler

Fehlender Current-Pointer vor Bootstrap liefert neutral `None`.

Unlesbare Datenbank, fehlende Tabellen, ungültige Encodings, Teilinventar oder
inkonsistente persistente Fakten ergeben ausschließlich
`ReleaseRegistryProjectionUnavailable`.

Die Exception enthält keine IDs, Keys, Fingerprints, SQL-, Tabellen-, Host-
oder DSN-Details.

## Nachweis

SQLite-Tests belegen neutrale Abwesenheit, kanonische LQ-238-kompatible Bytes,
vollständigen Bootstrap-Snapshot, aktuelle Sicht nach Key-Aktivierung,
Teilbestandsablehnung und detailarme technische Nichtverfügbarkeit.

Ein PostgreSQL-16-Test bestätigt den vollständigen Export aus einer frisch
migrierten und gebootstrappten Registry unter Repeatable Read.

Die vollständige Pflichtsuite besteht:

```text
3015 passed, 53 warnings
```

Der temporäre PostgreSQL-Cluster wurde kontrolliert gestoppt und vollständig
entfernt.

## Bewusst nicht enthalten

LQ-243 schreibt keine Registry-Datei und ändert die bestehende LQ-238-CLI noch
nicht auf direkte Datenbankverwendung um. Es gibt keine Registry-Mutation,
Key-Aktivierung, Signatur, Promotion, Veröffentlichung, Deployment oder
Git-Aktion.

## Nächster Slice

LQ-244 sollte die persistente Projektion direkt mit der LQ-238-
Promotionprüfung komponieren. Die Verifikation muss Registry-Bytes aus genau
einer aktuellen Projektion verwenden, ohne temporäre caller-kontrollierte
Registry-Datei oder zweiten Authority-Lookup.
