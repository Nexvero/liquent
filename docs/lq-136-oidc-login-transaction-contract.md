# LQ-136 — OIDC Login Transaction Contract

## Status

Architekturentscheidung und Vertrag, providerneutral. Keine Implementierung, kein
Anbieter, keine Route, keine Bibliothek, keine Persistenz und keine Freigabe einer
Laufzeitumgebung. Baut auf LQ-129 (Identitätsgrenze), LQ-130 (Persistenzgrenze),
LQ-131 (`ExternalIdentityLookup`), LQ-132/133 (Admission und Binding-Port) und
LQ-135 (lokaler Adapter) auf.

## Ziel

Definiere den Sicherheits- und Lebenszyklusvertrag einer **kurzlebigen
OIDC-Login-Transaktion** für den Authorization Code Flow mit PKCE.

## Login-Start

- Liquent erzeugt **kryptografisch unabhängige** Werte für:
  - einen opaken `state`,
  - einen OIDC-`nonce`,
  - einen PKCE-`code_verifier`.
- PKCE verwendet **ausschließlich `S256`**; der `code_challenge` wird aus dem
  `code_verifier` abgeleitet.
- `state`, `nonce` und `code_verifier` dürfen **nicht** voneinander abgeleitet oder
  wiederverwendet werden.
- Der Browser erhält **nur** die für das OIDC-Protokoll erforderlichen Werte; der
  `code_verifier` bleibt **ausschließlich serverseitig**.
- Liquent speichert eine kurzlebige serverseitige Login-Transaktion.
- Der `state` dient **ausschließlich** als opaker Korrelations- und
  CSRF-Schutzwert.
- Eine **optionale `IdentityAdmissionId`** wird beim Login-Start **serverseitig an
  die Transaktion gebunden**; der Callback darf keine andere Admission einsetzen.
- Ein **optionales Rückkehrziel** muss ein bereits validierter interner
  **relativer** Pfad sein — **keine** absolute URL und **kein** offener Redirect.

## Serverseitiger Transaktionszustand (konzeptionell)

Der spätere Zustand muss konzeptionell **mindestens** enthalten (noch **keine**
konkreten Python-Modelle, Felder oder Persistenztechnologie):

- sicheren Lookup-Bezug für `state`,
- erwarteten `nonce`,
- retrievbaren PKCE-`code_verifier`,
- erwarteten Issuer bzw. dessen stabile Identität; die Transaktion friert
  **keinen** Trust-Status vom Login-Start dauerhaft ein,
- exakte Redirect-URI bzw. deren stabile interne Referenz,
- Erstellungs-/Ablaufzeit,
- Konsumzustand,
- optional gebundene `IdentityAdmissionId`,
- optional validiertes internes Rückkehrziel.

## Callback-Grenze

Vor Erzeugung einer Liquent-Session müssen **vollständig und erfolgreich** geprüft
werden:

- `state` vorhanden und passend,
- Transaktion vorhanden, nicht abgelaufen und nicht bereits konsumiert,
- **atomarer Einmal-Konsum** der Login-Transaktion,
- Authorization Code nur einmal verarbeitet,
- erwarteter Issuer ist auch beim Callback nach der **aktuell aktiven**
  Liquent-Trust-Konfiguration weiterhin vertrauenswürdig; eine seit dem
  Login-Start entzogene oder deaktivierte Freigabe endet neutral,
- Tokenaustausch erfolgt ausschließlich gegen den Token-Endpunkt der aktuell
  vertrauenswürdigen Issuer-Konfiguration,
- ID-Token wurde vom erwarteten, weiterhin vertrauenswürdigen Issuer ausgestellt,
- Signatur und erlaubter Algorithmus,
- exakter Issuer,
- erwartete Audience und gegebenenfalls `azp`,
- Token-Ablauf und zeitliche Claims,
- exakter `nonce`,
- PKCE-Verifikation durch Token-Austausch mit dem gespeicherten `code_verifier`,
- vollständig verifizierte `(issuer, subject)`-Identität.

## Konsum- und Fehlerregel (fail-closed)

