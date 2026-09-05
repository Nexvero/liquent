# LQ-251 — Authorized Persistent Release Publication Handoff

## Ergebnis

LQ-251 implementiert den autorisierten persistenten Publication-Handoff aus
LQ-248 auf der Foundation und dem Bootstrap von LQ-249/250.

Ein erfolgreicher Aufruf commitet ausschließlich
`ready_for_publication`. Er greift auf keinen Provider zu, lädt nichts hoch
und startet kein Deployment.

## Geschlossener Handoff-Port

Der Port akzeptiert ausschließlich:

- stabile Handoff-ID;
- stabile Publication-Decision-ID;
- identifizierende Publisher-Authority-ID;
- stabile Channel-ID;
- exakt erwartete Channel-Policy-Revision;
- Bundle-Pfad;
- detached Signaturpfad;
- Pfad zu kanonischer positiver LQ-247-Evidence.

Er akzeptiert keine freie Ziel-URL, Credentials, Rolle, Capability,
Allow-Entscheidung, Public-Key-Datei, Registry-Datei oder behaupteten
Publication-Status.

## Einmalige Artefakt-Snapshots

Bundle, Signatur und bereitgestellte Promotion-Evidence werden pro Aufruf
jeweils einmal als reguläre nicht verlinkte Datei in Bytes gelesen.

Die Persistenzentscheidung bindet deren SHA-256-Werte. Lokale Pfade bleiben
Bedienkontext und werden nicht persistiert.

Ungültige, fehlende oder verlinkte Eingaben enden detailarm technisch nicht
verfügbar.

## Kanonische Promotion-Evidence

Die bereitgestellte Evidence muss kanonisches kompaktes ASCII-JSON mit
sortierten Schlüsseln, finalem Newline und `promotable=true` sein.

Sie bleibt ein historischer Entscheidungsfakt. Ihr Hash und ursprüngliches
`decided_at` werden im Handoff gebunden.

Caller können kein toleriertes Zusatzfeld, alternative Kodierung oder
nicht kanonisches JSON einschleusen.

## Erneute aktuelle Promotionprüfung

Für jeden neuen Handoff führt die Grenze LQ-244 erneut aus:

- genau eine aktuelle persistente Registry-Projektion;
- vollständige LQ-236-Bundle-Prüfung;
- exakte SHA256SUMS-Bindung;
- Fingerprintprüfung gegen den persistenten Public Key;
- SSHSIG-Verifikation unter festem Release-Namespace;
- aktuelle aktive Signer-, Key- und Policy-Auflösung.

Es gibt keinen Registry-Dateipfad, Cache, Default-Key oder älteren
Trust-Fallback.

## Abgleich alter und neuer Promotion

Die neue LQ-244-Entscheidung muss in allen Feldern außer der neuen
Entscheidungszeit exakt mit der bereitgestellten LQ-247-Evidence
übereinstimmen.

Damit bleiben insbesondere Bundle-, Checksum-, Signatur- und Registry-Hash,
Source-Commit, Version, Signer, Key, Fingerprint, Policy und unabhängige
Verification-Identität identisch.

Eine veränderte Registry, Revocation, andere Signatur oder manipulierte
Evidence führt neutral zu keinem Handoff.

## Normative Lock-Reihenfolge

PostgreSQL sperrt vor der neuen Prüfung in fester Reihenfolge:

- Current Release Registry und Revisionen;
- Release-Signer, Keys und unveränderliche Key-Fakten;
- Publication-Channels und Publisher-Authorities;
- Channel-Revisionen, Publisher-Member und Current-Pointer;
- Publication-Handoffs.

Die aktuelle Promotionprüfung läuft unter diesen gehaltenen
Control-Plane-Sperren. Eine konkurrierende Revocation oder Channelmutation
gewinnt dadurch normativ entweder davor oder danach, nicht dazwischen.

## Aktuelle Release-Fakten beim Commit

Nach positiver LQ-244-Prüfung bestätigt dieselbe Transaktion erneut:

- aktuellen Registry-Pointer;
- aktive Release-Policy;
- aktiven ausgewählten Key;
- aktive zugeordnete Signer-Authority;
- persistente Registry- und Policy-Revision;
- unveränderte Key-/Signer-Zuordnung.

Die intern aufgelöste Registry-Revision wird im Handoff gespeichert, obwohl
sie kein Callerfeld ist.

## Publisher-Authority und Channel

Der Handoff löst aus dem Publication-System of Record auf:

- Channel-ID ist aktuell sichtbar;
- erwartete Channel-Revision ist exakt current;
- Channelstatus ist aktiv;
- Artefaktklasse ist `operational_bundle`;
- Paketname ist `liquent`;
- identifizierte Publisher-Authority ist in genau dieser Revision aktiv.

Publisher-ID identifiziert den Actor, gewährt allein aber keine Authority.
Der aktuelle Revision-Member ist die maßgebliche Capability.

