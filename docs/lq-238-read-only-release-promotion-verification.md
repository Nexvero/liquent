# LQ-238 — Read-only Release Promotion Verification

## 1. Ergebnis

LQ-238 implementiert die lokale read-only Promotion-Prüfung aus LQ-237.

Das Werkzeug verbindet vier aktuelle Fakten:

- einen unveränderten LQ-236-Bundle-Snapshot;
- dessen detached SSHSIG-Datei;
- eine extern injizierte Release-Authority-Registry;
- eine stabile Key-ID als Lookup-Referenz.

Nur erfolgreiche technische, kryptografische und aktuelle Authority-Prüfung
erzeugt detailarme Evidence mit `promotable = true`.

Der Slice signiert, publiziert und deployt nichts.

## 2. Lokales Werkzeug

`tools/release_promotion_verifier.py` stellt eine lokale CLI und eine
programmatic Verification-Funktion bereit.

Die CLI verlangt exakt:

```text
--bundle
--signature
--registry
--key-id
```

Es gibt kein `--allow`, keine Rollen- oder Capability-Eingabe, keine
Signer-Aktivitätsbehauptung und keinen Revocation-Bypass.

## 3. Keine Signing-Grenze

Das Produktwerkzeug besitzt keinen Signiercommand und liest keinen privaten
Schlüssel.

Die Tests erzeugen kurzlebige Ed25519-Schlüssel nur in pytest-eigenen
temporären Verzeichnissen, um reale SSHSIG-Fixtures zu prüfen. Diese Schlüssel
werden weder eingecheckt noch als Produktfixture oder Release-Evidence
bewahrt.

## 4. Release-Authority-Registry

Die Registry ist eine extern kontrollierte read-only JSON-Projektion des
maßgeblichen Systems of Record.

Schema-Version 1 enthält geschlossen:

- `schema_version`;
- `policy_revision`;
- `policy_status`;
- `verification_identity`;
- `authorities`.

Unbekannte oder fehlende Top-Level-Felder machen die Registry technisch nicht
verwendbar.

## 5. Authority-Fakten

Jede Authority enthält exakt:

- stabile `authority_id`;
- `status` als `active` oder `inactive`;
- eine Liste ihrer Keys.

Authority-IDs müssen eindeutig, begrenzt und neutral maschinenlesbar sein.

Nur eine aktive Authority kann eine aktuelle Promotion tragen.

## 6. Key-Fakten

Jeder Key enthält exakt:

- stabile `key_id`;
- Status `active`, `inactive`, `expired` oder `revoked`;
- kanonischen SHA-256-Fingerprint;
- Algorithmus `ssh-ed25519`;
- exakt den Namespace `liquent-operations-release-v1`;
- öffentlichen OpenSSH-Schlüssel ohne Kommentar.

Key-IDs und Fingerprints müssen registryweit eindeutig sein. Private Keys sind
im Schema nicht darstellbar.

## 7. Aktuelle Auflösung

Jeder Aufruf liest und validiert die vollständige Registry neu.

Die übergebene Key-ID dient nur zur Auswahl. Authority-ID, Status,
Fingerprint, Algorithmus, Namespace, öffentlicher Schlüssel und Policy werden
aus der Registry geladen.

Unbekannter Key, inaktive Authority sowie inaktiver, abgelaufener oder
widerrufener Key führen fail-closed zu fachlicher Ablehnung.

## 8. Registry-Konsistenz

Vor der Auswahl prüft der Verifier das gesamte geschlossene Registry-Inventar.

Duplikative IDs oder Fingerprints, unbekannte Statuswerte, falsche Shapes,
falsche Algorithmen, fremde Namespaces und beschädigte öffentliche Schlüssel
werden nicht teilweise toleriert.

Eine beschädigte Registry ist technische Nichtverfügbarkeit und keine
neutrale Abwesenheit eines Keys.

## 9. Ein Bundle-Snapshot

Der Verifier liest die Bundle-Datei genau einmal in einen unveränderlichen
Byte-Snapshot.

