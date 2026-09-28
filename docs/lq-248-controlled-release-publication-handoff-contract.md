# LQ-248 — Controlled Release Publication Handoff Contract

## 1. Ergebnis

LQ-248 entscheidet den Vertrag zwischen positiver LQ-247-Promotion-Evidence
und einer späteren kontrollierten Artefaktveröffentlichung.

Der Handoff autorisiert noch keinen Upload. Er bindet unveränderliche
Artefakte, aktuelle Trust-Prüfung, Zielkanal und getrennte
Publisher-Authority in eine idempotente spätere Publication-Entscheidung.

Dieser Slice implementiert weder Persistenz noch Publisher oder Deployment.

## 2. Getrennte Entscheidungen

Folgende Schritte bleiben unabhängig:

1. deterministischer Bundle-Build;
2. persistentes autorisiertes Signing;
3. aktuelle unabhängige Promotionprüfung;
4. Publication-Handoff;
5. tatsächliche Veröffentlichung;
6. Deployment in ein Environment.

Kein positives Ergebnis ersetzt einen nachfolgenden Schritt.

## 3. Keine Produkt- oder Signing-Authority

Publisher-Authority ist eine eigene Release-Control-Plane-Capability.

Sie folgt nicht aus SessionPrincipal, UserId, WorkspaceId, Membership,
Research-Permission, Signing-Key-Besitz, Signer-Authority,
Registry-Lifecycle-Authority, Promotion-Verifier oder Git-/CI-Zugriff.

Signing-Executor, Promotion-Verifier und Publisher müssen getrennt
zuordenbar bleiben.

## 4. Stabile interne Fakten

Spätere Implementierung benötigt mindestens stabile, nicht wiederverwendbare:

- Publication-Handoff-ID;
- Publisher-Authority-ID;
- Publication-Channel-ID;
- Publication-Decision-ID;
- Provider-Receipt-ID;
- Withdrawal- oder Reassessment-ID.

Keine ID wird aus Paketversion, Dateiname, Hash, Username, URL, Zeit oder
Environmentnamen abgeleitet.

## 5. Zielkanal als System-of-Record-Fakt

Ein Publication-Channel ist eine kontrolliert konfigurierte interne
Identität, nicht eine freie Caller-URL.

Sein System of Record bindet mindestens Providerart, kanonischen Zielnamen,
zulässige Artefaktklasse, Status und aktuelle Channel-Policy-Revision.

Credentials, Tokens und konkrete Providerclients bleiben außerhalb dieses
öffentlichen Fakts in einer kontrollierten Providergrenze.

## 6. Geschlossener Handoff-Request

Der spätere Handoff akzeptiert ausschließlich:

- neue stabile Handoff-ID;
- lokalen unveränderten Bundle-Pfad;
- detached Signaturpfad;
- neue positive Promotion-Evidence;
- ausgewählte stabile Channel-ID;
- exakt erwartete Channel-Policy-Revision.

Er akzeptiert keine freie Ziel-URL, Credentials, Authority-ID, Rolle,
Allow-Entscheidung, Public-Key-Datei oder behaupteten Published-Status.

## 7. Exakte Artefaktbindung

Bundle, Signatur und Promotion-Evidence werden jeweils einmal als
unveränderliche Bytes gelesen.

Der Handoff verlangt exakte Gleichheit von:

- Bundle-Dateiname und Bundle-SHA-256;
- Checksum-SHA-256;
- Signatur-SHA-256;
- Source-Commit und Paketversion;
- Signer-Authority, Key-ID und Fingerprint;
- Policy- und Registry-Bindung;
- unabhängiger Verification-Identität.

Callerpfade sind Bedienkontext und werden nicht als Identität persistiert.

## 8. Promotion-Evidence ist kein dauerhaftes Ticket

LQ-247-Evidence belegt eine Entscheidung zu ihrem `decided_at`-Zeitpunkt.

Vor Annahme eines neuen Handoffs muss dieselbe kontrollierte Grenze erneut die
aktuelle persistente Release-Registry prüfen. Alte positive Evidence darf
keine zwischenzeitliche Revocation, Deaktivierung, Expiry oder Policy-Sperre
übergehen.

Die neue Prüfung bindet denselben Bundle- und Signatur-Snapshot.

## 9. Publisher-Authority-Auflösung

Für einen neuen Handoff löst das System of Record selbst auf:

- Publisher-Actor existiert und ist aktiv;
- Actor besitzt aktuell Publisher-Authority für den Zielkanal;
- Channel existiert und ist aktiv;
- erwartete Channel-Policy-Revision ist aktuell;
- Artefaktklasse und Paketname sind im Channel zulässig;
- die Version ist dort nicht widersprüchlich belegt.

Kein vorher berechnetes Boolean oder Caller-Role ersetzt diese Auflösung.

## 10. Separation of Duties

Der Publisher-Actor darf nicht allein aufgrund eigener Signing- oder
Promotionaktion veröffentlichen.

Mindestens Promotion-Verifier und Publisher-Executor müssen verschieden sein.
Eine Policy darf zusätzlich Trennung zum Signing-Executor verlangen.

Ausnahmen benötigen eine eigene explizite Policy-Revision; es gibt kein
Emergency-Boolean im normalen Request.

## 11. Immutable Version Semantics

Ein Zielkanal darf dieselbe Paketversion nicht unter anderen Bundle-, Wheel-
oder Signaturbytes neu belegen.

