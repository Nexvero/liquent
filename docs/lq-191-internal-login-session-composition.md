# LQ-191 — Interne Login-/Session-Composition

## 1. Ziel und Grenze

Dieser Slice verdrahtet die persistenten OIDC-Login-Transaktionen aus LQ-189
und Browser-Sessions aus LQ-190 um dieselbe extern besessene Engine, dieselbe
aware-UTC-Serveruhr und den bestehenden kryptografischen
Session-Materialgenerator.

Die Composition ist intern. Sie ergänzt keine HTTP-Route, Cookie-Policy,
OIDC-Konfiguration, Verifikation, Identity-Bindung oder automatische
Startup-Ausführung.

## 2. Engine und Uhr

`compose_login_sessions` erhält eine bereits erzeugte Engine. Sie liest keine
DSN, erzeugt keinen zweiten Pool und schließt die Engine nicht. Lifecycle und
Disposal bleiben bei der äußeren Process-Composition.

Eine injizierte Uhr wird gemeinsam für Transaction-Claim, Session-Lookup,
Rotation und Revocation verwendet. Ohne Testuhr gilt `datetime.now(UTC)`.
Browser-, Token-, Claim- oder Request-Zeit wird nicht übernommen.

## 3. Zusammengesetzte Fähigkeiten

`LoginSessionComposition` stellt intern bereit:

- `transactions`: persistente Creation und Claim von OIDC-Login-Transaktionen;
- `sessions`: persistente Creation, Lookup, Rotation und Revocation;
- `material`: den bestehenden sicheren SessionId-/CSRF-Generator;
- `issue_session(principal)`: sichere Ausgabe und atomare Speicherung;
- `rotate_session(session_id)`: frisches Material und atomare Rotation.

Die Stores bleiben dieselben bestehenden Portimplementierungen. Die Composition
fügt keine Inspektions-, Listing-, Lösch- oder Administrationsmethode hinzu.

## 4. Session-Material und Policy

Der Generator zieht Session-ID und CSRF-Token unabhängig über
`secrets.token_urlsafe` mit der bestehenden Mindestentropie von 32 Byte. Keine
Ableitung aus UserId, Login-State, Zeit oder vorherigem Session-Material.

Die positive Session-Lifetime wird einmal beim Aufbau gebunden. Sie ist kein
frei variierender Parameter einzelner Issue- oder Rotate-Aufrufe. Ungültige
Policy verhindert die Composition, bevor ein Store oder Generator benutzt
wird.

`issue_session` erhält einen bereits intern bestimmten `SessionPrincipal`.
`rotate_session` erhält keinen Principal; der persistente Store übernimmt ihn
ausschließlich aus der gesperrten Quellsession.

## 5. Fehler- und Geheimnisgrenze

Composition-seitig gibt es keinen Retry, keine Fehlerumdeutung und keinen
Fallback. Konflikte, neutrale Ergebnisse und detailfreie technische Fehler der
Anwendungsfälle und Stores behalten ihre bestehende Bedeutung.

Das Composition-`repr` ist konstant und enthält weder Engine, Uhr, Lifetime,
Materialgenerator noch Session- oder Login-Daten. Es wird nichts geloggt und
`BaseException` bleibt ungefangen.

## 6. Nicht enthalten

Keine Migration: LQ-191 nutzt ausschließlich Revisionen `0005` und `0006`.
Keine Route, Cookies, Header, CSRF-Transportprüfung, aktive OIDC-Konfiguration,
Authorization-Request-Erstellung, Tokenverifikation, Admission-Konsum oder
Identity-Bindung.

Die Composition wird nicht automatisch an `create_app` übergeben und öffnet
keinen Bootstrap- oder Onboarding-Pfad. Das endgültige Production-Wiring bleibt
ein eigener Slice mit vollständiger Dependency-Gate-Prüfung.

## 7. Nachweis und Folgeordnung

Unit-Tests beweisen Struktur, feste Policy, sichere Materialquelle, wertfreies
`repr` und fehlende Engine-Eigentümerschaft. Der markierte PostgreSQL-Test
durchläuft auf einer Engine Transaction-Creation und Claim, Session-Ausgabe,
Rotation, Lookup und Revocation.

Damit sind die zuvor fehlenden persistenten Grundlagen für Admission,
Login-Transaktionen und Sessions vorhanden. Als nächster Slice kann LQ-177
Production-Wiring kontrolliert wieder aufgenommen werden; Operator- oder
Onboarding-Transport bleibt weiterhin eine separate Sicherheitsgrenze.
