# LQ-155 — Provider-Neutral OIDC Callback Verification Boundary

## Status

Architekturentscheidung und **Sicherheitsvertrag**, providerneutral. **Keine**
Implementierung, **keine** Route, **kein** Python-Modell, **kein** Port, **kein**
Adapter, **keine** OIDC-Bibliothek, **keine** Discovery- oder JWKS-Implementierung
und **keine** Freigabe einer Laufzeitumgebung.

Baut auf LQ-129 (Identitätsgrenze), LQ-130 (Persistenzgrenze), LQ-131
(`ExternalIdentity` + read-only Lookup), LQ-132/LQ-133 (Admission und
Binding-Port), LQ-136 (Transaktionsvertrag), LQ-139 (atomarer Claim-Port),
LQ-146 (`TrustedOidcClientConfiguration`), LQ-148/LQ-150 (aktive Konfiguration),
LQ-152 (Login-Start-Transportvertrag und Browserbindung) und LQ-154
(implementierte Login-Start-Route) auf.

## 1. Ziel und Systemgrenze

Dieser Vertrag definiert die Grenze, die **nach** erfolgreicher Browserbindung
und **nach** dem atomaren Einmal-Claim:

1. den Authorization Code **genau einmal** einlöst,
2. sämtliche OIDC-/Tokenprüfungen **vollständig** durchführt,
3. **ausschließlich** eine vollständig verifizierte
   `ExternalIdentity(issuer, subject)` an Liquents innere Anwendungslogik
   zurückgibt.

Die Grenze ist **providerneutral**: sie kennt keinen Anbieternamen, keine
Produktbesonderheit und kein Branding. Ein konkreter Provider ist später
ausschließlich **Konfiguration**, niemals eine Fallunterscheidung im Vertrag.

## 2. Die drei Ebenen des Callbacks

Der spätere Callback-Ablauf besitzt drei klar getrennte Ebenen. Die Trennung ist
verbindlich, weil jede Ebene eine **andere** Vertrauensfrage beantwortet und
jede Vermischung eine der drei Antworten entwertet.

### Ebene 1 — HTTP- und Browserbindung

- Query-`state` **konstantzeitlich** gegen `__Host-liquent_oidc_state` prüfen.
- Fehlendes Cookie oder Mismatch: **neutral** abbrechen, **nichts** claimen,
  Cookie **nicht** löschen (LQ-152 §9).
- **Erst nach** erfolgreichem Match: Cookie auf **jedem** weiteren Endpfad
  löschen.

### Ebene 2 — Atomarer Transaktions-Claim

- `state` **genau einmal** über den bestehenden
  `OidcLoginTransactionClaimStore` beanspruchen.
- Unbekannt, abgelaufen oder bereits konsumiert: **neutral** abbrechen.
- Der Claim geschieht **vor** jeder externen Code-Einlösung.
- **Nach** dem Claim gibt es **niemals** Rollback oder Wiederfreigabe.

### Ebene 3 — Externe OIDC-Verifikation

- erhält **nur** den Authorization Code und das bereits geclaimte,
  serverseitige Transaktionsmaterial,
- führt aktuelle Trust-Prüfung, Code-Einlösung und ID-Token-Verifikation durch,
- liefert **nur** eine verifizierte externe Identität **oder** eine neutrale
  Ablehnung,
- **Tokens und Claims überschreiten diese Grenze nicht.**

**LQ-155 entscheidet ausschließlich Ebene 3 und ihre Schnittstelle zu Ebene 2.**
Die HTTP-Route, der Queryparser, der Cookie-Vergleich und das Cookie-Löschen
bleiben ein **späterer** Transport-Slice.

## 3. Eingabegrenze der Verifikationsebene

Die Verifikationsebene erhält **genau zwei** Dinge: den Authorization Code und
das Material der bereits geclaimten Transaktion. Aus dem geclaimten
`PendingOidcLoginTransaction` überschreiten **nur** diese Felder die Grenze:

