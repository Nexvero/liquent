# LQ-187 — Atomarer Bootstrap der ersten internen Identität

## 1. Ergebnis

LQ-187 implementiert den Vertrag aus LQ-186. Eine parameterlose interne
Persistenzgrenze legt genau einmal den ersten aktiven Nutzer, den ersten aktiven
Workspace, dessen aktive Onboarding-Verwaltungsautorität, eine offene
Identity-Admission und den historischen Bootstrap-Nachweis an.

Der Slice enthält keine CLI, HTTP-Route, Operator-Authentisierung,
Environment-Aktivierung oder Production-Verdrahtung. Die Operation ist daher
noch nicht von außen erreichbar.

## 2. Öffentliche Grenze

`IdentityAuthorityBootstrapStore.bootstrap_initial_identity(self)` nimmt keine
fachlichen Werte entgegen. Erfolg liefert
`BootstrappedIdentityAuthority(user_id, workspace_id, admission_id)`. Das
Ergebnis ist unveränderlich, slots-basiert, hashbar und blendet alle drei
Identifier aus `repr` aus.

Ein fremder nicht leerer Foundation-Bestand ergibt ausschließlich `None`.
Technische Störungen ergeben die detailfreie
`IdentityAuthorityBootstrapUnavailable`; eine normale innere Exception verlässt
die Grenze weder als Text noch als Cause oder Context. `BaseException` bleibt
ungefangen.

## 3. Interne Quellen

Der Datenbankadapter erhält Generatoren für `UserId`, `WorkspaceId`,
`ProvisioningRequestId` und `IdentityAdmissionId`, eine aware-UTC-Uhr und eine
positive Admission-Lebensdauer. Die Lebensdauer wird beim Bau geprüft. Die
parameterlose Methode liest jede Quelle erst nach der persistenten
Leereentscheidung und höchstens einmal. Es gibt keinen Generator-Retry.

Der Ablauf wird aus der einmal gelesenen Uhr plus der unveränderten Lebensdauer
gebildet. Die Admission beginnt offen und ungebunden. Keine Quelle stammt aus
OIDC, Callback, Session, Request oder Konfiguration des Browsers.

## 4. Migration

Revision `20260811_0004` ergänzt ausschließlich
`identity_authority_bootstrap_decisions`:

- `singleton_key` ist Primärschlüssel und per Check auf `1` beschränkt;
- `admission_id` ist eindeutig und verweist mit `ON DELETE RESTRICT` auf die
  erste Admission;
- die Migration enthält keinen Seed und kein Aktivierungsflag.

Nutzer, Workspace und interner Provisioning-Request werden verlustfrei über
die referenzierte Admission aufgelöst. Die vorhandenen Foundation- und
Admission-Tabellen bleiben unverändert.

## 5. Erstübergang

Der PostgreSQL-Adapter serialisiert die Leereentscheidung datenbankseitig an
der Singleton-Tabelle. Innerhalb derselben Transaktion prüft er zuerst eine
vorhandene Entscheidung, dann fremden Foundation-Bestand und erzeugt nur beim
vollständig leeren Zustand in dieser Reihenfolge Nutzer, Workspace, Autorität,
Admission und Entscheidung.

Jede Störung rollt die ganze Transaktion zurück. Insbesondere wird der
LQ-181-Adapter nicht nach einem Foundation-Commit aufgerufen; seine
Admission-Invarianten werden im selben Bootstrap-Commit erfüllt.

## 6. Wiederholung und Konkurrenz

Eine vorhandene vollständige Entscheidung wird über Admission, Foundation und
Autorität aufgelöst. Die Wiederholung liefert exakt dieselben drei Identifier,
ohne Uhr oder Generator, ohne Ablaufverlängerung und ohne eine konsumierte
Admission wieder zu öffnen. Statusänderungen ändern die historische Antwort
nicht; fehlende referenzierte Tatsachen sind dagegen technische Korruption.

Bei zwei PostgreSQL-Teilnehmern wartet einer an der transaktionalen
Datenbanksperre. Der Gewinner committet genau eine Foundation; der zweite liest
danach dieselbe Entscheidung und liefert dasselbe Ergebnis. Es gibt keinen
In-Process-Lock, Cache, Savepoint-Retry, automatischen Wiederholungsloop oder
zweiten Commit.

## 7. Nachweise

Portable Tests belegen Ergebnis- und Portform, die leere Migration,
Singleton-Check, restriktiven Foreign Key, Lifetime-Fail-fast, Erstübergang,
Wiederholung und Fehlergrenze. SQLite wird nicht als Konkurrenzbeweis benutzt.

Die markierten PostgreSQL-Tests belegen die vollständige referenzielle
Zuordnung, genau einen Quellenzugriff, Wiederholung nach Consumption ohne
Wiederöffnung, fremden Bestand als `None`, Rollback bei jeder Quelle und jeder
der fünf Schreibstufen, strukturelle Korruption als technische Störung sowie
zwei echte Teilnehmer mit einer einzigen Foundation und identischem Ergebnis.

## 8. Nicht enthalten und Folge

Unverändert offen bleiben die authentisierte Offline-Aufrufgrenze, reguläres
atomisches Onboarding, Membership und Rollen, Login-Transaktionspersistenz,
Sessionpersistenz und LQ-177. Kein bestehender OIDC-, Callback-, Session- oder
Transportvertrag wurde erweitert.
