# LQ-146 — Trusted OIDC Client Configuration

## Ergebnis

Ein kleines, unveränderliches Wertobjekt für eine **bereits vertrauenswürdig
ausgewählte** OIDC-Issuer-/Client-Konfiguration. Es setzt die Validierungsregeln
aus LQ-145 (Abschnitte 3, 5 und 9) in ein Modell um.

**Keine** Discovery, **kein** Trust-Registry-Port, **kein** Netzwerk, **kein**
Authorization-URL-Builder, **keine** Route.

## Signatur

`src/liquent_platform/identity/oidc_client_configuration.py`

```python
@dataclass(frozen=True, slots=True)
class TrustedOidcClientConfiguration:
    issuer: str
    authorization_endpoint: str
    client_id: str
    redirect_uri: str
    scopes: tuple[str, ...]
```

Exakt fünf Felder, keine optionalen. Unveränderlich und hashbar. Kein Export
über `identity/__init__.py` — diese Datei enthält projektweit nur einen
Docstring und exportiert nichts.

## Trust-Semantik

Der Docstring hält ausdrücklich fest:

- Das Objekt wird **ausschließlich** aus vertrauenswürdiger serverseitiger
  Konfiguration erzeugt.
- Es trifft **keine** aktive Trust-Entscheidung.
- Es enthält **keinen** eingefrorenen Aktivierungsstatus und **kein**
  `enabled`-, `trusted`- oder ähnliches Bool-Feld.
- Der Issuer muss beim Login-Start durch eine **spätere** Trust-Grenze aktuell
  ausgewählt werden.
- Beim Callback wird der aktuelle Issuer-Trust gemäß LQ-136 **erneut** geprüft.
- Ein gespeichertes Objekt darf eine später **entzogene** Freigabe **nicht**
  umgehen.
- **Kein** Browserwert darf dieses Objekt erzeugen oder ein Feld überschreiben.

Der bloße Besitz des Objekts ist also **kein** Beweis, dass der Issuer weiterhin
aktiviert ist.

## URL-Invarianten

Geprüft wird mit `urllib.parse.urlsplit` — das ist bereits die Projektkonvention
(`observability/external_health.py`). **Keine** OIDC-/OAuth- oder externe
URL-Bibliothek.

| Feld | HTTPS | Host | Userinfo | Query | Fragment | Pfad/Port |
|---|---|---|---|---|---|---|
| `issuer` | zwingend | zwingend | verboten | **verboten** | verboten | erlaubt |
| `authorization_endpoint` | zwingend | zwingend | verboten | **verboten** | verboten | erlaubt |
| `redirect_uri` | zwingend | zwingend | verboten | **erlaubt** | verboten | erlaubt |

Begründungen:

- Issuer und Authorization Endpoint dürfen **keine** Query tragen: Ein
  konfigurierter Endpoint mit Query wird gemäß LQ-145 **abgewiesen** statt
  zusammengeführt. Das schließt Kollision mit den verpflichtenden Parametern
  **per Konstruktion** aus.
- Die Redirect-URI **darf** eine fest konfigurierte Query tragen, weil
  OIDC-Redirect-URIs registrierte, exakt zu vergleichende Werte sind. Die Query
  bleibt unverändert Teil der URI.
- Userinfo wird gegen `None` geprüft, nicht gegen Truthiness, damit auch
  `https://@host/` abgewiesen wird.

**Validierung und Speicherung sind getrennt:** Der Helfer prüft und gibt
**nichts** zurück; das Modell speichert den Originalstring. Es gibt **kein**
Trimmen, **kein** Lowercasing, **kein** Entfernen eines abschließenden Slashs
und **keine** URL-Kanonisierung. Zwei unterschiedlich geschriebene Issuer
bleiben **zwei verschiedene** Konfigurationen — die aufrufende Trust-Grenze muss
bereits den kanonischen Wert liefern.

**Keine** Same-Origin-Regel zwischen Issuer und Authorization Endpoint. Deren
vertrauenswürdige Zuordnung stammt später aus kontrollierter Konfiguration oder
verifizierter Discovery, nicht aus einem Stringvergleich in diesem Modell. Der
Issuer wird **nicht** aus dem Endpoint abgeleitet, und die Redirect-URI **nicht**
aus Issuer, Endpoint, `Host`, `Forwarded`, `X-Forwarded-Host` oder
Browserparametern.

Die `client_id` muss lediglich nicht leer sein und bleibt exakt erhalten —
**keine** Format-, E-Mail-, UUID- oder URL-Annahme. Sie ist **kein** Secret.

Lokale HTTP-Ausnahmen sind **nicht** Teil dieses Slices.

## Scope-Invarianten

Reihenfolge der Prüfung: Tupel-Typ → nicht leer → je Eintrag (String, nicht
leer, kein Whitespace, nicht doppelt) → `openid` enthalten.

- mindestens ein Scope,
- jeder Scope nicht leer,
- `openid` exakt enthalten,
- jeder Scope eindeutig,
- **Reihenfolge exakt erhalten**,
- **keine** Sortierung, **keine** Deduplizierung, **keine** Ergänzung,
- **kein** automatisches `email`, `profile` oder `offline_access`.