- Eine Callback-Transaktion wird **vor** der externen Code-Einlösung **atomar
  beansprucht bzw. konsumiert**.
- Schlägt danach die Code-Einlösung oder Tokenprüfung fehl, **bleibt sie
  verbraucht**; es gibt **keinen** Rücksprung in einen wiederverwendbaren Zustand.
- Der Nutzer startet bei einem transienten oder fachlichen Fehler eine **neue**
  Login-Transaktion.
- Diese fail-closed Regel verhindert **parallele Wiederverwendung und Replay**.
- Unbekannt, abgelaufen, bereits konsumiert, falscher `state`, falscher `nonce` und
  sonstige Verifikationsfehler enden nach außen **neutral**.
- Fehler dürfen **nicht** offenlegen, ob Admission, `ExternalIdentity`, User oder
  Workspace bekannt sind.

## Daten- und Geheimnisgrenze

- **Keine** IdP-Tokens in URL, Cookies, Web Storage, Logs, Telemetrie oder
  Anwendungsdaten.
- Authorization Code, `state`, `nonce` und `code_verifier` werden **niemals**
  geloggt oder in Telemetrie aufgenommen.
- `state` und `nonce` erscheinen protokollbedingt im Authorization Request;
  Authorization Code und `state` erscheinen abhängig vom gewählten Response
  Mode im Callback-Transport. Diese notwendige Protokollübertragung erlaubt
  keine Aufnahme in Logs, Telemetrie, Fehlerseiten, Weiterleitungen oder
  Anwendungsdaten.
- Zugriffslogs und Fehlerbehandlung müssen sensible Authorization- und
  Callback-Parameter aussparen oder redigieren.
- Der `code_verifier` bleibt ausschließlich serverseitig und erscheint niemals
  im Browsertransport.
- Der `code_verifier` muss bis zum Callback retrievbar und geschützt serverseitig
  gespeichert werden.
- Persistente Hash-/Verschlüsselungsdetails bleiben LQ-130 bzw. einem späteren
  technischen Slice vorbehalten.
- Nach erfolgreichem oder fehlgeschlagenem Konsum sollen nicht mehr benötigte
  Geheimnisse nicht weiter verfügbar bleiben.

## Nach erfolgreicher Verifikation

Reihenfolge:

1. externe Identität vollständig verifizieren,
2. bestehende Bindung über `ExternalIdentityLookup` auflösen,
3. falls ungebunden: **ausschließlich** die serverseitig an die Transaktion
   gebundene Admission über `ExternalIdentityAdmissionStore` verwenden,
4. interne Autorisierung und Workspace-Zugriff **separat** prüfen,
5. **erst danach** eine eigene Liquent-Browser-Session erzeugen,
6. IdP-Tokens **niemals** als Liquent-Session verwenden.

Eine erfolgreiche OIDC-Anmeldung allein erzeugt **keine** Berechtigung.

## Assurance

- MFA und primäre Step-up-Verantwortung bleiben beim Identity Provider.
- Die Transaktion kann später erforderliche Assurance-Anforderungen referenzieren.
- Konkrete `acr`-/`amr`-Policies bleiben ein separater Slice.
- Fehlende erforderliche Assurance führt **neutral** zum Abbruch **vor**
  Session-Erzeugung.

## Bewusst nicht enthalten

- kein konkreter Identity Provider,
- keine Python-Modelle oder Ports,
- kein Generator,
- kein Store oder Adapter,
- keine Login-Start- oder Callback-Route,
- keine OIDC-/OAuth-Bibliothek,
- keine Tokenverarbeitung,
- keine Discovery-/JWKS-Implementierung,
- kein Schema und keine Migration,
- keine Session-Erzeugungsverdrahtung,
- keine CORS-, Deployment- oder Shared-Environment-Änderung,
- kein föderierter Logout,
- kein Multi-Issuer-/Enterprise-SSO,
- kein Overcoding.

## Nächster Schritt

Ein späterer Slice kann — nach der LQ-130-Persistenzentscheidung — den
konzeptionellen Transaktionszustand als kleines, isoliert getestetes Modell und
danach einen atomaren, einmalig konsumierbaren Login-Transaktions-Store definieren.
