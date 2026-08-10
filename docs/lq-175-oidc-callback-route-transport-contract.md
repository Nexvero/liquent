# LQ-175 — Transportvertrag der OIDC-Callback-Route

## 1. Status, Ziel und Systemgrenze

Architekturentscheidung und HTTP-Vertrag, **nur Vertrag**. Keine Route, kein
Querymodell, kein Parser, kein Wiring, kein Test. LQ-175 ist der **endgültige**
Transportvertrag für `GET /v1/session/oidc/callback` und verbindet die inzwischen
vollständig vorhandenen Grenzen: HTTP-Query und Browserbindung →
`verify_oidc_callback` (LQ-163) → `complete_oidc_login` (LQ-173) →
`resolve_internal_destination` (LQ-174) → Session-/CSRF-Ausgabe (LQ-114/115/119)
→ `303` auf ein validiertes internes Ziel.

**LQ-158 bleibt unverändert und vollständig maßgeblich**; es wird hier nicht
wiederholt, sondern per Verweis in Kraft gesetzt. LQ-175 entscheidet nur, was
LQ-158 §14 offenließ: Fehlerziele, Response- und Cookie-Ausgabe, Rohgrenzen der
Query und die Zuordnung jedes Ausgangs zu genau einer Ergebnisklasse.

## 2. Route und Methoden

Exakt `GET /v1/session/oidc/callback`, **kein** Provider und **kein** Issuer im
Pfad. Alle anderen Methoden werden **route-lokal** beantwortet: leerer
`405 Method Not Allowed` mit `Allow: GET`, ohne Abhängigkeit, ohne
Cookie-Veränderung, ohne `Location` — ausdrücklich auch `HEAD`, `OPTIONS`,
`TRACE` und `CONNECT`, denn das sind gewöhnliche Methoden, die ein Client an
diesem Pfad senden kann. **Keine** globale Verhaltensänderung anderer Routen und
kein globaler Exception-Handler, damit kein Framework-Default einen JSON-Body
erzeugt.

## 3. Verbindliche Callback-Reihenfolge

1. Methode prüfen.
2. **Rohgrenzen** der Query prüfen (§4), auf unveränderten Bytes vor jeder
   Dekodierung.
3. Query über die **echte Multimap** lesen, zunächst **ausschließlich** zur
   Bestimmung von exakt einem nicht leeren `state`.
4. `__Host-liquent_oidc_state` lesen.
5. State und Cookie **konstantzeitlich** vergleichen.
6. Fehlendes Cookie oder Mismatch: **kein** Claim, **keine** Verifikation,
   **keine** Completion, Cookie **nicht** löschen.
7. Erst nach erfolgreichem Match `verify_oidc_callback(...)` **genau einmal** —
   damit genau ein Claim und höchstens eine Code-Verifikation.
8. Nach dem Match auf **jedem** weiteren Endpfad das State-Cookie löschen.
9. Nur bei `VerifiedOidcCallback`: `complete_oidc_login(...)` **genau einmal**.
10. Nur bei `CompletedOidcLogin`:
    `resolve_internal_destination(completed.return_path)` **genau einmal**.
11. Nur bei validierter Destination: Erfolgstransport mit neuer Session und CSRF.

Keine Stufe darf umgeordnet, zusammengezogen oder durch einen Transportwert
ersetzt werden. **Kein** Retry, **kein** Rollback, **keine** zweite Ausführung
einer Stufe.

## 4. Query-Vertrag und Rohgrenzen

LQ-158 §§4–6 bleibt vollständig maßgeblich: Erfolgsform exakt `state` + `code`;
Providerfehlerform exakt `state` + `error`, optional je **einmal**
`error_description` und `error_uri`; keine unbekannten Parameter; keine
Duplikate; leere Werte sichtbar erfassen; **kein** skalarer Zugriff, der
Duplikate verliert; die **abschließende** Queryprüfung erst nach Match und
Claim; Providertexte **niemals** anzeigen, loggen oder weiterreichen; eine
malformed Query nach dem Match verbraucht die Transaktion fail-closed.

LQ-158 legt **keine** Größenobergrenze fest — sein einziger DoS-Abschnitt (§6)
behandelt das fail-closed-Verbrauchen **einer** Transaktion, nicht die
Requestgröße. LQ-175 schließt die Lücke endgültig:

```
maximale rohe Querylänge:  8192 Bytes
maximale Parameteranzahl:      4
maximale rohe Komponente:  4096 Bytes
```

