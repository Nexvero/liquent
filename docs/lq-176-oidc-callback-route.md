# LQ-176 — OIDC-Callback-Route

## Zweck und Ort

Die Implementierung von `GET /v1/session/oidc/callback` nach dem gemergten
LQ-175-Vertrag. Sie lebt in `src/liquent_platform/transport/http/app.py` in
einem eigenen `if oidc_callback_enabled:`-Block hinter der Login-Start-Route —
kein Hilfsmodul, kein Router, keine Middleware, keine Transportabstraktion und
keine Änderung an bestehenden Routen oder an den OIDC-, Session-, Cookie-,
Destination-, Port-, Cache- und Verifier-Bausteinen.

## Injektion

Neun neue optionale Factory-Parameter bilden die Callback-Gruppe:
`oidc_callback_transactions`, `_verifier`, `_identities`, `_admissions`,
`_sessions`, `_material`, `oidc_session_lifetime`, `_rejection` und
`_unavailable`. Beide Fehlerziele sind **bereits konstruierte**
`ValidatedInternalDestination`-Objekte; die Route nimmt keinen rohen Zielstring
entgegen und leitet nichts aus Request-, Host-, Origin- oder Forwarded-Werten
ab. Eine Fehlkonfiguration scheitert damit beim App-Bau, nicht im Fehlerpfad.

Die Uhr ist **keine neue Abhängigkeit**: `oidc_login_clock` bedient beide
Routen, weil LQ-175 denselben Callable an beiden Vertrauensstellen verlangt.
Sie wird deshalb aus beiden Gruppenlisten herausgehalten und getrennt geprüft:

- Login-Start ist aktiv, wenn die Uhr **und** seine fünf eigenen Werte da sind.
- Der Callback ist aktiv, wenn die Uhr **und** seine neun eigenen Werte da sind.
- Eine teilbefüllte Gruppe ist ein `ValueError` — je Gruppe getrennt.
- Eine Uhr **allein** bleibt wie bisher ein Konfigurationsfehler.

**Es gibt keine Aktivierungskopplung.** Der Callback lässt sich ohne
Login-Start aufbauen und umgekehrt; nur die geteilte Uhr ist beiden gemeinsam.

`oidc_session_lifetime` wird beim App-Bau geprüft: zwingend `timedelta` und
`int(total_seconds()) >= 1`. Sub-Sekunden-Werte kürzen auf `Max-Age=0`, was ein
Browser als sofort abgelaufen behandelt — ein erfolgreicher Login gäbe dann ein
Cookie aus, das der Browser verwirft. Keine Normalisierung, kein Ersatzwert, und
die Meldung nennt nur den Parameter, nie dessen Wert.

## Rohquery-Gate

Erste Anweisung des GET-Pfads, auf `request.scope["query_string"]` als **Bytes**:
höchstens 8192 Bytes gesamt, höchstens vier durch **rohes** `&` getrennte
Komponenten, höchstens 4096 Bytes je Komponente. Leere Komponenten zählen und
bleiben sichtbar. Kein `.decode()`, kein Unquote, kein Zugriff auf
`request.query_params`, kein Cookie-Lesen und keine Abhängigkeit davor.

Die Handlersignatur ist `(request: Request)` und deklariert **keinen**
Queryparameter, sodass FastAPI keinen extrahiert oder validiert. Nachgemessen im
hier verwendeten Stack: `request.query_params` bleibt vor dem eigenen Zugriff
unberührt, und `scope["query_string"]` liefert die unveränderten Bytes.

Eine leere Query erhält **keinen** Sonderfall: `b"".split(b"&")` ergibt eine
Komponente, passiert das Gate und fällt regulär auf „kein `state`".

## Methodenbesitz

Alle neun Methoden gehören der Route. Das ist keine Stilfrage — nachgemessen:
Eine reine `@app.get`-Registrierung beantwortet `OPTIONS`, `POST` und `TRACE`
mit dem 31 Byte großen JSON-Body des Frameworks und verletzt damit den
Leerbody-Vertrag. Besitzt die Route alle Methoden, ist jede Nicht-GET-Antwort
ein leerer `405` mit `Allow: GET`, denselben drei Datenschutzheadern, ohne
`Location`, ohne Cookie-Veränderung und ohne jede Abhängigkeit.

## Ablauf und Match-Zustand

