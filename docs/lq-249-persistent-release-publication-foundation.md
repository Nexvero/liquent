# LQ-249 — Persistent Release Publication Foundation

## Ergebnis

LQ-249 implementiert die leere persistente Foundation für den in LQ-248
entschiedenen Publication-Handoff.

Der Slice schafft stabile Identitäten und historienerhaltende Inventare für
Channels, Publisher, Handoffs, Receipts und Reassessments. Er erzeugt keinen
Seed und führt keinen Upload oder Deployment aus.

## Stabile Identitäten

Sieben neue repr-freie, immutable und geslottete Typen unterscheiden:

- Publication-Handoff;
- Publisher-Authority;
- Publication-Channel;
- Channel-Policy-Revision;
- Publication-Decision;
- Provider-Receipt;
- Publication-Reassessment.

Die Typen sind nicht gegenseitig austauschbar und akzeptieren ausschließlich
nicht leere Strings.

## Sichere Materialerzeugung

`SecureIdentityAuthorityMaterialGenerator` erzeugt jede neue Publication-ID
über einen eigenen unabhängigen Zug aus mindestens 32 Byte
Betriebssystementropie.

Keine ID wird aus Channelnamen, Provider, Paketversion, Hash, Actor, Zeit oder
Environment abgeleitet. Erzeugung einer ID gewährt selbst keine Authority.

## Additive Migration

Migration `20260817_0020` baut linear auf `20260817_0019` auf und ist der
einzige neue Head.

Sie erzeugt acht leere Tabellen:

- `release_publication_channels`;
- `release_publisher_authorities`;
- `release_publication_channel_revisions`;
- `release_publication_revision_publishers`;
- `release_publication_current_channels`;
- `release_publication_handoffs`;
- `release_publication_receipts`;
- `release_publication_reassessments`.

Es gibt keinen Singleton, Default-Channel, Default-Publisher oder anderen
Seed.

## Channel-Fakten

`release_publication_channels` hält ausschließlich stabile nie
wiederverwendete Channel-Identitäten.

Eine Channel-Revision bindet Channel, aktiven oder inaktiven Status,
Artefaktklasse `operational_bundle`, Paketname, Providerart und kanonischen
Zielnamen.

Provider-Credentials, Tokens, Clients und freie Caller-URLs sind keine
persistierten Foundation-Fakten.

## Historische Channel-Revisionen

Jede Revision bleibt unveränderlich referenzierbar. Der Current-Pointer ist
pro Channel eindeutig und muss dieselbe Channel-ID wie seine Zielrevision
tragen.

Ein Pointer kann dadurch nicht Revision A unter Channel B sichtbar machen.
Historische Revisionen werden beim späteren Pointerwechsel nicht
überschrieben.

LQ-249 implementiert noch keinen Adapter, der Pointer erzeugt oder bewegt.

## Publisher-Authority-Snapshots

Publisher-Authorities besitzen eine eigene stabile globale Existenz.

`release_publication_revision_publishers` bindet sie mit explizitem
`active`- oder `inactive`-Status an genau eine Channel-Revision. Eine
Authority außerhalb des vollständigen Revisionssnapshots wird nicht implizit
wirksam.

Signing-, Promotion-, Produkt- oder Git-Authority wird nicht als Publisher
übernommen.

## Handoff-Inventar

Die Handoff-Tabelle ist für unveränderliche
`ready_for_publication`-Entscheidungen vorbereitet und bindet:

- Handoff- und eindeutige Decision-ID;
- Publisher-Authority;
- Channel und exakte Channel-Revision;
- Bundle-, Wheel-, Checksum-, Signatur- und Promotion-Evidence-Hash;
- Source-Commit, Paketversion und Bundle-Formatversion;
- Signer-Authority und Key;
- Registry- und Policy-Revision;
- Promotion-Verifier und Promotionszeit;
- Annahmezeit und geschlossenen Status.

Lokale Pfade, DSN, Provider-Credentials und freie Ziel-URLs fehlen.

## Bestehende Release-Fakten

Ein Handoff kann nur einen bereits bekannten Release-Signing-Key mit seiner
unveränderlichen Signer-Zuordnung referenzieren.