Geprüft direkt auf dem unveränderten ASGI-`query_string` **als Bytes**, vor
Dekodierung, State-Ermittlung, Cookie-Lesen und -Vergleich, Claim und jeder
anderen Abhängigkeit. Gesamtlänge `<= 8192` und Anzahl `<= 4` sind zulässig; jede
durch **rohe** `&`-Trennung entstehende Komponente muss `<= 4096` Bytes sein.
Leere Komponenten bleiben **sichtbar** und werden erst später durch den
Queryvertrag abgelehnt. **Keine** Prozentdekodierung vor diesen Grenzen.
Überschreitung ist **neutrale fachliche Ablehnung vor dem Match**: Cookie nicht
löschen, Transaktion nicht claimen, keine Session- oder CSRF-Ausgabe.

Warum diese Zahlen: 8 KiB begrenzt den Request-Target-Verbrauch **unabhängig von
Proxy-Defaults**; 4 KiB je Komponente lässt großzügigen Raum für opake
Authorization Codes, ohne einen einzelnen Wert unbeschränkt zu lassen; vier
Parameter sind **exakt** die größte zulässige Providerfehlerform. Ein späterer
Provider, der das nicht erfüllt, braucht eine **ausdrückliche Vertragsänderung**
und rechtfertigt keine unbeschränkte Eingabe.

## 5. Ergebnis- und Response-Matrix

Jeder behandelte GET-Ausgang ist ein **leerer `303 See Other`** mit den
Datenschutzheadern aus §7.

| Ausgang | Klasse | Status | `Location` | State-Cookie | Session/CSRF |
|---|---|---|---|---|---|
| Methode ≠ `GET` | 405 | **405** + `Allow: GET` | — | unberührt | nein |
| Rohgrenze überschritten | fachlich, **vor** Match | 303 | Ablehnungsziel | **unberührt** | nein |
| `state` fehlt · leer · doppelt | fachlich, vor Match | 303 | Ablehnungsziel | unberührt | nein |
| Binding-Cookie fehlt | fachlich, vor Match | 303 | Ablehnungsziel | unberührt | nein |
| State-/Cookie-Mismatch | fachlich, vor Match | 303 | Ablehnungsziel | unberührt | nein |
| Queryform nach Match ungültig | fachlich, **nach** Match | 303 | Ablehnungsziel | **gelöscht** | nein |
| Providerfehlerform | fachlich, nach Match | 303 | Ablehnungsziel | gelöscht | nein |
| `verify_oidc_callback → None` | fachlich, nach Match | 303 | Ablehnungsziel | gelöscht | nein |
| `complete_oidc_login → None` | fachlich, nach Match | 303 | Ablehnungsziel | gelöscht | nein |
| `resolve_internal_destination → None` | fachlich, nach Match | 303 | Ablehnungsziel | gelöscht | nein |
| `OidcVerificationUnavailable` | technisch, nach Match | 303 | Unavailable-Ziel | gelöscht | nein |
| `OidcLoginCompletionUnavailable` | technisch, nach Match | 303 | Unavailable-Ziel | gelöscht | nein |
| Fehler **nach** gespeicherter Session | technisch, nach Match | 303 | Unavailable-Ziel | gelöscht | nein |
| unerwartete normale `Exception` **vor** Match | technisch, vor Match | 303 | Unavailable-Ziel | **unberührt** | nein |
| unerwartete normale `Exception` **nach** Match | technisch, nach Match | 303 | Unavailable-Ziel | **gelöscht** | nein |
| **vollständiger Erfolg** | Erfolg | 303 | `destination.value` | gelöscht | **ja** |
| `BaseException` | — | **kein in LQ-175 definiertes HTTP-Ergebnis** | — | — | — |

Die Cookie-Spalte folgt **dem erreichten Sicherheitszustand, nicht der
Ergebnisklasse**: Vor-Match-Ausgänge lassen das State-Cookie unberührt und
claimen nicht — auch technische und unerwartete normale Exceptions beim
Bearbeiten der Rohquery, beim Lesen des Cookies oder beim Vergleich. **Jeder**
Nach-Match-Ausgang löscht es. **Ausschließlich** der vollständige Erfolg gibt
Session-Cookie und CSRF-Header aus.
**`verify_oidc_callback(...) -> None` bleibt ungeteilt** —
die Route rekonstruiert **nicht**, ob Claim, Providerform oder Verifikation
abgelehnt hat, weil LQ-163 diese Fälle bewusst zusammengeführt hat.

## 6. Fehlerziele

LQ-175 entscheidet endgültig: **zwei getrennte semantische Zielabhängigkeiten** —
ein **fachliches Ablehnungsziel** und ein **technisches Unavailable-Ziel**, beide
als bereits im **App-Wiring konstruierte `ValidatedInternalDestination`-Objekte**.
Verbindlich: **kein** roher String im Handler; **keine** Konstruktion aus
Request-, Host-, Origin- oder Forwarded-Werten; beide dürfen **absichtlich auf
denselben validierten Pfad zeigen** und tun es beim heutigen Stand; der Vertrag
erfindet **keine** konkreten Frontend-Pfade; spätere getrennte Pfade dürfen
**ausschließlich** die groben Klassen „fachlich abgelehnt" und „technisch nicht
verfügbar" unterscheiden — **keine** feinere Differenzierung nach State, Claim,
Binding, Admission, Identität, Providerfehler oder Infrastrukturkomponente. Weil
die Konstruktion im Wiring geschieht, scheitert eine Fehlkonfiguration **beim
Start**, nicht erst im Fehlerpfad.