Ein bytegleicher Retry derselben Publication-Decision ist zulässig. Eine
gleiche Version mit abweichendem Hash ist ein detailarmer Konflikt und kein
Update.

Korrekturen erhalten eine neue Paketversion und eine neue Decision-ID.

## 12. Persistenter Handoff

Ein angenommener Handoff persistiert mindestens:

- Handoff-ID und Publication-Decision-ID;
- Bundle-, Wheel-, Checksum-, Signatur- und Promotion-Evidence-Hash;
- Source-Commit, Paket- und Bundle-Formatversion;
- Signer, Key, Registry- und Policy-Revision;
- Promotion-Verifier und Promotionszeit;
- Publisher-Actor und Publisher-Authority;
- Channel und Channel-Policy-Revision;
- Annahmezeit und Status `ready_for_publication`.

Er enthält keine Credentials, Tokens, DSN, lokalen Pfade oder Providersecrets.

## 13. Kein Publish beim Handoff

Commit von `ready_for_publication` führt keinen Netzwerkaufruf aus.

Der Handoff erzeugt weder Package-Index-Eintrag noch Container-Tag,
Git-Release, Objekt-Upload oder Deployment. Er ist nur die persistente
autorisierte Eingabe für einen späteren Publisher-Executor.

Damit bleibt unklarer externer Erfolg vom Authority-Commit getrennt.

## 14. Spätere Publication-Execution

Ein späterer Executor muss vor Providerzugriff den Handoff, aktuelle
Publisher-Authority, Channelstatus und aktuelle Release-Revocation erneut
prüfen.

Er lädt ausschließlich die bereits hashgebundenen Bytes hoch und persistiert
danach Provider-Receipt, extern beobachtete Hashes und Publication-Zeit.

Eine Providerantwort ohne Hash-/Identitätsbestätigung ist kein Erfolg.

## 15. Idempotenz und unklarer Ausgang

Exakter Retry derselben Decision-ID mit identischen Artefakten, Channel und
Policy liefert dieselbe persistierte Entscheidung.

Nach unklarem Providerausgang muss der Executor zuerst den Zielkanal read-only
abfragen. Ein bereits exakt vorhandenes Artefakt kann mit demselben Receipt
oder einer kontrolliert rekonstruierten Bestätigung abgeschlossen werden.

Blindes erneutes Hochladen oder Überschreiben ist unzulässig.

## 16. Revocation und Reassessment

Revocation vor Publication sperrt jede neue Execution.

Revocation nach Publication löscht keine Historie und behauptet nicht, dass
externe Bytes verschwunden sind. Sie erzeugt einen neuen
Reassessment-/Withdrawal-Bedarf für alle betroffenen Publications.

Withdrawal, Yanking, Deprecation oder Channel-Sperre sind neue explizite
Entscheidungen; sie überschreiben keinen historischen Receipt.

## 17. Deployment bleibt getrennt

Publication bedeutet nur, dass ein unveränderliches Artefakt in einem
kontrollierten Distributionskanal verfügbar ist.

Sie gewährt keine Environment-Authority, wählt kein Zielsystem und startet
kein Rollout. Deployment verlangt eigene Artefaktauflösung, Environment-
Policy, Freigabe, Rollbackfähigkeit und aktuelle Reassessment-Prüfung.

## 18. Fehlergrenzen

Unbekannte oder inaktive Authority, stale Revision, gesperrter Channel,
abgelaufene Promotion, Revocation oder Hashabweichung ergeben dieselbe
detailarme fachliche Ablehnung.

Wiederverwendung einer stabilen ID oder Version mit anderem Inhalt ist ein
detailarmer Konflikt.

Datenbank-, Projektions-, Dateisystem-, Provider- und Strukturfehler bleiben
getrennte detailarme technische Nichtverfügbarkeit.

## 19. Retention und Nichtwiederverwendung

Handoffs, Decisions, Receipts, Reassessments, Withdrawals, Channel-Revisionen
und alle gebundenen Hashes werden mindestens so lange aufbewahrt, wie ein
Release, Deployment, Rollback, Incident oder Audit darauf verweist.

IDs, Versionbindungen und Receipts werden nie gelöscht und unter neuer
Bedeutung wiederverwendet. Provider-Credential-Retention bleibt getrennt.

## 20. Audit-Evidence

Positive Evidence muss Build-, Signing-, Promotion-, Handoff- und spätere
Publication-Evidence über Hashes verknüpfen, ohne sie zu einem gemeinsamen
mutierbaren Dokument zu verschmelzen.

Jede Stufe behält eigene Actor-, Policy-, Zeit- und Ergebnisfelder. Logs oder
stdout ersetzen keine persistente Decision.

## 21. Bewusst nicht entschieden

LQ-248 entscheidet keine Python-Typen, Ports, Exceptions, Tabellen,
Migrationen, SQL, Locks, Provider-SDKs, Package-Indexe, Container-Registries,
Git-Releases, CLI, Credentials, Versionserhöhung oder Deploymenttechnik.

Es erfolgt keine Datei-, Registry-, Git-, Netzwerk-, Publication- oder
Deploymentmutation.

## 22. Nächster Slice

LQ-249 sollte die persistente Publication-Handoff-Foundation und stabilen
Decision-Typen implementieren. Der Slice darf leere historienerhaltende
Channel-, Authority-, Policy-, Handoff- und Receipt-Strukturen schaffen, aber
keinen Seed, Bootstrap, Publisher, Upload oder Deployment enthalten.
