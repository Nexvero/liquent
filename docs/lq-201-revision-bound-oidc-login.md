# LQ-201 — Revision-bound OIDC Login

## Ergebnis

LQ-201 bindet jeden persistent gestarteten OIDC-Login an genau die aktive
Trust-Revision, aus der seine Authorization-Anfrage gebaut wurde.

Der Callback liest den aktuell aktiven Trust erneut und akzeptiert die bereits
beanspruchte Login-Transaktion nur, wenn ihre Revision noch exakt aktiv ist.
Diese Prüfung geschieht vor Token-Austausch, JWKS-Zugriff und Clock-Read.

Damit genügt ein weiterhin gleicher Issuer nach Rotation nicht mehr. Eine neue
Revision macht alle noch offenen Transaktionen der alten Revision neutral
unbrauchbar.

## Aktiver Trust-Snapshot

`ActiveOidcTrustSnapshot` enthält genau zwei zusammengehörige Fakten:

- die stabile interne `OidcTrustRevisionId`,
- die vollständige unveränderliche `TrustedOidcClientConfiguration`.

Beide Felder sind unveränderlich und aus `repr` ausgeschlossen. Der Snapshot
enthält keinen Actor, keine Session, Rolle, Authority, Membership, Permission,
Änderungsentscheidung oder browsergelieferte Providerwahl.

Der neue parameterlose `ActiveOidcTrustLookup` akzeptiert weder Issuer noch
Revision oder Allow-Entscheidung. Der persistente Adapter liest Revision und
Konfiguration gemeinsam aus dem systemeigenen aktiven Singleton.

Leer und explizit inaktiv ergeben neutrales `None`. Eine als aktiv markierte
Konfiguration ohne gültige Revision ist kein neutraler Altbestand, sondern
detailfreie technische Nichtverfügbarkeit.

Der ältere reine Konfigurations-Lookup bleibt als Kompatibilitätsgrenze für
bestehende isolierte Komponenten und Tests erhalten. Die persistente
Production-Composition verwendet dagegen den revisionsgebundenen Snapshot.

## Schemaerweiterung

Die additive Migration `20260812_0010` ergänzt:

- `revision_id` am aktiven OIDC-Konfigurations-Singleton,
- `expected_trust_revision` an pending OIDC-Login-Transaktionen,
- Foreign-Key-Bindungen beider Werte an die unveränderlichen LQ-199-Revisionen.

Die Spalten sind migrationsverträglich nullable. Daraus entsteht jedoch keine
Runtime-Freigabe für revisionslosen aktiven persistenten Trust. Der sichere
Lookup behandelt genau diesen Zustand fail-closed als technisch nicht nutzbar.

Die Migration erzeugt keine Revision, keine aktive Konfiguration und keinen
Login. Sie migriert oder errät keine Legacy-Konfiguration und setzt keinen
Default.

## Login-Start

`prepare_oidc_login_authorization` liest den aktiven Trust genau einmal.
Revision und Konfiguration dieses einen Snapshots speisen gemeinsam:

- die gespeicherte erwartete Revision,
- den erwarteten Issuer,
- die gespeicherte Redirect-URI,
- Authorization Endpoint, Client-ID, Scopes und Redirect-URI der Anfrage.

Ein Login-Start kann deshalb keine Werte aus zwei Rotationsständen mischen.
Der Browser kann weder Revision noch Issuer, Provider oder Konfiguration
auswählen.

Ist kein aktiver Trust vorhanden, endet der Start wie bisher neutral als nicht
verfügbar, bevor Material erzeugt oder eine Transaktion gespeichert wird.

`PendingOidcLoginTransaction.expected_trust_revision` ist ein repr-freier
interner Korrelationswert. Er erteilt keine Trust-Management-Authority und ist
kein übertragbarer Capability-Token.

## Persistente Transaktion

Der Datenbankadapter speichert die erwartete Revision atomar mit State, Issuer,
Nonce, PKCE-Verifier, Redirect-URI, Zeitgrenzen und optionalem Admission-Bezug.

Beim Claim wird sie aus demselben gesperrten Datensatz rekonstruiert. Die
bestehende Einmaligkeits- und Ablaufsemantik bleibt unverändert.

Sobald eine pending Transaktion beansprucht wird, ersetzt der Adapter auch die
Revision durch `NULL`, gemeinsam mit den übrigen geheimen oder korrelierenden
Werten. Der State-Tombstone bleibt zur dauerhaften Nichtwiederverwendung
erhalten.