| Feld | Zweck an der Grenze |
|---|---|
| `expected_issuer` | Trust-Neuprüfung und exakter `iss`-Vergleich |
| `expected_nonce` | exakter `nonce`-Vergleich im ID-Token |
| `code_verifier` | PKCE-Nachweis bei der Code-Einlösung |
| `redirect_uri` | exakter Wert für die Code-Einlösung |

**Ausdrücklich ausgeschlossen — und warum:**

- **`admission_id`.** Der Admission-Handle ist ein Capability-Wert, der eine
  einmalige Onboarding- oder Bindungsoperation autorisiert (LQ-132/LQ-140). Eine
  Grenze, die ausschließlich eine Identität **beweist**, darf ihn weder tragen
  noch konsumieren können. Er bleibt auf Ebene 2 und wird erst **nach**
  erfolgreicher Verifikation von der inneren Identitätsauflösung verwendet.
- **`return_path`.** Ein validiertes internes Rückkehrziel ist eine reine
  Transportentscheidung und für keine einzige Tokenprüfung relevant.
- **`state`.** Er ist der Korrelations- und Bindungswert der Ebenen 1 und 2 und
  hat in der Verifikation **keine** Rolle. Ihn dennoch weiterzureichen würde nur
  die Geheimnisfläche vergrößern.
- **Jeder Browserwert.** Kein Header, Cookie, Queryparameter, Hostname,
  `Forwarded`-Wert, Body oder Formfeld — außer dem Authorization Code selbst,
  der protokollbedingt aus der Callback-Query stammt.

`created_at`, `expires_at` und der Konsumzustand überschreiten die Grenze
ebenfalls nicht: Ablauf und Einmal-Konsum sind **abschließend** auf Ebene 2
entschieden (LQ-139). Eine zweite Ablaufprüfung an der Verifikationsgrenze wäre
eine zweite, schwächere Quelle für eine bereits atomar getroffene Entscheidung.

## 4. Aktuelle Issuer-Trust-Prüfung

**Verbindlich:**

- Der beim Start gespeicherte `expected_issuer` ist eine **Erwartung**, **kein**
  eingefrorener Trust-Status.
- Beim Callback muss dieser Issuer **erneut** gegen die **aktuell aktive**
  serverseitige Trust-Konfiguration geprüft werden.
- Ein inzwischen **deaktivierter, entfernter oder ersetzter** Issuer führt
  **neutral** zum Abbruch.
- Der Browser darf Issuer, Provider, Tenant, Token-Endpunkt, Client-ID,
  Redirect-URI, JWKS-Quelle oder Algorithmus **nicht** auswählen.
- **Keine** Trust-Entscheidung anhand von Tokenclaims allein.
- **Kein** Fallback auf einen anderen Issuer.
- Multi-Issuer und Enterprise-SSO bleiben **spätere** Erweiterungen.

### Der konkrete Mechanismus mit der heutigen Konfigurationsgrenze

`ActiveOidcClientConfigurationLookup` (LQ-148) liefert die **eine** aktuell
aktive Konfiguration und nimmt **kein** Argument. Daraus folgt der Mechanismus:

1. die aktive Konfiguration **genau einmal** lesen,
2. `None` → **neutral** abbrechen (kein Fallback, kein Retry),
3. ihren `issuer` **byteweise exakt** mit dem gespeicherten `expected_issuer`
   vergleichen; Ungleichheit → **neutral** abbrechen,
4. **erst danach** dieselbe Konfiguration für Client-Identität und
   Schlüsselquelle verwenden.

Weil der Port **keinen** Selektor entgegennimmt, ist „der Browser wählt keinen
Issuer" **strukturell** garantiert und keine Laufzeitprüfung. Ein
zwischenzeitlich ausgetauschter Issuer scheitert an Schritt 3 — genau das ist
die geforderte Neuprüfung.

**Keine Normalisierung beim Vergleich:** kein Trimmen, kein Kleinschreiben, kein
Entfernen oder Ergänzen eines abschließenden Slash. Zwei unterschiedlich
geschriebene Issuer bleiben zwei verschiedene Issuer (LQ-146).

## 5. Notwendige Konsequenz für die Konfigurationsgrenze