Ein einzelner Scope darf **kein** Whitespace enthalten, weil Scopes später als
durch Leerzeichen getrennte Scope-Tokens serialisiert werden. Geprüft wird über
`str.isspace()` je Zeichen, was Leerzeichen, Tab und Zeilenumbruch abdeckt. Ein
ungültiger Eintrag wird **abgewiesen**, nicht normalisiert.

Abgewiesen werden mindestens: leeres Tupel, fehlendes `openid`, leerer Scope,
doppelter Scope, Scope mit Leerzeichen/Tab/Zeilenumbruch, Liste statt Tupel und
Nicht-String-Einträge.

## Ausgeschlossene Daten

Das Modell enthält **kein** Client-Secret, keine Tokens, Claims, Subjects,
User-IDs, Admission-IDs, Workspaces, Rollen, Berechtigungen, Session-Daten,
`state`, `nonce`, `code_verifier`, `code_challenge`, `return_path`, keine
Discovery-/JWKS-Daten, keinen Aktivierungs- oder Trust-Status und keinen
Providernamen oder Branding.

## Keine Laufzeitlogik

**Keine** Netzwerkaufrufe, **keine** DNS-Auflösung, **keine** Discovery,
**keine** URL-Neuschreibung, **keine** Rückgabe einer normalisierten URL. Das
Modul importiert ausschließlich `dataclasses.dataclass` und
`urllib.parse.urlsplit`.

Fehlermeldungen sind neutral: Sie nennen den **Feldnamen**, geben aber
**niemals** den Konfigurationswert wieder, damit eine abgelehnte Konfiguration
nicht über eine Fehlermeldung nach außen dringt.

## Was ausdrücklich nicht validiert wird

- kein Portwert-Check,
- keine Erreichbarkeits- oder DNS-Prüfung,
- kein `client_id`-Format,
- keine Aussage, ob der Issuer aktuell aktiviert ist,
- keine Beziehung zwischen Issuer und Authorization Endpoint,
- keine Registrierungsprüfung der Redirect-URI beim Provider,
- keine Aussage über die Scope-Semantik beim Provider.

## Tests

`tests/test_oidc_client_configuration.py` — 57 fokussierte Tests.

**Erfolg:** gültige Konfiguration · Unveränderlichkeit · Hashbarkeit · exakt
fünf Felder in festgelegter Reihenfolge · alle Werte verbatim · Issuerpfad und
abschließender Slash erhalten · Endpoint mit Pfad und Port akzeptiert ·
Redirect-URI mit konfigurierter Query exakt erhalten · Scope-Reihenfolge
erhalten.

**Issuer / Authorization Endpoint:** je sieben Ablehnungen (leer, HTTP, relativ,
ohne Host, Userinfo, Query, Fragment).

**Client-ID:** leer abgewiesen · Wert mit führenden/abschließenden Leerzeichen
und Sonderzeichen bleibt exakt.

**Redirect-URI:** sechs Ablehnungen (leer, HTTP, relativ, ohne Host, Userinfo,
Fragment) · eine Redirect-URI auf fremdem Host bleibt exakt und wird **nicht**
aus Issuer oder Endpoint abgeleitet.

**Scopes:** neun Ablehnungen · Standard-Scopes nur bei ausdrücklicher
Konfiguration · `offline_access` wird nie automatisch ergänzt.

**Strukturgrenzen:** parametrisiert kein `client_secret`, `secret`, `enabled`,
`trusted`, `is_active`, `state`, `nonce`, `code_verifier`, `code_challenge`,
`admission_id`, `return_path`, `session_id`, `user_id`, `workspace_id` · die
öffentliche Modulfläche ist exakt `TrustedOidcClientConfiguration` (plus die
beiden Importe), womit kein Port, Adapter, Store, Netzwerkaufruf oder
URL-Builder ergänzt wurde.

Geprüft wird ausschließlich der LQ-146-Vertrag; es gibt **keine** globalen
Import-, AST- oder Substring-Verbote über bestehende Module.

## Bewusst nicht enthalten

- kein Trust-Registry-Port, kein Konfigurations-Store, kein Adapter,
- kein aktiver/deaktivierter Status, keine Multi-Issuer-Auswahl, kein
  Enterprise-SSO,
- keine Discovery, kein JWKS, kein Netzwerk, keine DNS-Prüfung,
- keine OIDC-/OAuth-Bibliothek, kein Authorization-URL-Builder,
- keine Route, keine HTTP-Weiterleitung, kein Callback,
- keine Token-Verarbeitung, kein Client-Secret,
- keine Admission- oder Autorisierungslogik, keine Session-Erzeugung,
- keine Persistenz oder Migration, kein Production-Wiring,
- kein Deployment oder VPS-Zugriff, keine Proxy-/CORS-Konfiguration,
- keine CI-/Grype-Änderung, keine Änderung der CPython-Ausnahmen,
- keine Änderung an bestehenden Ports, Modellen, Adaptern oder
  Anwendungsfällen.

## Nächster Schritt

Ein späterer Slice kann die **Trust-Grenze** definieren, die genau eine solche
Konfiguration aus dem aktuell aktiven serverseitigen Zustand auswählt — und erst
danach folgen ein Authorization-Request-Builder und die Login-Start-Route mit
der in LQ-145 verschobenen Entscheidung über Pfad, Methode und Status.
