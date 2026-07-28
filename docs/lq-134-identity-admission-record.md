# LQ-134 — Identity Admission Record

## Ergebnis

Das minimale unveränderliche interne Zustandsmodell einer Identity-Admission:
`IdentityAdmissionRecord`. Kein Store, kein Adapter, kein neuer Port, keine Route.

## Modell

```
@dataclass(frozen=True, slots=True)
class IdentityAdmissionRecord:
    target_user_id: UserId
    target_workspace_id: WorkspaceId
    expires_at: datetime
    consumed_at: datetime | None = None
    bound_identity: ExternalIdentity | None = None
```

## Vertrag

- Die Klasse beschreibt **ausschließlich** intern gespeicherten Admission-Zustand.
- Der Zweck ist durch den Modelltyp festgelegt: die **erstmalige Bindung** einer
  externen Identität. Es gibt keine zusätzliche Purpose-Enum.
- `target_user_id` stammt aus kontrolliertem internem Onboarding.
- `target_workspace_id` begrenzt den Zielkontext, erzeugt aber **keine**
  Mitgliedschaft, Rolle oder Berechtigung.
- `expires_at` muss timezone-aware sein; `consumed_at` muss, sofern gesetzt,
  timezone-aware sein.
- `consumed_at` und `bound_identity` müssen **entweder beide gesetzt oder beide
  `None`** sein.
- Ein konsumierter Record bewahrt die **exakt** gebundene `ExternalIdentity`,
  damit eine exakte Wiederholung später idempotent erkannt werden kann.
- Der Record enthält **keine** E-Mail, Claims, IdP-Tokens, Rollen, Berechtigungen
  oder Session-Daten.
- Es findet **keine** automatische Normalisierung irgendeines Wertes statt.
- Das Modell entscheidet **nicht** über Gültigkeit und mutiert **keinen** Zustand.

## Bewusst nicht enthalten

- keine Purpose-Enum mit nur einem Wert,
- keine Membership-Erzeugung,
- kein Ablauf-/Konsum-Helper (solange kein Adapter ihn benötigt),
- kein Secret-Generator,
- kein Admission-Erzeugungs-Anwendungsfall,
- keine Änderung an `ExternalIdentityAdmissionStore`,
- kein In-Memory- oder persistenter Adapter,
- kein Schema, keine Migration, keine Login-/Callback-Route,
- kein Production-Wiring oder Deployment.

## Nächster Schritt

Ein späterer Slice kann — nach der LQ-130-Persistenzentscheidung — einen atomaren
Adapter definieren, der solche Records erzeugt, prüft und einmalig konsumiert und
dabei den LQ-132/133-Vertrag umsetzt.