Der bestehende LQ-236-Verifier prüft eine temporäre lokale Kopie mit exakt
demselben Dateinamen. Danach wird `SHA256SUMS` aus denselben Snapshotbytes nur
in Memory gelesen.

Damit kann ein Austausch des ursprünglichen Pfads zwischen Integritäts- und
Signaturprüfung keine unterschiedlichen Kandidaten einschleusen.

## 10. Vollständige LQ-236-Prüfung

Vor jeder Kryptografie muss der Snapshot den vollständigen LQ-236-Vertrag
bestehen, einschließlich:

- sicherer Archivstruktur;
- kanonischem Manifest;
- geschlossenem Inventar;
- vollständigen Checksummen;
- Wheel-, Migration-, Operator- und Entry-Point-Metadaten;
- gebundener Verification-Evidence;
- unsigned-candidate-Policy.

Ein beschädigtes Bundle erreicht OpenSSH nicht.

## 11. Signaturdateibindung

Der detached Signaturpfad muss exakt lauten:

```text
<bundle-dateiname>.sshsig
```

Symlinks und nicht reguläre Dateien werden abgelehnt.

Die Signaturdatei muss außerdem eine größenbegrenzte, kanonisch vollständig
abgeschlossene SSHSIG-Armor-Datei sein.

## 12. Kanonisches SSHSIG-Armor

OpenSSH toleriert in der geprüften lokalen Version angehängte Bytes nach dem
Armor-Ende. LQ-238 akzeptiert diese Mehrdeutigkeit nicht.

Vor dem kryptografischen Verify verlangt der Slice deshalb exakt:

```text
-----BEGIN SSH SIGNATURE-----
<Base64-Zeilen>
-----END SSH SIGNATURE-----
```

mit finalem Newline und ohne Präfix, Suffix oder zusätzliche Bytes.

Der negative Test belegt, dass ein angehängtes Byte fail-closed endet.

## 13. Trust-Root-Prüfung

Der öffentliche Schlüssel wird ausschließlich aus der Registry in ein
temporäres owner-only Allowed-Signers-Dokument projiziert.

Vor Signature Verification berechnet `ssh-keygen` den Fingerprint dieses
Schlüssels neu. Er muss exakt dem separat in der Registry gebundenen
Fingerprint entsprechen.

Ein caller-supplied Public Key oder Bundle-internes Keymaterial wird nicht
akzeptiert.

## 14. Kryptografische Prüfung

Der Verifier ruft den lokalen OpenSSH-Provider mit folgenden festen
Entscheidungen auf:

- SSHSIG-Verify;
- Registry-Authority-ID als Principal;
- Namespace `liquent-operations-release-v1`;
- registrygebundener Ed25519 Public Key;
- exakte `SHA256SUMS`-Snapshotbytes über Standard Input.

Provider-Output wird nicht an den Aufrufer weitergereicht.

## 15. Temporäre Dateien

Bundle-Snapshot, Public Key, Allowed Signers und Signaturkopie liegen nur in
eindeutig besessenen temporären Verzeichnissen.

Key-, Allowed-Signers- und Signaturdatei verwenden `0600`. Die
Temporary-Directory-Grenze entfernt alle Dateien nach der Entscheidung.

Es findet keine Extraktion in einen operatorgewählten Zielbaum statt.

## 16. Positive Promotion-Evidence

Ein erfolgreicher Aufruf liefert geschlossen strukturierte Evidence mit:

- Schema-Version;
- Bundle-Dateiname und SHA-256;
- SHA-256 der exakten `SHA256SUMS`-Bytes;
- SHA-256 der detached Signatur;
- Commit, Paket- und Bundle-Formatversion;
- Signaturformat und Namespace;
- Signer-Authority-ID, Key-ID und Fingerprint;
- Policy-Revision und Registry-Hash;
- Verification-Identität und UTC-Entscheidungszeit;
- Integritäts-, Signatur-, Authority- und Promotion-Ergebnis.