`TrustedOidcClientConfiguration` (LQ-146) trägt heute **ausschließlich**
`issuer`, `authorization_endpoint`, `client_id`, `redirect_uri` und `scopes`.

Für die Verifikation fehlen damit **vier** serverseitige Werte:

| Fehlender Wert | Wofür |
|---|---|
| **Token-Endpunkt** | Code-Einlösung beim aktuell vertrauenswürdigen Issuer |
| **Schlüsselquelle** (JWKS-Referenz oder statisches Schlüsselset) | Signaturprüfung |
| **erlaubte Signaturalgorithmen** | explizite Allow-List, siehe §8 |
| **zulässige Clock-Skew** | Zeitclaims, siehe §7 |

**Verbindlich entschieden:** Diese vier Werte gehören in die **serverseitige
Konfiguration** — niemals in die Login-Transaktion, niemals in einen Browserwert
und niemals in einen ungeprüften Tokeninhalt. Sie werden **nicht** aus dem
`issuer` abgeleitet und **nicht** per Laufzeit-Discovery bestimmt, solange kein
eigener Discovery-Vertrag existiert; eine ungesicherte Discovery wäre ein
zweiter, schwächerer Trust-Pfad neben der aktiven Konfiguration.

Daraus folgt eine **harte Reihenfolge**: Die Konfigurationsgrenze muss um diese
Werte erweitert werden, **bevor** ein Verifikationsport formuliert werden kann.
LQ-155 **entscheidet** diese Notwendigkeit hier abschließend und schiebt sie
nicht auf einen späteren Implementierer — analog zu LQ-152 §8, das
`PreparedOidcLoginAuthorization` als Vorbedingung der Login-Start-Route
festgelegt hat. Die konkrete Feldform bleibt ein **eigener** Slice.

## 6. Code-Einlösung

Der spätere Verifikationsadapter **muss**:

- den Authorization Code **genau einmal** an den Token-Endpunkt des **aktuell
  vertrauenswürdigen** erwarteten Issuers senden,
- **ausschließlich** die serverseitig konfigurierte Client-Identität verwenden,
- **exakt** die im Pending-Record gespeicherte Redirect-URI verwenden,
- **exakt** den gespeicherten `code_verifier` verwenden,
- **ausschließlich** Authorization Code Flow mit **PKCE S256** unterstützen,
- **keinen** Code aus Logs, Telemetrie, Fehlertexten oder Folge-URLs übernehmen,
- **keine** Wiederholung und **keine** automatische Retry-Schleife nach einem
  Einlösungsversuch durchführen.

**Ein transienter Netzwerkfehler nach atomarem Claim verbraucht die
Login-Transaktion.** Der Nutzer startet einen **neuen** Login. **Kein**
Rollback. Diese Härte ist beabsichtigt: jede Wiederverwendbarkeit nach einem
teilweise ausgeführten Austausch wäre ein Replay-Pfad, und ein Rollback wäre
selbst eine Wiederfreigabe.

### Warum Redirect-URI und Client-Identität aus verschiedenen Quellen stammen

Das ist bewusst **keine** Inkonsistenz:

- Die **Redirect-URI** muss dem Wert entsprechen, der tatsächlich im
  Authorization Request stand — das verlangt das Protokoll beim Token-Austausch.
  Maßgeblich ist deshalb der **im Pending-Record gespeicherte** Wert.
- Die **Client-Identität** ist eine **aktuelle serverseitige Tatsache** und wird
  deshalb aus der **jetzt aktiven** Konfiguration genommen.

Wurde die Konfiguration zwischen Start und Callback ausgetauscht, endet der
Login **neutral**: eine geänderte Redirect-URI lehnt der Identity Provider ab,
und eine geänderte Client-ID lässt die `aud`-Prüfung scheitern. Beides ist
fail-closed und korrekt — ein laufender Login überlebt eine Trust- oder
Client-Rotation nicht.

### Ausdrücklich offen gelassen

