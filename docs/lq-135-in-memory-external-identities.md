# LQ-135 — In-Memory External Identities

## Ergebnis

Ein lokaler, flüchtiger In-Memory-Adapter `InMemoryExternalIdentities`, der die
Ports `ExternalIdentityLookup` und `ExternalIdentityAdmissionStore` erfüllt. Kein
Production-Wiring und keine Admission-Erzeugung.

## Verhalten

- Der Konstruktor **kopiert** beide Eingabe-Mappings; spätere Änderungen an den
  übergebenen Mappings verändern den Adapter nicht.
- `get_user_id(identity)` ist rein lesend, löst exakt/opak auf, liefert die
  vorhandene Bindung oder neutral `None` und **liest die Uhr nicht**.
- `consume_admission_and_bind(admission_id, identity)`:
  - Der Ziel-`UserId` stammt **ausschließlich** aus dem `IdentityAdmissionRecord`;
    der Aufrufer liefert nie einen `UserId`.
  - **Reihenfolge:** unbekannte Admission → `None` (keine Uhr); konsumierte
    Admission → exakte Wiederholung (dieselbe `ExternalIdentity` und dieselbe
    bestehende Bindung) → derselbe `UserId`, sonst `None` (keine Uhr); strukturelle
    Neutralfälle einer unkonsumierten Admission (Identität bereits gebunden;
    Ziel-`UserId` bereits an eine andere Identität gebunden) → `None` (keine Uhr).
  - Erst für eine noch aktive, unkonsumierte Admission wird die Uhr **genau
    einmal** gelesen; danach Ablaufprüfung (`now >= expires_at` → `None`, auch
    exakt am Ablaufzeitpunkt).
  - **Erfolg:** beide neuen Zustands-Snapshots werden vollständig vorbereitet und
    dann gemeinsam übernommen — der Admission-Record wird durch einen mit
    `consumed_at=now` und exakt übergebener `bound_identity` ersetzt und die neue
    Bindung `identity -> target_user_id` angelegt; Rückgabe ist der intern
    bestimmte `UserId`.
  - Jeder Fehlerfall lässt Admission- und Binding-Zustand unverändert; alle Fehler
    sind neutral `None` ohne interne Details. Account-Linking bleibt ausgeschlossen.

## Bewusst nicht enthalten

- keine Admission-ID-Erzeugung und keine Methode zum nachträglichen Einfügen,
- keine User- oder Membership-Erzeugung,
- kein Account-Linking, Rebinding, Merge oder Unbinding,
- keine Login-/Callback-Route, keine OIDC-Bibliothek,
- keine Datenbank, kein Schema, keine Migration,
- keine Threads oder Locks, keine Persistenzsimulation,
- kein Production-Wiring, Provider oder Deployment.

## Nächster Schritt

Ein späterer Slice kann — nach der LQ-130-Persistenzentscheidung — einen atomaren
persistenten Adapter mit isolierten Integrationstests gegen eine wegwerfbare
Instanz definieren.
