# LQ-240 — Persistent Release Authority Registry Foundation

## 1. Ergebnis

LQ-240 implementiert die leere persistente Foundation für den in LQ-239
entschiedenen Release-Authority-Lifecycle.

Der Slice ergänzt neun stabile domänenspezifische Identitätstypen, sichere
unabhängige ID-Erzeugung, unveränderliche Authority- und Public-Key-Fakten,
vollständige historische Registry-Set-Revisionen, einen optionalen aktuellen
Revisionspointer sowie leere Lifecycle- und Signing-Decision-Inventare.

Er erzeugt keine Authority, keinen Key, keine Revision und keine Entscheidung.

## 2. Getrennte Identitätstypen

Die Release-Control-Plane erhält:

- `ReleaseSignerAuthorityId`;
- `ReleaseRegistryLifecycleAuthorityId`;
- `ReleaseSigningKeyId`;
- `ReleaseRegistrySetRevisionId`;
- `ReleasePolicyRevisionId`;
- `ReleaseRegistryLifecycleChangeId`;
- `ReleaseSigningDecisionId`;
- `ReleaseRegistryRecoveryId`;
- `ReleaseEmergencyRevocationId`.

Die Typtrennung verhindert strukturelle Verwechslung von Authority, Key,
Revision, Policy, regulärer Mutation, Signing, Recovery und Notfallentscheidung.

## 3. Modellgrenze

Alle neun IDs sind frozen Dataclasses mit Slots und repr-freiem Wert.

Leere Werte sowie `None`, Zahlen, Bytes und boolesche Werte werden bereits an
der Modellgrenze abgelehnt.

Die Typen enthalten keine E-Mail-Adresse, UserId, WorkspaceId, Rolle,
Capability oder Environmentbindung.

## 4. Sichere Erzeugung

Der bestehende `SecureIdentityAuthorityMaterialGenerator` besitzt neun neue
domänenspezifische Methoden.

Jede zieht unabhängig mindestens 32 Byte Betriebssystementropie. IDs werden
nicht aus vorherigen Revisionen, Fingerprints, Bundle-Hashes, Zeit oder
fachlichen Inhalten abgeleitet.

Eine erzeugte ID gewährt keine Authority. Erst eine spätere erfolgreich
committete Mutation kann daraus einen sichtbaren Registry-Fakt machen.

## 5. Geschlossene Statusvokabulare

Die Domain definiert ausschließlich:

- Authority: `active`, `inactive`;
- Signing-Key: `active`, `inactive`, `expired`, `revoked`;
- Policy: `active`, `inactive`.

Die Migration erzwingt dieselben Vokabulare für historische Revisionen.

Revocation bleibt von bloßer Inaktivität und Expiry unterscheidbar.

## 6. Additive Migration

Revision `20260817_0017` baut linear und ohne Merge-Head auf
`20260813_0016` auf.

Sie verändert keine vorhandene Identity-, Session-, Trust-, Membership-,
Lifecycle-, Research- oder Runtime-Tabelle.

Am Abschluss von LQ-240 war `20260817_0017` der einzige erwartete Head; LQ-241
baut darauf anschließend linear mit `20260817_0018` auf.

## 7. Stabile Authority-Existenz

Zwei getrennte Tabellen reservieren unveränderliche Existenzfakten für
Release-Signer-Authorities und Release-Registry-Lifecycle-Authorities.

Die Tabellen tragen absichtlich keinen aktuellen Status. Status gehört zum
vollständigen historischen Registry-Snapshot und wird nicht als unabhängig
überschreibbare Einzelzeile behandelt.

## 8. Unveränderliche Public-Key-Fakten

`release_signing_keys` bindet dauerhaft Key-ID, genau eine
Signer-Authority-ID, Algorithmus `ssh-ed25519`, Namespace
`liquent-operations-release-v1`, Fingerprint und Public Key.

Fingerprint und Public Key sind registryweit eindeutig. Private Keys oder
Provider-Handles sind nicht darstellbar.