Ein fremder oder nicht vorhandener Revisionswert kann wegen der persistenten
Bindung nicht als reguläre pending Transaktion eingefügt werden. Technische
Constraint- oder Datenbankfehler bleiben detailfrei.

## Callback-Neuprüfung

Der Callback übernimmt die erwartete Revision ausschließlich aus der atomar
beanspruchten serverseitigen Transaktion in die Verification-Eingabe.

Der Verifier liest danach den aktuell aktiven Trust genau einmal. Er vergleicht
zuerst dessen interne Revision mit der erwarteten Revision.

Folgende Zustände enden neutral mit `None`:

- kein aktuell aktiver Trust,
- eine andere aktuell aktive Revision,
- danach ein abweichender erwarteter Issuer,
- eine reguläre Ablehnung in Token- oder ID-Token-Verifikation.

Revision-Mismatch und fehlender aktiver Trust werden geprüft, bevor irgendein
Providerzugriff oder Clock-Read stattfindet. Token Endpoint und JWKS sehen in
diesem Fall keinen Request.

Stimmen Revision und Issuer überein, reicht der Verifier dasselbe unveränderte
Konfigurationsobjekt durch Token-Austausch, JWKS-Cache und Tokenprüfung. Während
eines einzelnen Verifikationsversuchs wird kein zweiter Trust-Stand gemischt.

## Rotation und Widerruf

Eine später atomar aktivierte Revision wirkt sofort auf spätere Entscheidungen.
Noch offene Transaktionen einer vorherigen Revision werden abgelehnt, selbst
wenn beide Revisionen denselben Issuer, Client oder Endpoint enthalten.

Eine spätere Deaktivierung wirkt ebenso: der aktuelle Lookup liefert neutral
keinen aktiven Trust, und der Callback erreicht kein Provider-Netzwerk.

LQ-201 selbst implementiert noch keine Aktivierung, Rotation, Deaktivierung
oder Authority-Prüfung. Er stellt nur die notwendige fail-closed Konsumgrenze
bereit, auf der diese Mutation sicher aufbauen kann.

## Fehler- und Datenschutzgrenze

Trust-Abwesenheit, Inaktivität, Revisionswechsel und Issuer-Mismatch bleiben
indistinguishable fachliche Ablehnungen. Sie erzeugen keinen neuen Fehlertyp und
verraten keine vorhandene Revision oder Konfiguration.

Nicht lesbare, revisionslose oder beschädigte aktive Persistenz sowie
Datenbank-, Netzwerk-, Cache-, Clock- oder Verifikationsfehler bleiben über die
bestehenden detailfreien technischen Grenzen getrennt.

Kein Fehlertext oder `repr` enthält Revision, Code, State, Nonce, Verifier,
Issuer, Redirect-URI, Token, Claim, SQL, DSN oder Providerantwort. Unerwartete
Fehler werden nicht als fachlicher Revisions-Mismatch ausgegeben.

## Tests

Die Tests belegen:

- exakte unveränderliche Snapshot-Bindung von Revision und Konfiguration,
- neutralen leeren und inaktiven Trust sowie fail-closed revisionslosen Bestand,
- Übernahme der aktiven Revision durch Login-Start und pending Transaktion,
- persistentes Roundtrip und Scrubbing der Revision beim Claim,
- Weitergabe der beanspruchten Revision an die Verification-Eingabe,
- Ablehnung einer geänderten Revision vor Token, JWKS und Clock,
- gleiche Issuer-Werte erlauben keine Umgehung des Revisionsvergleichs,
- unveränderte Legacy-Kompatibilität außerhalb der persistenten Production-
  Composition,
- Migration Head `20260812_0010` und Upgrade-Pfad.

## Bewusst nicht enthalten

- keine reguläre Trust-Aktivierung, Rotation oder Deaktivierung,
- keine Authority-Auflösung oder persistente Änderungsentscheidung,
- keine neue Route, CLI, Settings-Option oder Environment-Auswahl,
- keine Discovery, Secret-Verwaltung oder Provider-Metadaten-Aktualisierung,
- keine Nutzer-, Workspace-, Membership- oder Permission-Mutation,
- kein Retry einer bereits beanspruchten Login-Transaktion,
- kein Deployment und keine automatische Bootstrap-Ausführung.

## Nächster Schritt

LQ-202 sollte die reguläre autorisierte OIDC-Trust-Mutation implementieren. Sie
muss aktuelle globale Authority, unveränderliche Revision, Aktivierung oder
Deaktivierung und idempotente Änderungsentscheidung in einer persistenten
atomaren Ordnung verbinden. Erst danach folgt eine separate Operatorgrenze.
