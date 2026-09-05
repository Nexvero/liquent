# LQ-190 — Persistente Browser-Sessions

## 1. Ziel und Grenze

Dieser Slice implementiert die bestehenden Browser-Session-Ports persistent:
Lookup, atomare Erstellung, Rotation und idempotente Revocation. Sessions
überleben Prozesswechsel und mehrere App-Instanzen teilen dieselbe
Sicherheitsentscheidung.

Keine Route, Cookie-Policy, Login-Composition oder Production-Verdrahtung wird
ergänzt. Die bestehenden Session-Anwendungsfälle und Materialgeneratoren
bleiben unverändert.

## 2. Persistenter Datensatz

Revision `20260812_0006` ergänzt `browser_sessions` mit bytegenauer Session-ID,
internem UserId-Bezug, serverseitigem CSRF-Token, aware Ablaufzeit und optionaler
Revocation-Zeit. Es gibt keine Seed-Daten und keine Änderung bestehender
Tabellen.

Die Session-ID ist Primärschlüssel und bleibt nach Ablauf oder Entzug belegt.
Damit kann eine alte Cookie-ID niemals später auf eine neue Session zeigen.
Konkrete Löschung oder Retention bleibt einem eigenen Nichtwiederverwendungs-
und Datenschutzvertrag vorbehalten.

## 3. Erstellung und Lookup

`add_session` fügt exakt einen Record mit `ON CONFLICT DO NOTHING` ein. Eine
jemals belegte ID ergibt neutral `False`, überschreibt nichts und wird nicht
durch einen automatischen Retry ersetzt.

`get_session` gibt nur eine bekannte, nicht entzogene und noch nicht abgelaufene
Session zurück. `now >= expires_at` ist neutral inaktiv. Principal und
serverseitiges CSRF-Token werden exakt rekonstruiert; unbekannt, abgelaufen und
entzogen bleiben nach außen `None`.

## 4. Atomare Rotation

Rotation sperrt auf PostgreSQL die Quellsession. Der Aufrufer liefert nur neue
opake Session-ID, CSRF-Token und Ablaufzeit; der Adapter übernimmt den Akteur
ausschließlich aus dem gespeicherten Quellrecord.

Nur eine aktive Quelle und eine freie, künftig gültige Ersatz-ID erlauben
Erfolg. Ersatzinsert und Revocation der Quelle committen gemeinsam oder gar
nicht. Kollision, unbekannte, abgelaufene oder entzogene Quelle ergeben neutral
`False`; bei Ersatzkollision bleibt die Quelle aktiv.

Zwei konkurrierende Rotationen werden durch die Datenbank geordnet. Höchstens
eine kann die Quelle aktiv sehen und einen Ersatz committen. Kein
In-Process-Lock, Check-then-act über getrennte Transaktionen oder automatischer
Retry.

## 5. Revocation

Revocation sperrt einen vorhandenen Record und ist idempotent. Unbekannte,
bereits entzogene oder abgelaufene Sessions sind neutrale No-ops. Eine aktive
Session erhält exakt die einmal gelesene aware Serverzeit als `revoked_at`.

Die Methode liefert keinen Existenz- oder Statushinweis. Entzug wirkt auf jedes
spätere Lookup und der Datensatz bleibt als Nichtwiederverwendungsnachweis
erhalten.

## 6. Zeit-, Fehler- und Geheimnisgrenze

Alle Entscheidungen nutzen ausschließlich die injizierte aware-UTC-Serveruhr.
Naive oder unbrauchbare Zeit ist technische Nichtverfügbarkeit. SQLite-ISO-Zeit
wird strikt decodiert und nie ohne Offset als UTC interpretiert.

Normale Abwesenheit, Ablauf, Entzug und Kollision bleiben neutrale Ergebnisse.
Datenbank-, Transaktions-, Struktur-, Decodierungs-, Uhr- oder Commitfehler sind
getrennte detailfreie technische Nichtverfügbarkeit ohne Cause oder Context.
Session-ID, UserId, CSRF, SQL, Host und DSN bleiben unsichtbar. Das Adapter-
`repr` ist konstant, die Engine wird nicht geschlossen und `BaseException`
bleibt ungefangen.

## 7. Nachweis und Folgeordnung

SQLite beweist Migration, Creation, Lookup, Ablauf, Entzug, Kollision,
Principal-Bindung, atomare Rotation und Nichtwiederverwendung. Der markierte
PostgreSQL-Test beweist zwei echte konkurrierende Rotationen mit genau einem
Erfolg.

Als nächster Slice folgt die kontrollierte Login- und Session-Composition um
dieselbe extern besessene Engine. Erst danach kann LQ-177 Production-Wiring mit
persistenten Admissions, Login-Transaktionen und Sessions wieder aufgenommen
werden.