## 9. Nichtwiederzuweisung eines Keys

Historische Key-Snapshotzeilen referenzieren Key-ID und Signer-Authority
gemeinsam.

Dadurch kann ein bereits in einer Revision sichtbarer Key nicht auf eine
andere Signer-Authority umgehängt werden, ohne die historische
Fremdschlüsselbindung zu verletzen.

Rotation benötigt deshalb später zwingend eine neue Key-ID.

## 10. Registry-Set-Revisionen

`release_registry_set_revisions` hält stabile Revision-ID,
Policy-Revision-ID und Policy-Status.

Drei getrennte Member-Inventare beschreiben den vollständigen Snapshot aus
Signer-Authorities, Registry-Lifecycle-Authorities sowie Keys mit ihrer
unveränderten Signer-Zuordnung und dem jeweiligen Status.

Historische Member werden nicht durch einen späteren Snapshot überschrieben.

## 11. Current-Pointer

`release_registry_current_set` ist ein optionaler Singleton und darf nur auf
eine existierende Registry-Revision verweisen.

Die Migration erzeugt keinen Pointer. Ein fehlender Pointer bedeutet, dass
noch kein Registry-Bootstrap committet wurde. Es existiert kein Default- oder
Fallback-Snapshot.

## 12. Lifecycle-Decision-Inventar

`release_registry_lifecycle_changes` reserviert stabile reguläre
Change-Entscheidungen.

Jede Zeile bindet Change-ID, existierende Lifecycle-Actor-Authority, genau ein
typisiertes Ziel aus Signer, Lifecycle-Authority oder Key, domänengültigen
Intent sowie erwartete und resultierende existierende Registry-Revision.

Ein caller-supplied vollständiger Authority-Satz ist nicht speicherbar.

## 13. Geschlossene Transition-Form

Signer- und Lifecycle-Authority-Ziele erlauben nur `grant`, `deactivate` und
`reactivate`.

Key-Ziele erlauben nur `provision`, `activate`, `deactivate`, `reactivate`,
`expire` und `revoke`.

Diese Constraints führen noch keine Transition aus. Sie verhindern lediglich,
dass spätere Entscheidungen unter strukturell falscher Bedeutung gespeichert
werden.

## 14. Signing-Decision-Inventar

`release_signing_decisions` reserviert unveränderliche erfolgreiche
Signing-Entscheidungen mit Bundle-, Checksum- und Signaturhash, Source-Commit,
Paketversion, Signer-Authority, Key und Fingerprint, Registry-/Policy-Revision,
festem SSHSIG-Format und Namespace, Executor, Zeit sowie exakten Signatur- und
Evidence-Bytes.

Key und Signer-Authority werden gemeinsam fremdschlüsselgebunden.

## 15. Keine halben Decision-Fakten

Decision-ID, Authority, Key, Revisionen, Executor, Signatur und Evidence sind
nicht nullable.

Eine Signing-Decision kann nicht auf unbekannte Authority-, Key- oder
Registry-Fakten zeigen.

Die Foundation implementiert noch nicht die spätere atomare Koordination mit
exklusiven Outputdateien.

## 16. Kein Seed und keine Adoption

Alle zehn neuen Tabellen sind nach Migration leer.

Insbesondere entstehen keine Authorities, Public Keys, Registry- oder
Policy-Revisionen, Current-Pointer, Lifecycle-Changes oder Signing-Decisions.

Git-, CI-, Betriebssystem- oder vorhandene LQ-238-Registry-Dateien werden nicht
automatisch adoptiert.

## 17. Kein ausführbarer Port

LQ-240 fügt keinen Lookup-, Bootstrap-, Lifecycle-, Signing-, Recovery- oder
Emergency-Port hinzu.

Es entsteht deshalb auch keine neue fachliche Ablehnung oder technische
Exception. Spätere Ports müssen neutrale Abwesenheit, Konflikt und detailarme
technische Nichtverfügbarkeit getrennt halten.