Die CLI schreibt diese Evidence nur nach Standard Output. Sie legt keine
`promotion.json` an und mutiert keinen Releasekanal.

## 17. Evidence-Ergebnis

Nur der vollständige Erfolgsfall liefert:

```text
integrity = verified
signature = verified
authority = current
promotable = true
```

Es gibt keinen partiell positiven oder caller-gesteuerten Zustand.

Die Evidence autorisiert weiterhin kein Deployment und ersetzt bei einer
späteren Entscheidung keinen neuen Registry-Lookup.

## 18. Revocation

Tests bestätigen zuerst eine positive Entscheidung, ändern anschließend die
read-only Fixture-Projektion auf inactive, revoked oder expired und rufen den
Verifier erneut auf.

Jede spätere Entscheidung wird abgelehnt. Es existiert kein positiver
Authority-Cache und kein historischer `signed_at`-Bypass.

## 19. Fachliche Ablehnung

Detailarme fachliche Ablehnung umfasst unter anderem:

- unbekannte Key-ID;
- inaktive Authority oder Policy;
- inaktiven, abgelaufenen oder widerrufenen Key;
- Bundle- oder Signaturmanipulation;
- abweichenden Fingerprint;
- falschen Signaturdateinamen;
- kryptografisch ungültige Signatur.

Die CLI liefert hierfür ausschließlich
`release_promotion_rejected` mit Exitcode `2`.

## 20. Technische Nichtverfügbarkeit

Technische Nichtverfügbarkeit bleibt separat und gewährt ebenfalls keine
Promotion.

Sie umfasst insbesondere:

- unlesbare oder strukturell beschädigte Registry;
- ungültige Registry-Duplikate oder Trust-Root-Daten;
- fehlenden oder nicht ausführbaren OpenSSH-Provider;
- lokale I/O- oder Provider-Ausführungsfehler.

Die CLI liefert ausschließlich
`release_promotion_verification_unavailable` mit Exitcode `3`.

Weder Kategorie gibt Pfade, Schlüssel, Signaturbytes oder Providerdiagnosen
aus.

## 21. Verifikation

LQ-238 ergänzt acht gezielte Testfälle mit realen kurzlebigen SSHSIG-
Operationen.

Sie belegen:

- positive Signatur-, Fingerprint- und Authority-Prüfung;
- vollständig gebundene Promotion-Evidence;
- sofort wirksame Authority-Deaktivierung;
- sofort wirksame Key-Revocation und Expiry;
- Fingerprint- und Signaturmanipulation;
- unbekannte Key-Referenz und falschen Signaturpfad;
- Registry- und Kryptografie-Nichtverfügbarkeit;
- detailarme CLI-Ablehnung.

Gemeinsam mit LQ-236 bestehen `16` gezielte Tests.

Die vollständige datenbankunabhängige Suite besteht mit:

```text
2829 passed, 74 skipped, 53 warnings
```

LQ-238 verändert keine Datenbank-, Migrations- oder Runtime-Route. Die
PostgreSQL-Suite wurde deshalb nicht erneut gestartet.

## 22. Bewusst nicht enthalten

LQ-238 implementiert oder vollzieht keine:

- persistente Release-Authority-Datenbank;
- Registry-Mutation, Bootstrap, Rotation oder Recovery;
- private Key-Erzeugung im Produktpfad;
- Signing-CLI;
- dauerhafte Evidence-Datei;
- Releasekanal-, Registry- oder Hostingpublikation;
- Git-Tag, Package-Version oder Deployment;
- Git-Staging-, Branch-, Commit-, Push- oder Pull-Request-Aktion.

## 23. Nächster Slice

LQ-239 sollte den kontrollierten Release-Signing-Operatorvertrag und die
Authority-Registry-Lifecycle-Grenzen entscheiden.

Er muss Provisionierung, Aktivierung, Rotation, Revocation, Recovery und
Separation of Duties festlegen, ohne private Schlüssel im Repository zu
speichern oder bereits einen Release zu signieren oder zu publizieren.
