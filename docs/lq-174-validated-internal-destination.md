# LQ-174 — Validierte interne Destination

## Zweck und Signaturen

Die transportfreie Grenze aus LQ-158 §15.3: Ein optionaler serverseitiger
`return_path` wird in ein garantiert same-origin-fähiges internes Ziel
überführt. Keine HTTP-Antwort, kein `Location`-Header, kein Redirect.

```python
# src/liquent_platform/application/internal_destination.py
@dataclass(frozen=True, slots=True)
class ValidatedInternalDestination:
    value: str = field(repr=False)


def resolve_internal_destination(
    return_path: str | None,
) -> ValidatedInternalDestination | None: ...
```

Kein Port, kein Zustand, keine weitere öffentliche Form. Die Grenze liest
**keinen** Request und **keinen** Host-, Forwarded- oder Origin-Header, kennt
**keine** Session, Identität, Admission oder OIDC-Werte und macht **kein**
Netzwerk und **keine** DNS-Auflösung. `CompletedOidcLogin` bleibt unverändert.

## Positivgrammatik

Ein gültiges Ziel ist eine rohe ASCII-Pfadreferenz innerhalb derselben Origin:

```
ziel       := "/"  |  "/" segment ( "/" segment )*
segment    := 1*unreserved,  segment ∉ { ".", ".." }
unreserved := A-Z  a-z  0-9  -  .  _  ~
```

zuzüglich `type(value) is str` und `1 <= len(value) <= 2048`; der Wert darf
nicht auf `/` enden. Genau ein privates Prädikat
`_is_valid_internal_path(value)` trifft diese Entscheidung, verwendet von
`ValidatedInternalDestination.__post_init__` **und** von
`resolve_internal_destination` — keine zweite Regelmenge, kein abweichender
Sonderfall. Die doppelte Ausführung auf dem Erfolgspfad ist gewollt: Die
Invariante gilt unabhängig davon, wer konstruiert.

## Sicherheitsrelevante Folgen der Grammatik

Weil die Regel eine **erlaubte Zeichenmenge** ist und keine Verbotsliste, sind
strukturell ausgeschlossen — ohne dass einer dieser Fälle eigens geprüft würde:

- **Scheme** (`https:`) — `:` ist nicht unreserved, zudem fehlt der führende `/`
- **Authority / Network-Path** (`//host`) — leeres erstes Segment
- **Userinfo** (`@`), **Query** (`?`), **Fragment** (`#`), **Backslash** (`\`),
  **Prozentzeichen** und damit **jede Prozentkodierung**, **Whitespace**,
  **Steuerzeichen** und **Nicht-ASCII** — sämtlich nicht unreserved
- **leere Segmente** und **Dot-Segmente** (`.`, `..`) — eigene Segmentregel
- **Normalisierung** — findet nicht statt

Repräsentativ abgelehnt: `https://evil.test`, `//evil.test`, `\evil.test`,
`/a?next=//evil.test`, `/%2f%2fevil.test`, `/a//b`, `/a/../b`, `/tökén`.

Gültig bleiben `/`, `/workspaces/w-1/research`, `/users/user_1`,
`/reports/v1.2` und `/a/~draft` — ein Punkt **innerhalb** eines Segments ist
erlaubt, nur die Segmente `.` und `..` sind es nicht. Die bewusst enge Grammatik
schließt Browser-Normalisierungsunterschiede **strukturell** aus, statt sie
nachzubilden.

### Warum kein Parser und kein Normalisierer

Weder `urlsplit`, `urlparse`, `urljoin`, Unquote/Decode noch ein Regex mit
implizitem Unicode-Verhalten kommen zum Einsatz.

- `urlsplit` entfernt Tab, LF und CR still an jeder Stelle. Ein
  Parse-dann-Prüfen-Entwurf validierte den **gereinigten** String, während der
  Originalwert — der später in `Location` stünde — das Steuerzeichen behielte.
  Dieselbe Falle prüfen `oidc_client_configuration.py` und `app.py` bereits am
  Rohwert. `urlsplit` meldet zudem leere und fehlende Query oder Fragment
  identisch, sodass `?` und `#` ohnehin am Rohstring zu suchen wären.
- `urljoin` ist ein **Normalisierer** und damit das Gegenteil des Auftrags: Er
  löst Dot-Segmente auf, kann über die Wurzel hinauslaufen und aus einer
  Network-Path-Referenz eine absolute fremde Origin erzeugen — genau der offene
  Redirect, den diese Grenze verhindert (LQ-136).
- Weil `%` vollständig verboten ist, stellt sich die Dekodierfrage nie. Die
  akzeptierte Sprache ist eine echte Teilmenge von RFC-3986-`path-absolute` und
  mit einer Mengenzugehörigkeit entscheidbar; ein Parser brächte nur Fläche.

## Ergebnissemantik

| Eingabe | Ergebnis |
|---|---|
| `None` | `ValidatedInternalDestination("/")` — festes sicheres Standardziel |
| gültiger `str` | validiertes Objekt mit **exakt demselben Stringobjekt** |
| ungültiger `str` | `None` |
| falscher Typ | `None` |

Ein ungültiger gesetzter Wert fällt **niemals** auf `/` zurück: Fehlender und
manipulierter Wert sind verschiedene Situationen, und sie zusammenzulegen hieße,
eine Manipulation still auf eine funktionierende Seite umzuleiten.
Der Resolver wirft auf dem Ablehnungspfad **nicht**. Die direkte Konstruktion
eines ungültigen Objekts scheitert mit `ValueError("invalid internal
destination")` — ohne den abgelehnten Wert und ohne Exceptionkette. `repr(...)`
ist `ValidatedInternalDestination()`. Keine Logs, Telemetrie oder Metriklabels.
`type(value) is str` statt `isinstance`, weil eine `str`-Subklasse Gleichheit
neu definieren und ein hier validierter Wert später anders verglichen werden
könnte.

## Sicherheitsgrenze

Ein validiertes Objekt ist die **einzige** Form, die eine spätere
Callback-Route als internes Redirect-Ziel akzeptieren darf; ein roher
`return_path` darf nie direkt in `Location` geschrieben werden. Das Objekt
enthält keine Origin und keine absolute URL. Ob eine Ablehnung zu welchem Ziel
und Status führt, entscheidet erst ein späterer Transportvertrag (LQ-158).

**Syntaktisch gültig bedeutet nicht existent, autorisiert oder fachlich
zulässig.** Diese Grenze garantiert same-origin-fähige **Pfadsyntax**, nicht
dass eine UI-Route existiert oder für einen Nutzer erlaubt ist. Ein valider
interner Pfad gewährt **keine** Berechtigung; die Zielanwendung autorisiert
unverändert selbst.

## Nicht enthalten

Keine Workspace- oder Membership-Prüfung, Route-Registry, Frontend-Router-
Abfrage, Rollen- oder Berechtigungsentscheidung, keine extern konfigurierbare
Prefix-Liste, kein frei übergebbares Defaultziel. Keine Callback-Route, kein
`Location`-Header, keine Änderung an LQ-138, LQ-155, LQ-158, LQ-163, LQ-172 und
LQ-173, keine neue Dependency und kein Lockfile-, CI-, Container- oder
Grype-Eingriff.
