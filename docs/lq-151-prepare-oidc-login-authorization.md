# LQ-151 — Prepare OIDC Login Authorization

## Ergebnis

Ein kleiner, **transportfreier** Anwendungsfall, der die drei bestehenden
Login-Start-Bausteine verbindet: aktive Konfiguration lesen (LQ-148/LQ-150) →
Login-Transaktion starten (LQ-144) → Authorization Request bauen (LQ-147).

**Keine** Route, **keine** HTTP-Weiterleitung, **kein** neuer Port, **kein**
neuer Adapter, **kein** neues Rückgabemodell.

## Signatur

`src/liquent_platform/application/prepare_oidc_login_authorization.py`

```python
def prepare_oidc_login_authorization(
    configuration_lookup: ActiveOidcClientConfigurationLookup,
    transaction_store: OidcLoginTransactionCreationStore,
    generator: SecureOidcLoginMaterialGenerator,
    *,
    now: datetime,
    lifetime: timedelta,
    admission_id: IdentityAdmissionId | None = None,
    return_path: str | None = None,
) -> OidcAuthorizationRequest: ...
```

Name unverändert übernommen: Die Anwendungsschicht benennt konsequent
verb-first (`start_oidc_login`, `build_oidc_authorization_request`,
`create_session`, `issue_session`, `rotate_session`, `read_research_job`).

## Schutz vor caller-gesteuerter Providerwahl

Die Signatur akzeptiert **keinen** Issuer, Authorization Endpoint, Client-ID,
Redirect-URI, Scope, Provider, Tenant, Workspace, User, Host, Header, kein
Request- oder Response-Objekt. Diese Werte stammen **ausschließlich** aus
`ActiveOidcClientConfigurationLookup`. Damit kann eine spätere HTTP-Grenze schon
rein typseitig nicht steuern, zu welchem Provider ein Login geht.

## Exakte Aufrufreihenfolge

| # | Schritt | Häufigkeit |
|---|---|---|
| 1 | `configuration_lookup.get_active_configuration()` | **genau einmal** |
| 2 | `None` → `OidcLoginUnavailable` | vor jeder weiteren Abhängigkeit |
| 3 | `start_oidc_login(store, generator, expected_issuer=…, redirect_uri=…, now=…, lifetime=…, admission_id=…, return_path=…)` | genau einmal |
| 4 | `build_oidc_authorization_request(configuration, started)` | **erst nach** erfolgreicher Speicherung |

Belegt als Aufruffolge `["lookup", "generator", "store", "builder"]`.

`expected_issuer` und `redirect_uri` stammen **exakt** aus der gelesenen
Konfiguration; `now`, `lifetime`, `admission_id` und `return_path` werden
**exakt** weitergereicht. **Keine** Normalisierung, **kein** zweiter
Generatoraufruf, **kein** eigener Store-Aufruf neben dem Start-Anwendungsfall,
**kein** Retry.

## Snapshot-Konsistenz

Die Konfiguration wird **genau einmal** gelesen, und **dasselbe Objekt** speist
beide Seiten:

- `PendingOidcLoginTransaction.expected_issuer == configuration.issuer`
- `PendingOidcLoginTransaction.redirect_uri == configuration.redirect_uri`
- Authorization Endpoint, Client-ID, Redirect-URI und Scopes des Requests
  stammen aus genau diesem Objekt.

Damit ist ein Time-of-check-Mischen zweier Konfigurationen **innerhalb eines
Starts** ausgeschlossen. Ein Testdouble, das bei **jedem** Aufruf eine andere
Konfiguration liefern würde, wird nachweislich nur einmal aufgerufen, und
Pending-Record wie Request stammen beide aus der ersten Lesung. Zwei **getrennte**
Aufrufe dürfen jeweils einen neueren Snapshot lesen — die Trust-Grenze darf sich
zwischen zwei Logins ändern.

## Bewusste Reihenfolgen-Konsequenz

Die Zeitvalidierung bleibt bei `start_oidc_login` und wird **nicht** dupliziert.
Daraus folgt:

- Bei ungültigem `now` oder `lifetime` kann der **read-only** Konfigurations-
  Lookup bereits einmal stattgefunden haben.
- Generator und Store bleiben trotzdem **unberührt**, weil LQ-144 **vor** der
  Materialerzeugung validiert.

Diese Reihenfolge ist bewusst gewählt: Eine vorgezogene Zeitprüfung im neuen
Anwendungsfall wäre eine Duplizierung der LQ-144-Invariante, und der Lookup ist
nebenwirkungsfrei. Beides ist durch Tests belegt.

## Fehlergrenzen

| Situation | Verhalten |
|---|---|
| keine aktive Konfiguration | `OidcLoginUnavailable`, neutral und detailfrei; Generator, Store und Builder werden **nicht** berührt, kein Fallback, kein Retry |
| Creation-Konflikt | `OidcLoginStartConflict` **unverändert** propagiert; Builder wird nicht aufgerufen, kein zweiter Lookup-, Generator- oder Store-Aufruf |
| Lookup-Infrastrukturfehler | unverändert propagiert — **nicht** zu `None`, **nicht** zu `OidcLoginUnavailable`; keine weitere Abhängigkeit aufgerufen |
| Store- oder Generatorfehler | unverändert propagiert, nicht als Konfigurationsfehler umgedeutet, kein Retry, kein partieller Request |
| Builderfehler | unverändert propagiert |

Der neue Anwendungsfall erzeugt **keine** eigenen Fehlertexte mit Issuer,
Endpoint, Client-ID, Redirect-URI, State, Nonce, Code-Challenge, Admission-ID
oder Return-Path.

### Warum ein eigener Fehler

`OidcLoginUnavailable` steht neu in `application/oidc_login_errors.py` und folgt
dem dort etablierten Muster: konstantes neutrales `code`, argumentloser
`__init__`, keine internen Details.

`OidcLoginStartConflict` wird **nicht** wiederverwendet: „keine aktive
Konfiguration" und „State-Kollision" sind unterschiedliche Situationen, und eine
Zusammenlegung würde zwei unabhängige Ursachen für den Aufrufer ununterscheidbar
machen. Der Moduldocstring wurde minimal von „start conflicts" auf beide Fälle
geweitet.

Nach außen bleibt `OidcLoginUnavailable` neutral: Es sagt **nicht**, ob nie eine
Konfiguration existierte, ob sie deaktiviert wurde oder ob eine Freigabe
entzogen wurde.

## Geheimnisgrenze

Rückgabe ist ausschließlich `OidcAuthorizationRequest`. Der bestehende
`repr`-Schutz der vollständigen URL bleibt erhalten. **Nicht** zusätzlich
zurückgegeben werden Konfiguration, `StartedOidcLogin`, State oder Nonce als
eigene Felder, Code-Verifier, Admission-ID, Pending-Record oder User-,
Workspace- und Session-Daten.

Der `code_verifier` bleibt ausschließlich im serverseitigen Pending-Record;
Admission-ID und `return_path` sind serverseitig gebunden und erscheinen
**nicht** im Authorization Request.

## Trust-Semantik

Der Anwendungsfall liest die aktuell bereitgestellte Konfiguration genau einmal,
trifft **keine** eigene Issuer-Trust-Entscheidung, validiert die Konfiguration
**nicht** erneut, friert **keinen** Trust-Status ein, führt **keine** Discovery
aus, lädt **keine** Signaturschlüssel und prüft **keine** Tokens oder Claims.

Der Callback muss den aktuellen Issuer-Trust gemäß LQ-136 weiterhin **separat
erneut** prüfen. Ein zwischen Start und Callback deaktivierter Issuer führt beim
Callback **neutral** zum Abbruch.

## Tests

`tests/test_prepare_oidc_login_authorization.py` — 41 fokussierte Tests mit
einem gemeinsamen Aufruf-Recorder, sodass Reihenfolge **und** Nichtaufruf präzise
belegbar sind. Der Builder wird eng begrenzt per `monkeypatch` auf dem neuen
Modul beobachtet.