```
Methode → Rohgate → genau ein nicht leerer state → Binding-Cookie
        → konstantzeitlicher Vergleich          ← ab hier: Match
        → verify_oidc_callback → complete_oidc_login
        → resolve_internal_destination → Erfolgsresponse
        → zweiter Clock-Read → set_issued_session
        → clear_oidc_state_cookie → Rückgabe
```

Der Match-Zustand wird **strukturell** geführt, nicht rekonstruiert: `_matched_state`
liefert entweder einen `OidcLoginState` — dann hat der konstantzeitliche
Vergleich gehalten — oder `None`. Beide Ausgänge dieser Phase, auch der
`except`-Zweig, lassen das Binding-Cookie **unberührt**; ein Schreiben auf diesen
einzigen Slot könnte die neuere, gültige Bindung eines parallel gestarteten
Logins beschädigen (LQ-152 §7, LQ-158 §7).

Erst danach läuft die zweite Phase, und `clear_oidc_state_cookie` steht **hinter**
ihrem `try`/`except` — also auf **jedem** post-match-Ausgang, ohne Ausnahme für
technische Fehler. Der `state` wird nicht erneut gelesen und nicht erneut
verglichen.

## Query-Form und der eine Claim

Nach dem Match liest die Route die **echte Multimap** (`multi_items()`); ein
skalarer Zugriff würde ein Duplikat verbergen. Die Erfolgsform ist exakt ein
`state` und ein nicht leerer `code`. Jede andere Form — Providerfehler, unbekannter
Parameter, Duplikat, leerer Code — ergibt `None` als Authorization Code.

Diese beiden Fälle werden **absichtlich nicht** unterschieden: `verify_oidc_callback`
claimt in **beiden** zuerst und gibt dann `None` zurück. Damit verbraucht auch eine
malformed Antwort die Transaktion fail-closed (LQ-158 §6), und es gibt trotzdem
nur **einen** Claim auf jedem post-match-Pfad.

## Uhr, Erfolg und Teilfortschritt

`complete_oidc_login` bekommt den injizierten Callable und liest ihn intern
einmal nach belastbarem `UserId`. Der Handler liest ihn **danach genau einmal
erneut** für `set_issued_session`; ein Vorablesen würde LQ-173s Zusage brechen,
dass eine fachliche Ablehnung keine Uhr berührt. Eine werfende, naive oder für
die Cookie-Restlaufzeit unbrauchbare Zeit ist technische Nichtverfügbarkeit
**nach** gespeicherter Session.

Der Erfolgsresponse entsteht in `_handled_after_match` und bleibt lokal. Wirft
irgendetwas — auch nach `set_issued_session` —, verlässt der Kontrollfluss die
Funktion, das Objekt wird nie zurückgegeben, und der `except`-Zweig baut ein
**frisches** `Response`. Dieses hat `set_issued_session` nie gesehen, kann also
weder Session-Cookie noch `X-CSRF-Token` tragen. Kein Rollback der verbrauchten
Transaktion, des Admission-Bindings oder der gespeicherten Session, kein Retry,
keine zweite Issuance und kein rekursiver Wiederholungsmechanismus.

Beide Cookie-Operationen hängen an (`set_cookie`, `delete_cookie`); es gibt
keine Zuweisung an `headers["Set-Cookie"]`, und beide Slots überleben im selben
Erfolgsresponse.

## Fehler- und Geheimnisgrenze

`None` aus Verifikation, Completion oder Destination → Ablehnungsziel.
`OidcVerificationUnavailable`, `OidcLoginCompletionUnavailable` und jede andere
normale Exception nach dem Match → Unavailable-Ziel. Eine normale Exception
**vor** dem Match → Unavailable-Ziel mit unberührtem Cookie. `BaseException`
wird nicht gefangen und erhält kein HTTP-Ergebnis.

Keine neue Exceptionklasse und keine neue Ergebnisform. Die Route loggt nicht
und erzeugt keine Telemetrie: kein Exceptiontext, Providertext, Querywert,
State, Code, Cookie, Token, Ziel oder Konfigurationswert verlässt sie.

## Nicht enthalten

Kein Korrelations-ID-Mechanismus, keine Middleware, kein Logging-Slice, keine
neue Telemetrie, kein Frontend-Pfad, kein Orphaned-Session-Cleanup, keine
globale Revoke-Politik, keine Persistenz und kein Production-Wiring. Keine
Änderung an Dependencies, Lockfiles, CI, Container oder `.grype.yaml`.
