# LQ-133 — External Identity Admission Port

## Ergebnis

Die minimale Typ- und Portgrenze für die **atomare** Umsetzung des LQ-132-Vertrags:
ein opakes `IdentityAdmissionId`-Wertobjekt und ein `ExternalIdentityAdmissionStore`-
Port, der eine intern ausgestellte Admission konsumiert und die erstmalige Bindung
einer verifizierten `ExternalIdentity` anlegt. Kein Adapter, keine Persistenz.

## Sicherheitsprinzip

Der Aufrufer übergibt **keinen** `UserId` an die Bindungsoperation. Der Ziel-`UserId`
stammt **ausschließlich** aus der intern gespeicherten, zuvor ausgestellten Admission.
Dadurch kann ein Login-/Callback-Aufrufer eine externe Identität **nicht** an einen
frei gewählten oder fremden Benutzer binden.

## IdentityAdmissionId

- Genau ein Feld `value: str`, das nicht leer sein darf.
- Wert **exakt und opak**: kein Trimmen, kein Lowercasing, keine Normalisierung.
- Unveränderlich und hashbar; keine weiteren Felder und keine Admission-Daten im
  Wertobjekt (keine Workspace-, Rollen-, Claims-, Token- oder Session-Daten).

## ExternalIdentityAdmissionStore

`consume_admission_and_bind(admission_id, identity) -> UserId | None`

- Der Store ermittelt den Ziel-`UserId` **ausschließlich** aus der Admission; der
  Aufrufer liefert niemals einen `UserId` (die Signatur enthält keinen).
- Admission-Prüfung, Ablaufprüfung, Einmal-Konsum und erstmalige Bindungsanlage
  erfolgen **atomar**.
- Erfolg liefert den intern bestimmten `UserId`.
- Eine **exakte Wiederholung** derselben bereits erfolgreich abgeschlossenen
  Operation ist idempotent und liefert denselben `UserId`.
- Unbekannte, abgelaufene oder anderweitig konsumierte Admission, Identitäts-
  kollision und eine Bindung an einen anderen User führen neutral zu `None`;
  `None` lässt **nicht** erkennen, welcher interne Fehlerfall eingetreten ist.
- Der Port erstellt **keinen** Benutzer, **keine** Workspace-Mitgliedschaft, Rolle
  oder Berechtigung; die Admission verweist auf einen bereits intern zugelassenen
  Ziel-`UserId`.
- Kein Überschreiben, Rebinding, Account-Linking oder Benutzer-Merge.

## Bewusst nicht enthalten

- kein In-Memory- oder persistenter Adapter,
- kein Schema und keine Migration,
- keine Admission-Erzeugung und keine Benutzererzeugung,
- keine Workspace-Mitgliedschaft,
- kein Anwendungsfall, der nur redundant delegiert,
- keine Login-/Callback-Route,
- keine OIDC-Bibliothek,
- kein Account-Linking, Rebinding, Merge oder Unbinding,
- kein Production-Wiring, Provider oder Deployment.

## Nächster Schritt

Ein späterer Slice kann — nach der LQ-130-Persistenzentscheidung — einen atomaren
Adapter für diesen Port als eigenen, isoliert getesteten Slice gegen eine
wegwerfbare Instanz implementieren.