**Erfolgsablauf:** Rückgabe ist ein `OidcAuthorizationRequest` · Lookup,
Generator und Store je genau einmal · Aufruffolge exakt
`["lookup", "generator", "store", "builder"]` · der Builder erhält
`is`-identisch das vom Lookup gelieferte Objekt.

**Datenfluss:** Pending-Record trägt exakt Issuer und Redirect-URI der
Konfiguration · der Request trägt exakt Endpoint, Client-ID, Redirect-URI und
Scopes derselben Konfiguration · `now` und `lifetime` exakt weitergereicht ·
Admission-ID und `return_path` serverseitig gebunden, aber weder als Parameter
noch als Substring in der URL · Code-Verifier nur im Pending-Record · `repr` der
Rückgabe ohne URL, State und Nonce.

**Struktureller Schutz:** 16 Konfigurations- und Transportparameternamen
parametrisiert ausgeschlossen · die Signatur ist exakt die vereinbarte, mit
`now` und `lifetime` **ohne** Default (keine versteckte Uhr) · Rückgabeannotation
ist exakt `OidcAuthorizationRequest`.

**Leerfall:** `None` → `OidcLoginUnavailable` mit konstantem neutralem Code · der
Fehlertext enthält keinen der fünf Konfigurationswerte · Generator, Store und
Builder bleiben unberührt, die Aufruffolge ist nur `["lookup"]`.

**Fehlerpropagation:** Lookup-, Store-, Generator- und Builderfehler propagieren
unverändert · nach Lookup-Fehler wird nichts weiter aufgerufen · bei
Creation-Konflikt läuft der Builder nicht und es gibt keinen zweiten Lookup-,
Generator- oder Store-Aufruf.

**Zeitgrenze:** ungültige `lifetime` und naives `now` werden weiterhin von LQ-144
abgewiesen; dabei ist der Lookup genau einmal erfolgt, Generator und Store
bleiben unberührt, die Aufruffolge ist nur `["lookup"]`.

**Snapshot-Konsistenz:** ein rotierendes Lookup-Double wird pro Start nur einmal
aufgerufen und der gesamte Start nutzt die erste Lesung · zwei getrennte Aufrufe
lesen jeweils einen neuen Snapshot.

Geprüft wird ausschließlich der LQ-151-Vertrag: **keine** Modulflächenprüfungen,
**keine** globalen Importverbote, **keine** AST-Prüfungen über bestehende
Module, **keine** Substring-Suchen über ganze Module.

## Bewusst nicht enthalten

- keine Änderung an LQ-144, LQ-147, LQ-148 oder LQ-150,
- kein neues Rückgabemodell, kein neuer Port, kein neuer Adapter,
- keine dynamische Trust-Registry, keine Multi-Issuer-Auswahl, kein
  Providerparameter,
- keine Login-Start-Route, kein HTTP-Redirect, keine Entscheidung über Route,
  Methode oder Redirect-Status, keine HTTP-Request-/Response-Typen,
- keine Discovery, kein Signaturschlüssel-Loading, kein Netzwerk,
- keine OIDC-/OAuth-Bibliothek,
- kein Callback, keine Token- oder Claim-Verarbeitung,
- keine Admission-Erzeugung oder -Validierung, keine Workspace-Autorisierung,
- keine Session-Erzeugung, keine Persistenz oder Migration,
- kein Production-Wiring, kein Deployment oder VPS-Zugriff,
- keine Proxy-/CORS-Konfiguration,
- keine CI-/Grype-Änderung, keine Änderung der CPython-Ausnahmen.

## Nächster Schritt

Die serverseitige Login-Start-Kette ist damit vollständig und in einem Aufruf
komponierbar. Offen bleibt allein die **Route**, mit der in LQ-145 ausdrücklich
verschobenen Entscheidung über Pfad, Methode und Redirect-Status — sowie später
der Callback-Anwendungsfall, der die Transaktion über den Claim-Port genau
einmal einlöst.