Das **Client-Authentifizierungsverfahren** (etwa Client Secret oder private-key
JWT) und der **konkrete Provider** bleiben spätere Konfigurations- bzw.
Adapterentscheidung. Verbindlich ist nur: **Browserwerte beeinflussen sie
nie**, und ein Client Secret erscheint niemals im Browsertransport.

## 7. Verpflichtende ID-Token-Prüfungen

Vor Ausgabe einer `ExternalIdentity` müssen **alle** folgenden Prüfungen
**vollständig erfolgreich** sein:

| Prüfung | Anforderung |
|---|---|
| Tokenformat | erwartungsgemäß |
| Signatur | gültig |
| Algorithmus | **explizit erlaubt**, niemals aus ungeprüften Headern frei akzeptiert |
| Schlüssel | stammt aus der **aktuell vertrauenswürdigen** Issuer-Konfiguration |
| `iss` | entspricht **exakt** dem gespeicherten `expected_issuer` |
| `aud` | enthält die erwartete serverseitige Client-ID |
| `azp` | bei **mehreren** Audiences nach OIDC-Regeln geprüft |
| `exp` | gültig |
| `nbf` | falls vorhanden, gültig |
| `iat` | plausibel und **nicht unzulässig in der Zukunft** |
| Clock-Skew | klein, **explizit serverseitig konfiguriert**, niemals aus dem Token übernommen |
| `nonce` | entspricht **exakt** dem gespeicherten erwarteten Nonce-Wert |
| `sub` | vorhanden, **nicht leer**, exakt und opak behandelt |
| Identitätsschlüssel | **keine** E-Mail, **kein** Anzeigename, **kein** anderer veränderlicher Claim |

### Keine Prüfung darf übersprungen werden

**Ein erfolgreicher Token-Endpunkt-Response ist kein Ersatz für irgendeine
dieser Prüfungen.** Das gilt ausdrücklich auch dort, wo OIDC Core es formal
erlauben würde: Für den Authorization Code Flow lässt der Standard es zu, die
Signaturprüfung zu unterlassen, wenn das Token direkt und TLS-gesichert vom
Token-Endpunkt stammt. **Liquent nutzt diese Erlaubnis nicht.** Ein HTTP 200
beweist nur, dass ein Endpunkt geantwortet hat — nicht, dass die Antwort vom
erwarteten Issuer stammt, für diese Client-Identität bestimmt ist, zu **dieser**
Login-Transaktion gehört oder zeitlich gültig ist. Genau das sollen die
Prüfungen feststellen.

Ebenso ersetzt ein **UserInfo-Endpunkt** die ID-Token-Verifikation **nicht**.
Er ist in dieser Grenze nicht vorgesehen; eine spätere Nutzung wäre ein eigener
Vertrag und müsste ein `sub` liefern, das dem verifizierten ID-Token-`sub`
exakt entspricht.

## 8. Schlüsselauswahl und Algorithmen

Die Signaturprüfung ist der Punkt, an dem ein Angreifer die Trust-Kette am
billigsten bricht. Deshalb verbindlich:

- Die **erlaubten Algorithmen** stehen als **serverseitige Allow-List** fest.
  Der `alg`-Wert im JOSE-Header darf **auswählen**, welcher der erlaubten
  Algorithmen gilt — er darf **niemals** einen Algorithmus **einführen**.
- Ein Token, dessen `alg` nicht in der Allow-List steht, wird **abgelehnt,
  bevor** irgendeine Signaturberechnung stattfindet.
- **`alg: none` ist verboten.**
- Ein Wechsel zwischen asymmetrischer und symmetrischer Signatur darf **nicht**
  durch den Tokenheader ausgelöst werden.
- **`jku`, `x5u` und `jwk` im Header werden niemals befolgt.** Sie sind vom
  Angreifer wählbare Verweise auf Schlüsselmaterial; ihnen zu folgen hieße, den
  Prüfschlüssel vom Prüfling bestimmen zu lassen.
- **`kid` darf ausschließlich innerhalb** des Schlüsselsets der aktuell
  vertrauenswürdigen Issuer-Konfiguration auswählen. Ein unbekannter `kid` führt
  **neutral** zum Abbruch und **niemals** zu einem Nachladen aus einer im Token
  genannten Quelle.
