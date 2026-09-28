# LQ-252 — Controlled Release Publication Executor Contract

## 1. Ergebnis

LQ-252 entscheidet den Vertrag für den kontrollierten Executor, der einen
persistenten LQ-251-Handoff später tatsächlich in einen externen
Publication-Channel überführt.

Der Vertrag trennt Authority-Preflight, externe Publication, Reconciliation
und Receipt-Commit. Dieser Slice implementiert keinen Providerzugriff und kein
Deployment.

## 2. Voraussetzungen

Publication-Execution setzt voraus:

- persistenten Handoff mit Status `ready_for_publication`;
- unveränderlich auflösbare Bundle- und Signaturbytes;
- vollständige LQ-247-Promotion-Evidence;
- aktuellen aktiven Channel;
- aktuellen aktiven Publisher;
- weiterhin aktuelle Release-Authority ohne Revocation;
- kontrolliert injizierten Provideradapter.

Fehlt eine Voraussetzung, findet kein externer Write statt.

## 3. Getrennte Authority

Publication-Executor-Identität ist ein eigener stabiler interner Fakt.

Sie ist getrennt von:

- Signing-Executor;
- Promotion-Verifier;
- Publisher-Authority;
- Registry- und Channel-Lifecycle-Authority;
- SessionPrincipal und Produktrollen;
- Deployment- oder Environment-Authority.

Executor-Identität allein gewährt keine Publication. Maßgeblich bleibt die
aktuelle Publisher-Authority im Zielchannel.

## 4. Geschlossener Execution-Request

Ein späterer Request enthält ausschließlich:

- stabile Publication-Execution-ID;
- bestehende Handoff-ID;
- identifizierende Publisher-Authority-ID;
- exakt erwartete Channel-Policy-Revision.

Er enthält keine Artefaktbytes, Ziel-URL, Credentials, Provider-Receipt,
Rolle, Allow-Entscheidung, Hashüberschreibung oder Deploymentangabe.

Alle übrigen Fakten werden aus persistentem Handoff und System of Record
aufgelöst.

## 5. Unveränderliche Artefaktquelle

Der Executor liest Bundle, Signatur und Promotion-Evidence über eine
kontrolliert injizierte Artifact-Source-Grenze.

Die Quelle wird ausschließlich mit den im Handoff gebundenen Identitäten und
Hashes angesprochen. Sie darf keine freie Caller-URL oder Pfadsubstitution
akzeptieren.

Vor Providerzugriff werden die vollständigen Bytes erneut gehasht. Bundle-,
Wheel-, Checksum-, Signatur- und Evidence-Hash müssen exakt dem Handoff
entsprechen.

## 6. Erneuter Bundle- und Trust-Preflight

Ein Handoff ist kein dauerhaftes Publish-Ticket.

Jede neue Execution muss vor externem Write erneut prüfen:

- vollständige LQ-236-Bundle-Integrität;
- detached SSHSIG und SHA256SUMS-Bindung;
- aktuelle aktive Signer-Authority und Key;
- aktuelle Policy und Registry-Revision;
- aktuellen Channel und erwartete Channel-Revision;
- aktuelle Publisher-Authority;
- keine offene sperrende Reassessment-/Withdrawal-Entscheidung.

Es gibt keinen positiven Authority-Cache oder Grace-Boolean.

## 7. Execution-Attempt als persistente Grenze

Vor dem ersten Provideraufruf persistiert die Control Plane eine
unveränderliche Execution-Attempt-Entscheidung.

Sie bindet mindestens:

- Execution-ID und Handoff-ID;
- Publisher-Actor und Executor-Identität;
- Channel und Channel-Policy-Revision;
- alle Handoff-Artefakthashes;
- Providerart und kanonischen Zielnamen;
- Attempt-Nummer und Startzeit;
- Status `prepared`.

Ohne committeten Attempt findet kein Provider-Write statt.

## 8. Warum kein Datenbanklock über Netzwerk

Die Datenbanktransaktion wird nicht während eines unbeschränkten externen
Provideraufrufs offen gehalten.