Die gebundene Registry-Revision muss ebenfalls existieren. Damit kann ein
späterer Adapter keine frei erfundene Signing- oder Registry-Identität in den
Publication-Bestand schreiben.

LQ-249 prüft noch keine aktuelle Revocation und akzeptiert keinen Handoff.

## Provider-Receipts

Ein Receipt besitzt eine stabile eigene ID und gehört eindeutig zu genau
einem bekannten Handoff.

Es hält opaque Providerbestätigung, extern beobachteten Bundle-Hash und
Publication-Zeit. Leere Providerbestätigung und Receipt ohne Handoff sind
strukturell ausgeschlossen.

Die Foundation erzeugt, interpretiert oder rekonstruiert kein Receipt.

## Reassessment und Withdrawal

Reassessments referenzieren ausschließlich bekannte Handoffs und verwenden
geschlossene Intents `reassess` oder `withdraw` sowie Status `pending` oder
`completed`.

Sie überschreiben weder Handoff noch Receipt. Spätere Revocation kann damit
eine neue Historie anstoßen, ohne frühere Publication-Fakten umzudeuten.

LQ-249 löst noch keinen Reassessment aus.

## Datenbankinvarianten

Primär-, Unique-, Composite-Foreign-Key- und Check-Constraints erzwingen:

- stabile eindeutige IDs;
- gleiche Channel-ID zwischen Revision und Current-Pointer;
- bekannte Publisher in Revisionssnapshots;
- bekannte Channel-Revision für jeden Handoff;
- bekannte Signing-Key-/Signer-Zuordnung;
- bekannte Registry-Revision;
- höchstens ein Receipt pro Handoff;
- bekannte Handoffs für Receipts und Reassessments;
- geschlossene Status-, Intent- und Artefaktklassen.

Diese Constraints gewähren keine aktuelle Authority; sie schützen nur die
strukturelle Foundation.

## Retention und Nichtwiederverwendung

Channels, Authorities, Revisionen, Handoffs, Decisions, Receipts und
Reassessments werden nicht gelöscht und unter neuer Bedeutung
wiederverwendet, solange Release, Deployment, Rollback, Incident oder Audit
darauf verweisen kann.

Deaktivierung oder Withdrawal muss später als neue historische Entscheidung
modelliert werden, nicht als Umbenennung oder Überschreiben.

## Bundle-Gate

Das LQ-236-Wheelgate erwartet nun zwanzig lineare Migrationen bis Head
`20260817_0020`.

Die Zahl der Console Entry Points und Operatormodule bleibt unverändert bei
vierzehn beziehungsweise zwölf. Bundle-Formatversion 1 bleibt bestehen.

## Nachweis

SQLite-Tests belegen alle sieben ID-Typen, unabhängige sichere Erzeugung,
vollständig leere Inventare, Channel-/Revision-Konsistenz und referenzielle
Sperren für unbekannte Receipts und Reassessments.

Ein echter PostgreSQL-16-Test bestätigt alle acht Tabellen und ihren leeren
Ausgangszustand nach vollständiger Migration.

Die vollständige Pflichtsuite besteht:

```text
3086 passed, 56 warnings
```

Der temporäre PostgreSQL-Cluster wurde kontrolliert gestoppt und entfernt.

## Bewusst nicht enthalten

LQ-249 implementiert keine Ports, Exceptions, Bootstrap-, Lifecycle-,
Authority-, Handoff-, Receipt-, Publisher-, Reassessment- oder
Withdrawal-Adapter.

Es gibt keine Seeds, Credentials, Provider-SDKs, CLI, Datei-, Git-, Netzwerk-,
Publication-, Package-Index-, Registry- oder Deploymentmutation.

## Nächster Slice

LQ-250 sollte den einmaligen Publication-Control-Plane-Bootstrap
implementieren. Er darf atomar genau einen ersten aktiven Channel, eine erste
aktive Publisher-Authority, eine erste vollständige Channel-Revision und den
Current-Pointer erzeugen, aber keinen Handoff, Receipt, Upload oder Deployment
ausführen.