- Schlüsselrotation ist eine **Konfigurations- und Adapterfrage**, keine
  Tokenfrage.

## 9. Verifiziertes Ergebnis

Nach vollständiger Verifikation darf die Grenze **ausschließlich** liefern:

```
ExternalIdentity(
    issuer=<exakt verifizierter issuer>,
    subject=<exakt verifiziertes sub>
)
```

**Entscheidungen:**

- Werte **exakt und opak**, **keine** Normalisierung — konsistent mit dem
  bestehenden `ExternalIdentity`-Modell (LQ-131), das beide Werte verbatim hält
  und nur bei byteweiser Gleichheit gleich ist.
- **Keine** E-Mail, **kein** Name, **keine** Gruppen, Rollen oder
  Workspace-Daten.
- **Keine** ID-, Access- oder Refresh-Tokens.
- **Keine** Rohclaims.
- **Keine** Admission-ID.
- **Keine** Sessiondaten.
- **Keine** Berechtigung.
- Erfolgreiche Verifikation erzeugt **weder User noch Binding noch
  Mitgliedschaft**.

Der ausgegebene `issuer` ist derselbe Wert, gegen den `iss` exakt geprüft wurde
— also der kanonische Wert der aktiven Trust-Konfiguration. Er wird **nicht**
aus dem Token übernommen und **nicht** neu abgeleitet.

**Identitätsauflösung und Admission-Binding erfolgen erst danach** über die
bestehenden internen Grenzen: `ExternalIdentityLookup` (LQ-131) und, nur bei
ungebundener Identität, `ExternalIdentityAdmissionStore` (LQ-133) mit der
**serverseitig an die Transaktion gebundenen** Admission. Eine Liquent-Session
entsteht **erst danach** und **niemals** in dieser Grenze.

## 10. Assurance

MFA und Step-up bleiben Verantwortung des Identity Providers. LQ-155 hält fest:

- Eine spätere **Policy darf verifizierte `acr`-/`amr`-Informationen
  verlangen**.
- **Ohne explizite Liquent-Policy entsteht aus `acr` oder `amr` keine Rolle und
  keine Berechtigung.** Ein Assurance-Claim ist eine Aussage über die
  Authentifizierung, niemals über die Autorisierung.
- Die konkrete **Assurance-Repräsentation und Policy bleiben ein eigener
  Slice**.
- Für die **erste** Verifikationsgrenze ist `ExternalIdentity` das **einzige**
  fachliche Ergebnis.

## 11. Provider-Fehler im Callback

Der spätere HTTP-Callback muss auch einen OIDC-/OAuth-**Fehlerpfad**
berücksichtigen:

- Providerfehler mit **passendem State** durchlaufen **zuerst** dieselbe
  Browserbindung und denselben atomaren Claim.
- **Danach wird keine Code-Einlösung versucht.**
- Die Transaktion **bleibt verbraucht**.
- `error`, `error_description`, `error_uri` und sonstige Providertexte werden
  **nicht ungefiltert** angezeigt, geloggt oder telemetriert.
- **Fehlender oder falscher State bleibt ein Browserbindungsfehler** und darf
  **nicht** durch Providerfehlerparameter umgangen werden.
- **Gemischte Erfolg-/Fehlerantworten**, etwa gleichzeitig `code` und `error`,
  werden **neutral abgelehnt**.

Ein Providerfehler ist damit kein Sonderweg an der Bindung und am Claim vorbei:
Sonst wäre ein angehängter `error`-Parameter ein billiger Weg, die
Browserbindung zu umgehen oder eine Transaktion unverbraucht zu lassen.

Die genaue Query-Form, HTTP-Antwort und Benutzerweiterleitung bleiben dem
**späteren Callback-Transportvertrag** vorbehalten.

## 12. Fehlerklassen

Der Vertrag unterscheidet **konzeptionell zwei** Klassen. Beide bleiben
**intern getrennt**, und **keine** von beiden legt interne Details nach außen
offen.

### Was „neutral" hier bedeutet

