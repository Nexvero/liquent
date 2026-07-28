# LQ-129 — Provider-Neutral Identity Boundary

## Status

Architekturentscheidung und Vertrag. Keine Implementierung, kein Anbieter und
keine Freigabe einer Laufzeitumgebung.

## Entscheidung

Liquent authentifiziert Benutzer nicht mit selbst gespeicherten Passwörtern.
Eine spätere externe Authentifizierungsgrenze verwendet providerneutral
OpenID Connect mit Authorization Code Flow und PKCE.

Erfolgreiche externe Authentifizierung beweist nur eine Identität. Sie erteilt
keine Workspace-Mitgliedschaft, Rolle oder fachliche Berechtigung. Diese
Autorisierung bleibt ausschließlich in Liquent.

## Vertrauens- und Identitätsmodell

- Die dauerhafte externe Identität ist ausschließlich das verifizierte Paar
  `(issuer, subject)`.
- Dieses Paar wird genau einem internen `UserId` zugeordnet.
- E-Mail-Adresse, Benutzername, Anzeigename und andere veränderliche Claims
  sind keine dauerhaften Identitätsschlüssel.
- Eine E-Mail-Übereinstimmung verknüpft niemals automatisch Konten.
- Nur explizit vertrauenswürdige Issuer dürfen Identitäten liefern.
- IdP-Tokens sind Nachweise an der äußeren Grenze, keine Liquent-Sessions.

## Konzeptioneller Ablauf

### Login-Start

1. Liquent erzeugt einmalige, kurzlebige Werte für `state`, `nonce` und PKCE.
2. Der Browser wird zum konfigurierten, vertrauenswürdigen Issuer umgeleitet.
3. Die Login-Anfrage enthält keine interne Rolle oder Berechtigung.

### Callback

Vor jeder internen Identitätszuordnung prüft die Grenze vollständig:

- exakte Übereinstimmung von `state`,
- erwartete `nonce`,
- gültigen PKCE-Nachweis,
- Signatur und zulässigen Signaturalgorithmus,
- exakt vertrauenswürdigen Issuer,
- erwartete Audience,
- Ablauf und sonstige verpflichtende Zeitgrenzen.

Erst danach darf `(issuer, subject)` einem internen `UserId` zugeordnet werden.
Erst nach dieser Zuordnung und erfolgreicher atomarer Speicherung darf Liquent
eine eigene Browser-Session ausgeben.

### Fehlergrenze

Jeder abgelehnte Login endet neutral. Antworten unterscheiden nicht, ob ein
Nutzer, eine E-Mail-Adresse, ein Subject, eine Einladung oder eine externe
Identitätsbindung bekannt ist. Externe Fehlertexte und Tokeninhalte werden
nicht ungefiltert weitergegeben.

## Token- und Datenvertraulichkeit

- ID-, Access- und Refresh-Tokens des Identity Providers werden niemals als
  `liquent_session`-Cookie verwendet.
- IdP-Tokens erscheinen nicht in URL, Query, Logs, Telemetrie, Web Storage,
  fachlichen Anwendungsdaten oder Client-Fehlermeldungen.
- Die spätere Callback-Grenze verarbeitet nur die für Verifikation und
  Identitätszuordnung notwendigen Claims.
- Die vorhandene opake Liquent-Session bleibt vom IdP-Token getrennt und folgt
  ihrem eigenen Ablauf-, Rotations- und Widerrufsvertrag.

## Onboarding und Autorisierung

- Eine erfolgreiche Anmeldung erzeugt keine automatische Berechtigung.
- Workspace-Zugriff setzt kontrolliertes Onboarding, eine Einladung oder eine
  bereits vorhandene interne Zuordnung voraus.
- Workspace-Mitgliedschaften, Rollen und Berechtigungen werden ausschließlich
  durch die bestehenden internen Autorisierungsgrenzen entschieden.
- Fehlende Mitgliedschaft bleibt eine Autorisierungsentscheidung und wird
  nicht durch IdP-Claims ersetzt.

## MFA und Step-up

Der Identity Provider verantwortet Authentifizierungsfaktoren und deren
Prüfung. Liquent kann später für besonders schützenswerte Aktionen erwartete
Assurance-Claims verlangen. Konkrete Claim-Profile, Richtlinien und Aktionen
bleiben separate Entscheidungen.

## Logout-Grenze

Der vorhandene lokale Liquent-Logout widerruft ausschließlich die
Liquent-Browser-Session. Er behauptet keinen Logout beim Identity Provider.
Föderierter Logout, Single Logout und providerweite Sitzungsbeendigung bleiben
eine eigene Entscheidung.

## Erweiterungsgrenzen

Enterprise-SSO, mehrere vertrauenswürdige Issuer, tenant-spezifische
Providerkonfiguration und sichere Kontoverknüpfung sind spätere explizite
Erweiterungen. Keine davon wird aus E-Mail-Domänen oder ungeprüften Claims
automatisch abgeleitet.

## Bewusst nicht enthalten

- kein konkreter Identity Provider,
- keine Login-, Callback- oder Token-Route,
- keine OAuth-/OIDC-Bibliothek,
- keine neuen Ports oder Datenmodelle,
- keine Persistenz oder Kontoverknüpfungsimplementierung,
- kein Composition- oder Production-Wiring,
- keine CORS-, Deployment- oder Shared-Environment-Änderung,
- kein Release und kein Deployment.

## Nächste Architekturentscheidung

Vor realer Nutzung folgt eine separate Persistenzentscheidung für externe
Identitätsbindungen, Login-Transaktionen und den atomaren Session Store. Erst
danach dürfen konkrete Ports, Adapter und Routen geplant werden.
