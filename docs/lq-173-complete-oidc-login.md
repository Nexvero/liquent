# LQ-173 — Complete OIDC Login

## Zweck und Signaturen

Die transportfreie Completion-Grenze aus LQ-172: Aus einem bereits verifizierten
Callback wird **genau ein** interner Nutzer bestimmt und **genau eine** frische
Browser-Session ausgegeben. Keine Route, kein Cookie- oder Header-Aufruf, keine
Redirect-Validierung.

```python
# src/liquent_platform/application/complete_oidc_login.py
@dataclass(frozen=True, slots=True)
class CompletedOidcLogin:
    session: IssuedBrowserSession = field(repr=False)
    return_path: str | None = field(repr=False)


def complete_oidc_login(
    identity_lookup, admission_store, session_store, generator, verified,
    *, clock: Callable[[], datetime], lifetime: timedelta,
) -> CompletedOidcLogin | None: ...
```

Die Signatur nimmt **keine** ambient Session-ID, kein Request, Cookie, Header,
State, keinen Authorization Code, kein Token, keinen frei gewählten Nutzer und
keine Return-URL entgegen.

### Warum eine Funktion mit injizierter Uhr

Jeder Anwendungsfall in `application/` ist eine Funktion; Klassen dort sind nur
Ergebnisobjekte. Eine komponierende Klasse wäre die größere Form ohne Gewinn,
da keine Portmethode mit fester Signatur zu erfüllen ist.

Die Uhr ist dennoch ein `Callable` statt eines `datetime`-Werts wie in den
Nachbarfällen: Der Vertrag verlangt **keinen Uhrlesevorgang bei fachlicher
Ablehnung**. Ein übergebener Wert wäre vom Aufrufer bereits gelesen — die
Zusage könnte gar nicht erst existieren. `lifetime` bleibt ein Wert aus
Serverkonfiguration.

## Ablauf und Obergrenzen

1. Nicht positive `lifetime` → `OidcLoginCompletionUnavailable`, **vor** dem
   Lookup und vor jeder Mutation.
2. `identity_lookup.get_user_id(verified.identity)` **genau einmal**.
3. Vorhandener Nutzer → **exakt** dieser; die Admission wird **weder gelesen
   noch konsumiert**.
4. Kein Nutzer und keine Admission → `None`.
5. Kein Nutzer, Admission vorhanden → `consume_admission_and_bind(...)` **genau
   einmal**; `None` bleibt fachliche Ablehnung.
6. Erst danach: Uhr **genau einmal** lesen, `SessionPrincipal` bilden,
   `issue_browser_session(...)` **genau einmal**.
7. Ergebnis trägt **exakt** die zurückgegebene `IssuedBrowserSession` und
   **exakt** `verified.return_path`.

| Aufruf | Höchstens |
|---|---|
| Lookup · Admission · Uhr · Session-Issuance | je **1** |
| Generatoraufrufe | `session_id`, `csrf_token` — je **1** |

Kein zweiter Lookup, keine zweite Admission, kein zweiter Uhrlesevorgang, kein
Retry und kein Rollback. Nichts wird normalisiert oder kopiert: Identität,
Admission-ID, Nutzer und `return_path` gehen verbatim durch.

## Bindung und Admission

Ein bestehendes Binding hat **absoluten Vorrang** — es wird read-only aufgelöst
(LQ-131), und eine beiliegende Admission bleibt unangetastet, weil sie eine
einmalig konsumierbare Capability für die **erstmalige** Bindung ist (LQ-132).
Der atomare `consume_admission_and_bind` ist die **einzige** Schreibentscheidung
dieser Grenze; sein Ergebnis entscheidet allein, ohne zweiten Lookup, Fallback
oder Check-then-act.

Die Completion erzeugt **niemals** einen Nutzer, eine Mitgliedschaft, eine Rolle
oder eine Berechtigung.

## Zeit, Session und CSRF

Die Uhr wird **erst nach** belastbarer Nutzerermittlung gelesen — eine fachliche
Ablehnung erzeugt weder einen Messwert noch Session- oder CSRF-Material. Ein
falsch typisierter oder naiver Wert und eine werfende Uhr sind technische
Nichtverfügbarkeit; beide werden erkannt, **bevor** der Generator läuft, sodass
kein Material entsteht, das anschließend verworfen würde. `BaseException` wird
nicht gefangen.

Session-ID, CSRF-Material und Lebensdauer stammen ausschließlich aus der
bestehenden Issuance-Grenze (LQ-114/115); dieser Slice definiert keine neue
Zeit-, Rundungs- oder Max-Age-Semantik. Es gibt keine Übernahme, Verlängerung,
Rotation oder Widerrufung einer bestehenden Session.

## Ergebnis- und Return-Path-Grenze

`CompletedOidcLogin` ist frozen, slots-basiert und in **beiden** Feldern
`repr`-frei; die Darstellung ist `CompletedOidcLogin()`. Es trägt **keine**
`ExternalIdentity`, keinen `UserId`, keine Admission-ID, keine Claims und keine
Providerdaten.

Der `return_path` bleibt **unvalidiert und nicht transportfähig**. Ihn
weiterzureichen ist ein verlustfreies Handover an eine eigene
Validated-Internal-Destination-Grenze — **keine** Redirect-Freigabe. Er wird
hier weder interpretiert noch normalisiert.

## Fehlergrenze

Fachliche Ablehnung ist ein einheitliches `None` und unterscheidet nichts.
Technische Nichtverfügbarkeit ist `OidcLoginCompletionUnavailable` mit dem Code
`oidc_login_completion_unavailable` — getrennt von `OidcVerificationUnavailable`,
`OidcLoginUnavailable`, `OidcLoginStartConflict` und `SessionLifecycleConflict`.

Jede austretende Exception hat neutrale `args`, `__cause__ is None` und
`__context__ is None`; kein ursprünglicher Text erscheint im formatierten
Traceback. Erreicht wird das über dieselbe äußere Form wie in LQ-171: Eine
bereits **saubere** Completion-Exception behält ihre Identität, eine mit Cause
oder Context wird ersetzt, jede andere normale `Exception` — einschließlich
`SessionLifecycleConflict`, ohne Retry — ebenfalls, und die Ersetzung entsteht
außerhalb des Handlers.

## Teilfortschritt

Die Reihenfolge ist irreversibel. Eine erfolgreich konsumierte Admission bleibt
gebunden, auch wenn die Session-Speicherung danach scheitert; es gibt kein
Rollback und keinen zweiten Admission-Versuch. Ein neuer Versuch beginnt mit
einem **neuen Login-Start** und löst die nun gebundene Identität regulär über
den Lookup-Pfad auf.

## Nicht enthalten

Keine Callback-Route, kein Cookie- oder CSRF-Header-Aufruf, kein Redirect, kein
Validated-Internal-Destination-Modell, keine Portänderung, keine Änderung an
`verify_oidc_callback`, den Admission-, Session- oder In-Memory-Bausteinen,
keine neue Dependency und kein Lockfile-, CI-, Container- oder Grype-Eingriff.
LQ-158 bleibt für den Transport maßgeblich.