Die beiden Klassen verlangen gegensätzliche Benutzerführung: „Anmeldung
fehlgeschlagen, bitte neu starten" ist ein sinnvoller Retry-Hinweis, während bei
technischer Nichtverfügbarkeit ein sofortiger Retry die Lage verschärft; ein
einziges festverdrahtetes Ziel nähme diese Unterscheidung dauerhaft weg.

Die Trennung ist unbedenklich, **weil alle fachlichen Ablehnungen in genau eine
Klasse kollabieren**: „State fehlt" ist von „Admission verweigert" und „Identität
nicht gebunden" nach außen ununterscheidbar; übrig bleibt nur „abgelehnt" gegen
„unsere Infrastruktur hat versagt". Das **Restwissen ist benannt und akzeptiert**:
Wer eine technische Störung gezielt auslöst, erfährt, dass er die Pipeline weiter
durchlaufen hat — relevant nur für einen Angreifer, der bereits `state`,
Binding-Cookie und gültigen Code kontrolliert, also für einen kompromittierten
Identity Provider, der ohnehin alles weiß. **Die technische Klasse beschreibt den
Zustand der Plattform, nicht die Existenz eines Nutzers oder Bindings.**

### Herkunft und Typ aller Zielwerte

Das Erfolgsziel entsteht **zur Laufzeit** aus
`resolve_internal_destination(completed.return_path)`, genau einmal; die beiden
Fehlerziele stammen unverändert aus dem Wiring. Alle drei sind ausschließlich
`ValidatedInternalDestination`; `Location` erhält
**exakt** `.value`. **Kein** `urljoin`, **keine** absolute URL, **keine** Query,
**kein** Fragment, **kein** Host-, Origin- oder Forwarded-Wert. Der Handler
schreibt **niemals** einen rohen Return-Path in `Location`. Liefert
`resolve_internal_destination(completed.return_path)` ein `None`:
**fachliche Ablehnung**, **kein** Fallback auf `/`, keine Session- oder
CSRF-Ausgabe, State-Cookie nach Match löschen, bereits gespeicherte Session
bleibt bestehen, **keine** zweite Completion, Ablehnungsziel als `Location`. Das
feste `/` entsteht **ausschließlich** aus einem ursprünglich fehlenden
`return_path` (LQ-174).

## 7. Einheitlicher HTTP-Datenschutz

Jeder behandelte GET-Ausgang trägt `Cache-Control: no-store`,
`Pragma: no-cache` und `Referrer-Policy: no-referrer`.

Zusätzlich: leerer Body; **kein** `Content-Type`, sofern der leere
Framework-Response keinen setzt; **keine** Queryreflexion; **kein** State, Code,
Providertext, Return-Path, Session- oder CSRF-Wert im Body; **keine** vollständige
Callback-URL und **kein** `Location` in Logs, Traces oder Telemetrie; **keine**
Querywerte oder Zielpfade in Metriklabels. Erlaubte Beobachtbarkeit ausschließlich:
normalisierter Routenname, Methode, grobe neutrale Ergebnisklasse und eine
Korrelations-ID **ohne** OIDC-Material.

Der Methoden-`405` muss mindestens `Cache-Control: no-store` tragen; die beiden
weiteren werden bewusst **vereinheitlicht**, sodass alle drei auf **allen**
Methoden dieser Route stehen — sonst hinge ein Referer-Leak davon ab, welche
Methode ein Client sendet.

## 8. Cookie- und Session-Ausgabereihenfolge

Die Regel ist **zustandsbasiert und kennt keine Ausnahme nach Fehlerklasse**.

**Vor** erfolgreichem Match wird das State-Cookie auf **keinem** Endpfad gelöscht
— auch nicht bei technischer Nichtverfügbarkeit oder einer unerwarteten normalen
Exception. In diesem Zustand ist noch nicht erwiesen, dass das Cookie zu *dieser*
Transaktion gehört; ein Schreiben auf diesen einzigen Slot könnte eine **neuere,
gültige** Bindung eines parallel gestarteten Logins beschädigen (LQ-152 §7,
LQ-158 §7, LQ-159). Ebenso wird kein Session-Cookie gesetzt oder gelöscht und
kein CSRF-Header ausgegeben.