## 18. Bundle-Head

Am Abschluss von LQ-240 erwartete der LQ-236-Builder exakt siebzehn lineare
Migrationen und Head `20260817_0017`; LQ-241 zieht diese aktuelle Bindung auf
achtzehn Migrationen und `20260817_0018` weiter.

Sein synthetisches Test-Wheel wurde entsprechend erweitert. Ein Wheel mit dem
alten Head oder nur sechzehn Migrationen wird nicht mehr als aktueller
Formatversion-1-Kandidat akzeptiert.

Die historischen LQ-232/234-Preflight-Aussagen bleiben als damalige Evidence
unverändert.

## 19. SQLite-Nachweis

Foundation-Tests aktivieren SQLite-Fremdschlüssel explizit und belegen:

- alle neun repr-freien stabilen ID-Typen;
- unabhängige sichere Erzeugung;
- geschlossene Statusvokabulare;
- zehn vollständig leere Tabellen;
- erhaltene historische Revisionen nach Pointerwechsel;
- eindeutige Fingerprints;
- nicht umhängbare historische Key-Zuordnung;
- genau ein typisiertes Lifecycle-Ziel;
- keine Pointer oder Signing-Decisions auf unbekannte Fakten.

## 20. PostgreSQL-Nachweis

Ein separater verpflichtender PostgreSQL-Test migriert eine frische
Throwaway-Datenbank auf `20260817_0017`.

Er bestätigt leere Registry- und Signing-Inventare sowie die serverseitige
Fremdschlüsselsperre gegen spätere Umhängung eines historisch referenzierten
Keys.

Der isolierte lokale PostgreSQL-16-Cluster wurde nach der Prüfung kontrolliert
gestoppt und vollständig entfernt.

## 21. Gesamtnachweis

Die vollständige Suite einschließlich aller PostgreSQL-Pflichttests besteht:

```text
2965 passed, 53 warnings
```

Der Migration-Head bleibt eindeutig. Die LQ-236/238-Release-Prüfungen bleiben
mit der neuen Migration grün.

## 22. Retention und Nichtwiederverwendung

Authority-, Key-, Revision-, Lifecycle- und Signing-Fakten werden nie unter
neuer Bedeutung wiederverwendet.

Historische Revisionen und Decisions müssen mindestens so lange erhalten
bleiben, wie Release, Retry, Promotion, Deployment, Rollback, Incident oder
Audit auf sie verweist.

Konkrete Archivierungs-, Partitionierungs- und Datenschutzfristen bleiben
späteren Entscheidungen vorbehalten und dürfen diese Untergrenze nicht
unterschreiten.

## 23. Bewusst nicht enthalten

LQ-240 implementiert oder vollzieht keine:

- Bootstrap- oder Foundation-Adoption;
- Registry-Lifecycle-Mutation;
- Proof of Possession oder Key-Aktivierung;
- Signing- oder Key-Provider-Grenze;
- Recovery- oder Emergency-Revocation-Persistenz;
- Registry-Projektion für LQ-238;
- Operator-CLI, Route, Settings oder Runtime-Wiring;
- private oder öffentliche Schlüssel;
- Signatur, Promotion, Veröffentlichung oder Deployment;
- Git-Staging-, Branch-, Commit-, Push- oder Pull-Request-Aktion.

## 24. Nächster Slice

LQ-241 sollte den einmaligen persistenten Release-Registry-Bootstrap
implementieren.

Er muss erste Lifecycle- und Signer-Authority, ersten inaktiven Public Key,
erste Registry-/Policy-Revision, Current-Pointer und unveränderliche
Bootstrap-Entscheidung atomar erzeugen, sobald die gesamte Registry-Historie
leer ist. Er darf den Key nicht aktivieren, keinen Release signieren und
Bootstrap nach irgendeiner sichtbaren Historie nie wieder öffnen.
