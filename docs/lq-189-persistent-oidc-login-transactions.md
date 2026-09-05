# LQ-189 — Persistente OIDC-Login-Transaktionen

## 1. Ziel und Grenze

Dieser Slice implementiert die bestehenden Creation- und Claim-Ports für
OIDC-Login-Transaktionen auf der persistenten Datenbankgrenze. Pending-State
überlebt Prozesswechsel, kann genau einmal beansprucht werden und wird bei
Erfolg oder Ablauf atomar von allen Geheimnissen befreit.

Keine Route, OIDC-Verifikation, Identity-Bindung, Session-Erzeugung oder
Production-Composition wird ergänzt. Die bestehenden Login-Start- und
Callback-Anwendungsfälle bleiben unverändert.

## 2. Persistenter Zustand

Revision `20260812_0005` ergänzt `oidc_login_transactions`. Der opake State ist
bytegenauer Primärschlüssel. Ein Datensatz ist genau in einem Zustand:

- `pending`: alle erforderlichen Callback-Felder und Zeitwerte sind vorhanden;
- `used`: sämtliche Pending-Felder, einschließlich Admission-ID und Return-Path,
  sind `NULL`; nur State und der secret-freie Nutzungsstatus bleiben.

Die Migration enthält keine Seed-Daten und ändert keine bestehende Tabelle.
Der Check-Constraint verbietet halbe Pending-Datensätze und gebrauchte Records
mit verbliebenen Geheimnissen.

## 3. Erstellung und Nichtwiederverwendung

`add_transaction` speichert State und Record exakt und atomar. Es normalisiert,
trimmt und faltet keine Zeichen. Ein bereits pending oder früher verwendeter
State ergibt neutral `False`, überschreibt nichts und liest keine Uhr.

Die Datenbank entscheidet die Konkurrenz durch den Primärschlüssel und
`ON CONFLICT DO NOTHING`. Es gibt keinen Vorab-Check als Sicherheitsgrenze,
keinen In-Process-Lock und keinen automatischen Retry. Ein unbekannter Claim
reserviert den State nicht; eine spätere erstmalige Erstellung bleibt möglich.

## 4. Atomarer Claim

`claim_transaction` sperrt einen vorhandenen Datensatz auf PostgreSQL. Unbekannt
und bereits gebraucht ergeben einheitlich `None` ohne Uhrzugriff. Für einen
pending Datensatz wird die injizierte aware-UTC-Uhr genau einmal gelesen.

Noch vor dem Commit werden alle Pending-Felder gelöscht und der Status auf
`used` gesetzt. Ist `now >= expires_at`, liefert der Claim neutral `None`;
andernfalls liefert er den exakt rekonstruierten
`PendingOidcLoginTransaction`. In beiden Fällen ist derselbe State danach
dauerhaft nicht wiederverwendbar und seine Geheimnisse sind nicht mehr über den
Store erreichbar.

## 5. Zeit- und Datengrenze

Zeit kommt ausschließlich aus dem gespeicherten Record und der injizierten
Serveruhr. Naive, ungültige oder strukturell unbrauchbare Zeitwerte sind
technische Nichtverfügbarkeit. SQLite-ISO-Texte werden strikt über
`datetime.fromisoformat` decodiert; eine fehlende Zeitzone wird nie als UTC
interpretiert.

Issuer, Nonce, Verifier, Redirect-URI, Admission-ID und Return-Path werden als
exakte UTF-8-Bytes gespeichert und gelesen. Ungültige, leere oder nicht
decodierbare Persistenzwerte werden nicht ersetzt oder normalisiert.

## 6. Fehler- und Geheimnisgrenze

Normale Abwesenheit, Ablauf, bereits erfolgter Claim und State-Kollision bleiben
neutrale Ergebnisse. Datenbank-, Transaktions-, Decodierungs-, Struktur-, Uhr-
oder Commitfehler sind getrennte detailfreie technische Nichtverfügbarkeit.

Der Fehler trägt keine State-, Issuer-, Nonce-, Verifier-, Admission-, SQL-,
Tabellen-, Constraint-, Host- oder DSN-Details und verlässt die Grenze ohne
Cause oder Context. Das Adapter-`repr` ist konstant und wertfrei; die injizierte
Engine wird nicht geschlossen und `BaseException` bleibt ungefangen.

## 7. Retention-Untergrenze

Ein verwendeter oder abgelaufener State bleibt mindestens als secret-freier
Tombstone erhalten, solange ein alter Callback oder eine Wiedervergabe relevant
sein kann. Löschen und spätere Wiederverwendung desselben States sind ohne
einen eigenen Retention- und Nichtwiederverwendungsnachweis verboten.

Restore oder Reimport darf einen `used`-Datensatz weder wieder `pending` machen
noch seine früheren Geheimnisse rekonstruieren. Konkrete Aufbewahrungsfristen
und Löschverfahren bleiben späteren Datenschutz- und Retention-Slices
vorbehalten.

## 8. Nachweis und Folgeordnung

SQLite beweist Migration, Creation, Claim, Ablauf, Geheimnislöschung,
Nichtwiederverwendung, unbekannten Claim und detailfreie Fehler. Der markierte
PostgreSQL-Test beweist zwei echte gleichzeitige Claims: genau einer erhält den
Pending-Record, der andere neutral `None`.

Als nächster Slice folgen persistente Browser-Sessions mit atomarer Erstellung,
Lookup, Rotation und Revocation. Erst danach kann die vollständige Login- und
Onboarding-Kette kontrolliert in Production verdrahtet und LQ-177 wieder
aufgenommen werden.
