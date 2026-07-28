# LQ-131 — External Identity Lookup

## Ergebnis

Ein unveränderliches `ExternalIdentity`-Wertobjekt und ein read-only
`ExternalIdentityLookup`-Port bilden die minimale, provider-neutrale Grundlage,
um ein verifiziertes `(issuer, subject)`-Paar einem internen `UserId` zuzuordnen.
Beides folgt der LQ-129-Entscheidung, ohne Persistenz, Admission oder Route.

## ExternalIdentity

- Genau zwei Felder: `issuer: str` und `subject: str`; beide dürfen nicht leer sein.
- Werte werden **exakt und opak** gehalten: kein Lowercasing, kein Entfernen von
  Slashes, keine E-Mail-Normalisierung. Zwei Identitäten sind nur gleich, wenn
  beide Felder byte-genau übereinstimmen.
- Das Objekt ist unveränderlich (frozen) und trägt **nichts** weiter — keine
  E-Mail, Claims, Tokens, Rollen oder Session-Daten.

## ExternalIdentityLookup

- Read-only Port mit `get_user_id(identity: ExternalIdentity) -> UserId | None`.
- Liefert den vorhandenen internen `UserId` oder neutral `None`; das Ergebnis
  verrät nichts über E-Mail, Claims oder Session-Zustand.
- Eine abweichende Schreibweise oder ein zusätzlicher Slash ist eine **andere**
  Identität und löst nicht auf.

## Bewusst nicht enthalten

- kein schreibender Binding-Port und keine Admission,
- keine Login-, Callback- oder Token-Route,
- keine OAuth-/OIDC-Bibliothek und kein konkreter Provider,
- kein Adapter, Schema oder Persistenz-Wiring,
- keine CORS-, Deployment- oder Shared-Environment-Änderung,
- kein Release und kein Deployment.

## Nächster Schritt

Ein späterer Slice kann — nach der LQ-130-Persistenzentscheidung und einer
Admission-Grenze — einen schreibenden Binding-Pfad definieren, der nur nach
expliziter interner Zulassung ein neues `(issuer, subject) → UserId` anlegt.
