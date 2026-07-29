# LQ-140 — Identity Admission ID Repr Hardening

## Ergebnis

Kleiner Sicherheitsslice: Der sensible Capability-Wert einer
`IdentityAdmissionId` ist auch bei **direkter Objekt-Repräsentation** nicht mehr
sichtbar. Geändert wurde ausschließlich die Felddefinition in
`src/liquent_platform/identity/admission.py` plus der zugehörige Docstring.

## Änderung

```
from dataclasses import dataclass, field
...
    value: str = field(repr=False)
```

Vorher stand dort `value: str`, wodurch der Wert im `repr` erschien.

## Begründung

`OidcLoginMaterial` (LQ-137), `PendingOidcLoginTransaction` (LQ-138) und
`OidcLoginState` (LQ-139) verbergen ihre sensiblen Werte bereits im `repr`. Das
in LQ-138 hinzugefügte Feld `admission_id` ist dort ausdrücklich als sensibler
Capability-Handle repr-frei — die `IdentityAdmissionId` selbst war es jedoch
noch nicht. Eine `IdentityAdmissionId` kann einen **einmalig konsumierbaren**
Onboarding-/Binding-Vorgang referenzieren; sie darf nicht versehentlich über
Objekt-Repräsentationen in Logs oder Fehlerdiagnosen gelangen. LQ-140 schließt
diese Lücke.

## Verbindlicher Vertrag

- `IdentityAdmissionId` bleibt **unveränderlich** und **hashbar**.
- Der Wert bleibt **exakt und opak** und wird **nicht normalisiert**.
- Ein **leerer Wert** bleibt ungültig (`admission id must not be empty`).
- **Gleichheit und Hashverhalten bleiben unverändert** — `field(repr=False)`
  berührt weder `__init__` noch `__eq__` noch `__hash__`.
- Der Wert bleibt über **`.value`** für autorisierte interne Verarbeitung
  verfügbar.
- Der **konkrete Wert erscheint nicht** im `repr`; der Klassenname darf
  erscheinen.
- Der Docstring benennt den Wert ausdrücklich als **sensiblen
  Capability-Handle**.
- **Keine** Änderung an `IdentityAdmissionRecord`, Ports, Adaptern oder
  Login-Modellen.

## Tests

`tests/test_identity_admission_id.py` — additiv erweitert von 7 auf 10 Tests.

**Unverändert bestehend:** exakter Wert · leerer Wert abgewiesen · keine
Normalisierung · Case-/Slash-Unterschiede bleiben unterschiedliche IDs ·
unveränderlich · hashbar und als Dict-Schlüssel verwendbar · nur das Feld
`value`.

**Neu:** `IdentityAdmissionId("secret-admission")` enthält `secret-admission`
nicht im `repr` · der Klassenname `IdentityAdmissionId` darf im `repr`
erscheinen · `.value` liefert nach der Härtung weiterhin exakt den
ursprünglichen Wert.

**Regression:** Admission-Record-, External-Identity-, Admission-Port-,
In-Memory-Adapter- und OIDC-Tests bleiben unverändert grün. Kein Test und kein
Produktionscode hing am sichtbaren `repr`; eine Voranalyse über `src/` fand
ausschließlich Docstring-Erwähnungen und den Import, keine Formatierung,
Stringkonversion oder Protokollierung einer `IdentityAdmissionId`.

## Bestehende Dokumente

`docs/lq-133-external-identity-admission-port.md` macht **keine** `repr`-Aussage
und `docs/lq-138-pending-oidc-login-transaction.md` beschreibt das Feld
`admission_id` bereits als repr-frei. Beide **widersprechen dem neuen Verhalten
nicht** und bleiben deshalb unverändert.

## Bewusst nicht enthalten

- keine Änderung an Semantik oder Portsignaturen,
- kein neuer Wertobjekttyp,
- keine Rotation oder Ersetzung bestehender Admissions,
- kein Store oder Adapter,
- keine Login-/Callback-Route,
- keine Persistenz oder Migration,
- keine Änderung am Grype-/CI-Workflow,
- kein Production-Wiring oder Deployment.