**Erst nach** erfolgreichem Match gehört das Cookie nachweislich zu dieser
Transaktion. Ab dann gilt auf **jedem** danach behandelten Endpfad
`clear_oidc_state_cookie(response)` **genau einmal**, ohne erneutes Setzen des
Binding-Cookies und ohne Ausnahme für technische oder unerwartete Fehler.

**Vollständiger Erfolg**, verbindliche Reihenfolge:

1. lokalen, noch **nicht** zurückgegebenen leeren `303`-Response erzeugen,
2. `Location = destination.value`,
3. **zweiter** serverseitiger Clock-Read,
4. `set_issued_session(...)` **genau einmal**,
5. `clear_oidc_state_cookie(...)` **genau einmal**,
6. Datenschutzheader vollständig setzen,
7. Response zurückgeben.

Beide Cookie-Operationen müssen **anfügende** APIs verwenden; `headers["Set-
Cookie"] = ...` ist verboten, weil eine Zuweisung den anderen Slot überschriebe.
Der Erfolgsresponse enthält **gleichzeitig** ein neues `liquent_session`, die
Löschung von `__Host-liquent_oidc_state` und `X-CSRF-Token` exakt aus der
`IssuedBrowserSession`. **Keine** Session- oder CSRF-Werte im Body oder in
`Location`; **keine** bestehende Session wird übernommen, rotiert oder
widerrufen.

## 9. Die zwei Uhr-Lesegrenzen

Der spätere Handler verwendet **denselben** serverseitig injizierten
Clock-Callable an **zwei getrennten Vertrauensstellen**:
`complete_oidc_login(...)` liest ihn **intern genau einmal** und **nur nach**
belastbarem `UserId`; nach erfolgreicher Completion liest der Handler ihn
**genau einmal erneut** für die Cookie-Restlaufzeit der Session-Ausgabe.

Ein Vorablesen **vor** der Completion ist untersagt: Es würde LQ-173s Zusage
verletzen, dass eine fachliche Ablehnung **keine** Uhr berührt. Die
Cookie-Restlaufzeit muss zum **tatsächlichen Ausgabezeitpunkt** bestimmt werden;
der zweite Wert ändert die serverseitige Session-Gültigkeit **nicht**. Eine
werfende, falsch typisierte, naive oder bereits zu späte Zeit ist **technische
Nichtverfügbarkeit nach gespeicherter Session** — kein Rollback, keine zweite
Session-Issuance.

## 10. Teilfortschritt und kein Rollback

Nach Match und Claim ist die Login-Transaktion **verbraucht**. Ein
Admission-Binding kann bereits wirksam und eine Session bereits serverseitig
gespeichert sein, während die Destination-Auflösung oder die Response-Erzeugung
danach scheitert. Tritt dann eine normale Exception auf: den teilweise
aufgebauten Erfolgsresponse **verwerfen**, keine Session- oder CSRF-Ausgabe,
einen technischen `303` zum Unavailable-Ziel erzeugen, das State-Cookie nach
erfolgreichem Match **trotzdem** löschen, die gespeicherte Session **nicht**
zurückrollen und **keinen** zweiten Clock-, Generator-, Store- oder
Session-Issuance-Versuch unternehmen. **Kein rekursiver
Wiederholungsmechanismus.** Ein neuer Versuch beginnt ausschließlich mit einem
**neuen Login-Start** und löst die nun gebundene Identität regulär über den
Lookup-Pfad auf; Orphaned-Session-Cleanup und globale Revoke-Politik bleiben ein
eigener Slice.

## 11. Statuscodes

Alle behandelten GET-Ausgänge verwenden `303 See Other`, auch fachliche
Ablehnung und technische Nichtverfügbarkeit: Ein leerer `400` oder `500` ließe den
Browser **auf der Callback-URL stehen**, sodass `code` und `state` in Verlauf,
Referer und teilbaren Links blieben — genau das verbietet LQ-158 §13. Die interne
Unterscheidung trägt deshalb das **validierte Ziel**, nicht der Statuscode und
**kein** detaillierter Body. Andere Methoden bleiben `405` ohne `Location`.
**Keine Abweichung von LQ-158 §13.**

## 12. Bewusst verschoben und nächster Schritt

Python-Querymodell und Parser, FastAPI-Registrierung, Parameternamen und
Dependency-Injection, die konkreten UI-Pfade im Wiring, der
Korrelations-ID-Mechanismus, Frontend-Darstellung, Orphaned-Session-Cleanup,
globale Revoke-Politik, Persistenz und Production-Wiring. Als Nächstes folgt der
Implementierungsslice nach diesem Vertrag: Rohgrenzen, Multimap-Queryvertrag,
Browserbindung, die vier Aufrufe in fester Reihenfolge und die Response-Ausgabe.