**Neutral heißt detail- und bestandsfrei — nicht zwingend derselbe HTTP-Status
für eine fachliche Ablehnung und eine technische Nichtverfügbarkeit.**

Eine Antwort ist neutral, wenn sie keine Auskunft darüber gibt, ob eine
Identität, ein Subject, ein Nutzer, eine Bindung, eine Admission, ein
Workspace, eine Login-Transaktion oder eine bestimmte Issuer-Konfiguration
existiert, und wenn sie keine technischen Interna, Providertexte oder
Konfigurationswerte durchreicht. Diese Eigenschaft ist verbindlich.

Ob beide Klassen darüber hinaus **denselben** oder **unterschiedliche** neutrale
HTTP-Statuscodes beziehungsweise Benutzerpfade erhalten, ist **ausdrücklich
keine** Entscheidung von LQ-155.

### 1. Neutrale Verifikationsablehnung

- untrusted oder deaktivierter Issuer,
- Token-Endpunkt lehnt den Code ab,
- ungültiges Token,
- Signatur-, Claim-, Nonce- oder Audiencefehler,
- fehlendes oder leeres Subject.

**Innerhalb dieser Klasse einheitlich:** Die aufgeführten Fälle sind nach außen
**nicht voneinander** unterscheidbar und verraten **keine**
Bestandsinformation. Sonst würde erkennbar, ob ein bestimmter Issuer aktiv ist,
ob ein Code akzeptiert wurde oder ob ein Subject existiert.

### 2. Infrastrukturfehler

- Netzwerk nicht verfügbar,
- Trust-/Konfigurationsspeicher nicht lesbar,
- JWKS-/Schlüsselmaterial technisch nicht verfügbar,
- interner Adapterfehler.

Darf **intern getrennt** behandelt werden — Diagnose, Alarmierung, Metriken —
aber **ohne** Tokens, Codes oder Claims in Fehlermeldungen.

Ein Infrastrukturfehler **darf später als generische temporäre
Nichtverfügbarkeit behandelt werden**, ohne technische Details offenzulegen.
Das ist kein Widerspruch zur Neutralität: „gerade technisch nicht verfügbar"
sagt nichts darüber aus, ob eine Identität, ein Nutzer oder eine Konfiguration
existiert.

### Gemeinsame Regeln

Verbindlich für **beide** Klassen:

- Beide bleiben **intern getrennt**.
- Beide lassen die bereits geclaimte Transaktion **verbraucht** zurück.
- **Keine** Klasse erlaubt einen Retry **derselben** Transaktion oder ein
  Store-Rollback. Der Nutzer startet einen **neuen** Login.
- **Keine** von beiden legt jemals Authorization Code, Tokens, Nonce, Verifier,
  State, Claims, Providertexte oder Trust-Konfigurationsdetails offen — weder
  in einer Exception noch in einer Antwort, einem Log, einer Telemetrie oder
  einem Metriklabel.

### Was LQ-155 hier bewusst nicht entscheidet

Die **Transportabbildung** der beiden Klassen gehört dem **späteren
Callback-Transportvertrag**: konkrete HTTP-Statuscodes, Benutzerweiterleitung,
Fehlerseite und die Frage, ob eine temporäre Nichtverfügbarkeit anders
beantwortet wird als eine fachliche Ablehnung.

LQ-155 **darf diese Transportentscheidung nicht vorwegnehmen**. Die
Verifikationsgrenze liefert eine verifizierte Identität oder eine Ablehnung der
jeweiligen Klasse; wie eine spätere Route daraus eine Antwort formt, ist dort zu
entscheiden — mit den hier festgelegten Detail- und Bestandsfreiheitsregeln als
verbindlicher Untergrenze.

Die spätere konkrete **Python-Rückgabe- und Fehlerform** wird ebenso in einem
**eigenen Port-Slice** entschieden.

## 13. Geheimnis- und Aufbewahrungsgrenze

**Verbindlich:** Authorization Code, `code_verifier`, ID-Token, Access-Token und
Refresh-Token erscheinen **niemals** in:

- der URL nach dem Callback,
- Cookies,
- Web Storage,
- Logs,
- Telemetrie,
- Traces,
- Metriklabels,
- Fehlertexten,
- Anwendungsdaten.

Weiter gilt:

- Tokenantworten werden **nur so lange im Speicher** gehalten, wie die
  Verifikation sie benötigt.
- Nach Abschluss werden **keine IdP-Tokens persistiert** (LQ-130).
- **Nicht benötigte Claims werden nicht in innere Modelle kopiert.** Was nie
  kopiert wurde, kann später nicht versehentlich gespeichert, geloggt oder
  ausgeliefert werden.
- Die **Liquent-Browser-Session bleibt vollständig getrennt** und verwendet
  eigene opake Sessionwerte. Ein IdP-Token ist **niemals** eine Liquent-Session.

Erlaubt bleiben ein normalisierter Operationsname, eine neutrale Fehlerklasse
und eine Korrelations-ID **ohne** OIDC-Material — konsistent mit LQ-152 §12.
**Keine** Metriklabels mit Issuer, Client-ID, `sub`, `kid` oder Providertext:
solche Labels hätten unbegrenzte Kardinalität und gäben zugleich
Bestandsinformationen preis.

## 14. Was diese Grenze ausdrücklich nicht tut

- **keine** Browserbindung und **kein** Cookie-Zugriff (Ebene 1),
- **kein** Claim und **keine** Ablauf- oder Konsumentscheidung (Ebene 2),
- **keine** Identitätsauflösung auf einen `UserId`,
- **keine** Admission-Prüfung, **kein** Admission-Konsum, **keine**
  Bindungsanlage,
- **keine** Workspace-Mitgliedschaft, Rolle oder Berechtigung,
- **keine** Liquent-Session, **keine** Rotation, **kein** Widerruf,
- **kein** föderierter Logout,
- **keine** Persistenz von Tokens oder Claims.

Ein erfolgreiches Ergebnis dieser Grenze bedeutet **ausschließlich**: *Diese
externe Identität wurde für genau diese Login-Transaktion vollständig
verifiziert.*

## 15. Bewusst nicht enthalten

- keine Callback-Route, kein Queryparser, kein Cookie-Vergleich, kein
  Cookie-Löschen,
- kein Python-Modell, kein neuer Port, kein Adapter,
- keine OIDC-/OAuth-Bibliothek, keine Discovery- oder JWKS-Implementierung,
- kein konkreter Provider, kein Client-Authentifizierungsverfahren,
- keine Token-Einlösung und keine Claimprüfung im Code,
- keine Identitätsauflösung, keine Admission-Verarbeitung, keine
  Session-Erzeugung,
- keine Persistenz, kein Schema, keine Migration,
- kein Production-Wiring, kein Deployment, kein VPS-Zugriff,
- keine CORS-, CI-, Container-, Dependency- oder Grype-Änderung,
- keine Änderung an LQ-146, LQ-148, LQ-151, LQ-153 oder der LQ-154-Route,
- kein Multi-Issuer, kein Enterprise-SSO, keine Assurance-Policy.

## 16. Nächster Schritt

Zwingende Reihenfolge:

1. **Konfigurationsgrenze erweitern** — Token-Endpunkt, Schlüsselquelle,
   erlaubte Algorithmen und zulässige Clock-Skew (§5). **Ohne** diesen Slice ist
   ein Verifikationsport nicht formulierbar.
2. **Verifikationsport definieren** — Eingabe nach §3, Ergebnis nach §9,
   Fehlerform nach §12.
3. **Callback-Transportvertrag** — Query-Form, Provider-Fehlerpfad (§11) und
   HTTP-Antworten für die Browserbindung aus LQ-152 §9.
4. **Callback-Route** — Ebene 1 und Ebene 2 nach LQ-152 §9 und LQ-139, danach
   Aufruf der Verifikationsgrenze.
5. **Identitätsauflösung und Admission-Binding** über LQ-131/LQ-133, **erst
   danach** Session-Erzeugung.

Jeder Punkt bleibt ein **eigener, klein geschnittener** Slice mit isolierten
Tests.
