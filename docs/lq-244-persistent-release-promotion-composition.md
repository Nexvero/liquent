# LQ-244 — Persistent Release Promotion Composition

## Ergebnis

LQ-244 komponiert die aktuelle persistente LQ-243-Registry-Projektion direkt
mit der read-only LQ-238-Promotionprüfung.

Die neue Grenze benötigt keine Registry-Datei und akzeptiert keine vom Caller
gelieferten Authority-, Status-, Rollen- oder Allow-Fakten.

## Geschlossene Eingaben

Der Aufruf erhält ausschließlich:

- den Pfad des unveränderlichen LQ-236-Bundle-Kandidaten;
- den Pfad seiner detached LQ-237-SSHSIG-Datei;
- die beim Aufbau injizierte parameterlose Registry-Projektion;
- die zu prüfende stabile Key-ID;
- optional kontrollierte Clock- und OpenSSH-Abhängigkeiten.

Ein Registry-Pfad ist an dieser Grenze nicht vorhanden. Ebenso fehlen
Authority-ID, Public Key, Fingerprint, Policy, Status und Verification-ID als
Aufrufparameter.

## Genau ein Trust-Snapshot

Die Komposition ruft `project()` pro Promotionentscheidung exakt einmal auf.

Die zurückgegebenen Bytes werden unverändert für Registry-Parsing,
Authority-Auflösung und `registry_sha256` verwendet. Es gibt keinen zweiten
Lookup, keinen positiven Cache und keine Rekonstruktion aus Einzelwerten.

Damit kann eine Entscheidung nicht Authority aus einer Revision und
Evidence-Hash aus einer anderen Revision mischen.

## Aktuelle Authority

Die Projektion liest bei jedem neuen Aufruf den aktuellen persistenten
System-of-Record-Snapshot.

Der bestehende geschlossene Verifier löst daraus erneut auf:

- aktive Policy;
- genau eine bekannte Key-ID;
- aktive Signer-Authority;
- aktiven Key;
- Ed25519-Algorithmus und festen Namespace;
- eindeutigen Fingerprint und gebundenen Public Key;
- unabhängige Verification-Identität.

Eine committierte spätere Deaktivierung, Expiry oder Revocation wirkt deshalb
auf die nächste Entscheidung. Eine frühere positive Entscheidung erzeugt
keine fortdauernde Authority.

## Snapshot- und Signaturbindung

Bundle und Signatur werden weiterhin jeweils einmal in Bytes gelesen. Der
Verifier prüft das Bundle vollständig in Memory und extrahiert die exakten
`SHA256SUMS`-Bytes aus demselben Snapshot.

OpenSSH verifiziert die kanonische detached SSHSIG über genau diese Bytes mit
Namespace `liquent-operations-release-v1`.

Positive Evidence bindet weiterhin Bundle-, Checksum-, Signatur- und
Registry-Hash, Source-Commit, Paket- und Bundle-Version, Authority, Key,
Fingerprint, Policy, Verification-Identität und UTC-Entscheidungszeit.

## Abwesenheit und technische Nichtverfügbarkeit

Eine Projektion ohne aktuellen Registry-Pointer liefert `None`. Die
Komposition behandelt diese neutrale Abwesenheit als detailarme fachliche
Ablehnung und gewährt keine Promotion.

Eine fehlgeschlagene Projektion, ein unerwarteter Rückgabetyp, leere Bytes
oder beschädigte Registry-Bytes führen zur bereits bestehenden detailarmen
technischen Nichtverfügbarkeit.

Weder Datenbank-, Tabellen-, SQL-, Pfad-, Key-, Authority- noch
Infrastrukturdetails verlassen die Grenze. LQ-244 führt dafür keinen neuen
Exception-Typ ein.

## Kein Fallback

Bei Abwesenheit oder technischer Nichtverfügbarkeit wird weder eine lokale
Registry-Datei gelesen noch ein älterer Snapshot, Cache, Default-Key oder
Callerwert verwendet.

Die Entscheidung endet fail-closed. Ein Retry ist eine neue Entscheidung und
liest dann genau einen neuen aktuellen Snapshot.

## Kompatibilität

Die bestehende LQ-238-Funktion und CLI mit expliziter externer Registry-Datei
bleiben unverändert verfügbar. LQ-244 ändert deren Argumente und Verhalten
nicht.

Diese Kompatibilitätsgrenze ist jedoch kein Bestandteil der persistenten
Komposition. Wer die neue Funktion verwendet, kann keine Registry-Datei
einschleusen.

## Nachweis

Gezielte Tests belegen:

- erfolgreiche Prüfung mit exakt einem Projektionsaufruf;
- Hashbindung an genau die projizierten Bytes;
- neutrale Ablehnung bei fehlendem Current-Snapshot;
- detailarme Nichtverfügbarkeit bei technischem Projektionsfehler;
- detailarme Nichtverfügbarkeit bei leerem oder typfremdem Ergebnis;
- unveränderte Funktion der dateibasierten LQ-238-Grenze;
- direkte Akzeptanz des kanonischen LQ-243-Projektionsformats.

Die vollständige Pflichtsuite besteht:

```text
3020 passed, 53 warnings
```

Der PostgreSQL-Pflichtnachweis verwendet weiterhin den linearen Migration-Head
`20260817_0019`; LQ-244 benötigt keine neue Migration.

## Bewusst nicht enthalten

LQ-244 signiert, promotet, veröffentlicht oder deployt kein Artefakt. Es
schreibt keine Registry, Evidence- oder Trust-Datei und mutiert weder Keys noch
Authorities, Policy oder Revisionen.

Es gibt keine neue CLI, Route, Konfiguration, Migration, Schemaänderung,
Providerwahl, private Schlüsselverwaltung oder Production-Verdrahtung.

## Nächster Slice

LQ-245 sollte den kontrollierten Signing-Operator implementieren. Er muss ein
vollständig geprüftes LQ-236-Bundle an aktuelle persistente Signing-Authority,
Key-Status und Policy binden, private Schlüssel ausschließlich über eine
explizite Providergrenze verwenden und eine persistente idempotente
Signing-Entscheidung erzeugen, ohne Promotion oder Veröffentlichung.