## Wheel- und Manifestbindung

Nach vollständiger Bundle-Verifikation liest die Grenze den Wheel-SHA-256 aus
dem kanonischen Manifest desselben Bundle-Snapshots.

Der Handoff bindet Bundle-, Wheel-, Checksum-, Signatur- und Promotion-
Evidence-Hash gemeinsam mit Source-Commit, Paketversion und
Bundle-Formatversion.

Ein Pfad oder Dateiname ersetzt keinen dieser Hashfakten.

## Persistente Entscheidung

Ein erfolgreicher Commit erzeugt genau eine Zeile in
`release_publication_handoffs` mit:

- Handoff- und eindeutiger Decision-ID;
- Publisher, Channel und exakter Channel-Revision;
- allen fünf Artefakt-/Evidence-Hashes;
- Commit, Paketversion und Bundle-Format;
- Signer, Key, Registry- und Policy-Revision;
- Promotion-Verifier und ursprünglicher Promotionszeit;
- neuer Handoff-Zeit;
- Status `ready_for_publication`.

Receipt- und Reassessment-Inventare bleiben unverändert leer.

## Exakter Retry

Ein Retry derselben Handoff-ID prüft vor aktueller Projektion den bereits
persistierten Input-Fingerprint.

Stimmen Decision, Channel, Channel-Revision, Bundle-, Signatur- und
Promotion-Evidence-Hash exakt überein, liefert die Grenze dasselbe typisierte
Resultat ohne neue Registry-Projektion, Clock oder Mutation.

Der Retry veröffentlicht nichts und erzeugt kein Receipt.

## Konflikte

Dieselbe Handoff-ID mit anderer Decision, anderem Channel, anderer Revision
oder anderen Artefakt-/Evidence-Bytes ist
`ReleasePublicationHandoffConflict`.

Eine bereits verwendete Publication-Decision-ID darf keinem zweiten Handoff
zugeordnet werden. Es gibt kein Upsert, Überschreiben oder Version-Rebinding.

## Neutrale Ablehnung

Stale Channel-Revision, inaktiver Publisher, unbekannter Channel, aktuelle
Release-Revocation, falsche Signatur oder abweichende Promotion-Evidence
liefern neutral `None`.

`None` enthält keine Registry-, Channel-, Publisher- oder Keydetails und
erzeugt keine Teilentscheidung.

## Technische Nichtverfügbarkeit

Ungültige Typen, nicht kanonische Evidence, Datenbank-, Projektions-,
OpenSSH-, Clock-, Tar-/JSON- oder Dateisystemfehler ergeben detailarm
`ReleasePublicationHandoffUnavailable`.

DSN, SQL, Pfade, Providerdetails und ursprüngliche Exceptions verlassen die
Grenze nicht. Die Transaktion rollt vollständig zurück.

## Keine Publication

`ready_for_publication` ist nur eine persistente autorisierte Eingabe für
einen späteren Publisher.

LQ-251 erzeugt keinen Providerclient, Netzwerkaufruf, Package-Index-Eintrag,
Git-Release, Container-Tag, Receipt, Withdrawal oder Deploymentauftrag.

Ein aktiver Handoff ist kein Beleg, dass externe Bytes existieren.

## Migration und Bundle-Gate

LQ-251 verwendet die bestehende LQ-249-Handoff-Tabelle und benötigt keine
Migration. Head bleibt `20260817_0021`; das Bundle-Gate bleibt bei 21
Migrationen, vierzehn Entry Points und zwölf Operatormodulen.

## Nachweis

SQLite-Tests belegen erfolgreichen vollständigen Handoff, aktuelle
Promotion-Reverification, Publisher-/Channel-Auflösung, persistierte
`ready_for_publication`-Fakten, leere Receipts, exakten Retry ohne Projektion,
Decision-Konflikt, stale Revision, Publisher-Entzug und manipulierte Evidence.

Ein PostgreSQL-16-Test bestätigt dieselbe aktuelle Release-/Publication-
Bindung unter der normativen Lock-Reihenfolge.

Die vollständige Pflichtsuite besteht:

```text
3107 passed, 62 warnings
```

Der temporäre PostgreSQL-Cluster wurde kontrolliert gestoppt und entfernt.

## Bewusst nicht enthalten

LQ-251 implementiert keine reguläre Channel-/Publisher-Mutation, CLI,
Providergrenze, Receipt-Aufzeichnung, Publication-Execution, Reassessment,
Withdrawal, Git-, Netzwerk- oder Deploymentaktion.

## Nächster Slice

LQ-252 sollte den kontrollierten Publication-Executor-Vertrag entscheiden.
Er muss aktuellen Handoff, Revocation, Publisher und Channel erneut prüfen,
Provider-Upload und read-only Zielabgleich bei unklarem Ausgang trennen und
Receipt-/Observed-Hash-Semantik festlegen, ohne Deployment zu implementieren.