Ein lang gehaltener Registry- oder Channel-Lock würde Revocation blockieren
und externe Latenz in die Control Plane tragen.

Stattdessen trennt der Attempt den autorisierten Preflight vom externen
Effekt. Nach dem Aufruf folgt zwingend eine neue aktuelle Reconciliation.

## 9. Providergrenze

Der Provideradapter besitzt getrennte Methoden für:

- read-only Zielinspektion;
- immutable Create/Upload;
- read-only Receipt-/Hash-Auflösung.

Er erhält nur kontrollierten Channelkontext, Paketversion und exakt
hashgeprüfte Artefaktbytes.

Er erhält keine Datenbankengine, Authority-Snapshots, Rollen, private
Signing-Keys oder Deploymentdaten.

## 10. Create-only Semantik

Publication ist ausschließlich create-only.

Der Provider darf weder bestehende Versionen überschreiben noch mutable
Tags, Aliase oder "latest" als normative Identität verwenden.

Existiert die Version bereits mit anderen Hashes, ist das ein Konflikt. Ein
bytegleiches vorhandenes Artefakt kann ausschließlich über Reconciliation als
idempotenter Erfolg bestätigt werden.

## 11. Read-before-write

Vor jedem Create prüft der Executor das Ziel read-only.

Mögliche Resultate:

- Ziel fehlt: kontrollierter Create darf beginnen;
- Ziel existiert mit exakt denselben Hashes: kein neuer Upload, Reconciliation;
- Ziel existiert mit anderen Hashes: detailarmer Konflikt;
- Zielzustand technisch nicht feststellbar: kein Write.

Blindes Hochladen ist unzulässig.

## 12. Eindeutige Provider-Idempotenz

Falls der Provider native Idempotency-Keys unterstützt, wird ausschließlich
die stabile interne Execution-ID verwendet.

Fehlt native Unterstützung, bleiben unveränderliche Zielidentität,
read-before-write und read-after-unknown verpflichtend.

Eine neue zufällige Provider-ID bei Retry darf keinen zweiten externen
Artefaktbestand erzeugen.

## 13. Erfolgreicher Provideraufruf

Eine positive API-Antwort allein ist kein Publication-Erfolg.

Der Executor muss anschließend read-only bestätigen:

- kanonische externe Artefaktidentität;
- Paketname und Version;
- beobachteten Bundle-/Artefakthash;
- Provider-Receipt oder unveränderliche Providerrevision;
- tatsächliche Sichtbarkeit im erwarteten Channel.

Nur bestätigte externe Fakten dürfen persistiert werden.

## 14. Unknown Outcome

Timeout, Verbindungsabbruch oder Prozessverlust nach möglichem Provider-Write
erzeugt Status `outcome_unknown`.

Der nächste Retry führt keinen sofortigen zweiten Upload aus. Er inspiziert
zuerst das Ziel read-only:

- exakt vorhanden: Receipt kontrolliert rekonstruieren und abschließen;
- nicht vorhanden und Provider bestätigt fehlenden Write: neuer Attempt darf
  nach aktuellem Preflight beginnen;
- abweichend vorhanden: Konflikt und Security-Reassessment;
- weiterhin unklar: `outcome_unknown` bleibt bestehen.

Unknown ist niemals stillschweigend Erfolg oder Ablehnung.

## 15. Aktuelle Reconciliation nach externem Effekt

Nach jedem möglichen externen Write werden Release-Registry, Channel,
Publisher-Authority und Reassessment-Status erneut aktuell gelesen.

Bleibt alles zulässig und stimmen externe Hashes, kann das Receipt normal
committet werden.

Wurde während des Provideraufrufs revokiert oder deaktiviert, muss der
externe Fakt trotzdem historisch als Receipt erfasst werden; gleichzeitig
wird atomar ein `pending` Reassessment erzeugt. Externe Realität darf nicht
verschwiegen werden.

## 16. Persistentes Receipt

Ein Receipt bindet mindestens:

- stabile Provider-Receipt-ID;
- Handoff- und Execution-ID;
- Channel und externe kanonische Artefaktidentität;
- beobachtete Bundle-/Artefakthashes;
- Providerrevision;
- Publication- und Bestätigungszeit;
- Reconciliation-Ergebnis;
- Status `published` oder `published_reassessment_required`.

Provider-Credentials, Tokens und rohe HTTP-Antworten werden nicht gespeichert.

## 17. Exakter Retry

Ein abgeschlossenes Receipt macht dieselbe Execution-ID idempotent.

Exakter Retry liefert dasselbe Receipt ohne Provider-Write. Abweichende
Wiederverwendung von Execution-ID, Handoff, Channel oder Hashbindung ist ein
detailarmer Konflikt.

Eine andere Execution-ID für einen bereits veröffentlichten Handoff wird
nur über read-only Reconciliation auf dasselbe externe Artefakt bezogen und
darf kein zweites Artefakt erzeugen.

## 18. Konkurrenz

Für denselben Handoff darf höchstens ein neuer write-fähiger Attempt zugleich
wirksam sein.

Die Persistenzgrenze serialisiert Attempt-Erzeugung. Andere Prozesse sehen
`prepared`, `outcome_unknown` oder abgeschlossenes Receipt und dürfen nicht
parallel blind schreiben.

Unterschiedliche Channels bleiben getrennte Handoffs und Entscheidungen.

## 19. Reassessment und Withdrawal

Ein `pending` Reassessment sperrt neue Publication-Executions für denselben
Handoff oder dieselbe kompromittierte Signing-Bindung.

Withdrawal ist eine eigene kontrollierte spätere Provideroperation. Sie
überschreibt oder löscht weder Receipt noch ursprünglichen Handoff.

Providerseitiges Yanking oder Deprecation muss als neue Evidence erfasst
werden. Physische Löschung ist kein impliziter Standard.

## 20. Fehlergrenzen

Fehlende aktuelle Authority, Revocation, stale Channel, offene Sperre oder
nicht passende Artefakthashes ergeben detailarme fachliche Ablehnung.

ID-/Versionswiederverwendung mit anderem Inhalt ist ein detailarmer Konflikt.

Artifact-Source-, Datenbank-, Provider-, Netzwerk- und Strukturfehler sind
detailarme technische Nichtverfügbarkeit. Möglicher externer Effekt wird
jedoch als `outcome_unknown` statt als gewöhnlicher Fehler festgehalten.

## 21. Retention

Attempts, Unknown-Outcomes, Receipts, externe Identitäten, beobachtete Hashes,
Reassessments und Withdrawals bleiben mindestens so lange erhalten, wie ein
Release, Deployment, Rollback, Incident oder Audit darauf verweist.

Execution- und Receipt-IDs werden nie gelöscht und unter neuer Bedeutung
wiederverwendet.

## 22. Keine Deploymentwirkung

Ein persistiertes Receipt bestätigt ausschließlich externe Verfügbarkeit im
Publication-Channel.

Es startet kein Deployment, wählt kein Environment, aktualisiert keine
Runtime und gewährt keine Deployment-Authority.

Deployment muss Receipt, aktuelle Reassessment-Lage und exakte Artefakthashes
in einer separaten Control Plane erneut prüfen.

## 23. Bewusst nicht entschieden

LQ-252 implementiert keine Python-Typen, Ports, Exceptions, Tabellen,
Migrationen, SQL, Provider-SDKs, Artifact Store, CLI, Credentials,
Package-Index-, Git-Release-, Container-, Netzwerk- oder Deploymentaktion.

Es wird kein Attempt, Receipt, Reassessment oder externer Zustand erzeugt.

## 24. Nächster Slice

LQ-253 sollte die persistente Publication-Execution-Foundation und stabilen
Attempt-/Executor-Typen implementieren. Sie muss Attempt-Status,
Unknown-Outcome, Receipt-Reconciliation und eindeutige write-fähige
Handoff-Bindung historienerhaltend vorbereiten, ohne Providerzugriff, Upload
oder Deployment.
