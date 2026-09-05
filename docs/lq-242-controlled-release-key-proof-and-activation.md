# LQ-242 — Controlled Release Key Proof and Activation

## Ergebnis

LQ-242 implementiert Proof-of-Possession- und Approval-gebundene Aktivierung
eines aktuell inaktiven Release-Keys.

Der Caller liefert nur stabile Change-, Lifecycle-Actor-, Key- und erwartete
Registry-Revision sowie opaque Proof- und Approval-Artefakte. Public Key,
Fingerprint, Authority-, Signer-, Key- und Policy-Status werden aktuell aus
dem Registry-System of Record gelesen.

## Getrennte Verifier

`ReleaseKeyProofVerifier` prüft den Besitz des privaten Schlüssels gegen den
registrygebundenen Public Key und einen kanonischen Challenge-Kontext.

`ReleaseKeyActivationApprovalVerifier` prüft unabhängig das Approval und
liefert eine stabile repr-freie Reviewer-ID. Ein fehlendes Approval oder ein
Reviewer mit derselben ID wie der Lifecycle-Actor sperrt neutral.

Es gibt keinen caller-supplied Allow-Wert und keinen privaten Schlüssel im
Produktpfad.

## Kanonische Challenge

Die Challenge bindet Schema-Version, dedizierten Namespace
`liquent-release-key-possession-v1`, Change-ID, Actor-Authority, Key-ID,
erwartete Revision, Key-Fingerprint und Hash des Public Keys in kanonischem
JSON.

Sie ist keine Release-Signatur und kann keinen Kandidaten promoten.

## Aktuelle Autorisierung

Die atomare Schreibgrenze verlangt dieselbe aktuelle Registry-Revision sowie:

- aktive Policy;
- aktive Registry-Lifecycle-Authority des Actors;
- inaktiven ausgewählten Key;
- aktive zugeordnete Signer-Authority;
- unveränderte Key-/Signer-Zuordnung.

Stale Revision, inaktive Fakten, fehlender Proof oder fehlende unabhängige
Freigabe enden neutral ohne ID-Erzeugung.

## Persistente Entscheidung

Migration `20260817_0019` ergänzt `release_key_activations` und bindet
Change-ID, Actor, Key, erwartete/resultierende Revision, Challenge-, Proof- und
Approval-Hash sowie Reviewer-ID unveränderlich.

Die bestehende Lifecycle-Decision wird im selben Commit mit Target `key` und
Intent `activate` erzeugt.

## Vollständiger Snapshot

Eine erfolgreiche Aktivierung kopiert Signer-, Lifecycle- und Key-Inventar der
erwarteten Revision vollständig in eine neue Revision. Ausschließlich der
gewählte Key wechselt von `inactive` auf `active`.

Policy-Revision und Policy-Status bleiben gebunden. Der historische
Bootstrap-Snapshot bleibt unverändert inaktiv. Der Current-Pointer wechselt
genau einmal auf die neue Revision.

## Retry und Konflikt

Exakte Wiederholung derselben Change-ID mit Actor, Key, erwarteter Revision und
identischen Proof-/Approval-Bytes liefert die bereits committete Revision und
Reviewer-ID ohne erneute Verifikation oder Generatorzug.

Abweichende Wiederverwendung derselben Change-ID ist ein detailfreier
`ReleaseKeyActivationConflict`.

Verifier-, Generator-, Transaktions-, Encoding- oder Strukturfehler werden als
detailfreie `ReleaseKeyActivationUnavailable` ausgegeben.

## Konkurrenz

PostgreSQL sperrt Current-Pointer, Revisionen, Authority-/Key-Snapshots und
Decision-Inventare in fester Reihenfolge. Zwei Aktivierungen gegen dieselbe
erwartete Revision erzeugen genau einen Commit; die zweite sieht anschließend
stale State und endet neutral.

## Nachweis

SQLite-Tests belegen erfolgreichen Snapshotwechsel, unveränderte Historie,
Proof-/Approval-Sperren, Separation of Duties, stale Revision, exakten Retry,
Konflikt und vollständigen Rollback.

Ein echter PostgreSQL-16-Konkurrenztest bestätigt genau eine Aktivierung gegen
dieselbe Revision. Die vollständige Pflichtsuite besteht:

```text
3003 passed, 53 warnings
```

Der temporäre PostgreSQL-Cluster wurde kontrolliert gestoppt und vollständig
entfernt.

## Bewusst nicht enthalten

LQ-242 erzeugt keinen privaten Schlüssel, implementiert keinen konkreten HSM-,
Agent-, Approval- oder Signing-Provider und signiert keinen Release. Es gibt
keine Operator-CLI, Registry-Projektion, Promotion, Veröffentlichung,
Deployment oder Git-Aktion.

## Nächster Slice

LQ-243 sollte die read-only Projektion der aktuellen persistenten Registry in
das geschlossene LQ-238-JSON-Format implementieren. Sie muss Current-Pointer,
vollständigen Snapshot, Public Keys und Status aus demselben System of Record
binden, ohne caller-supplied Authority oder Mutation.
