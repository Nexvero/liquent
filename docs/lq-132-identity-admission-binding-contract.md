# LQ-132 — Identity Admission and Binding Contract

## Status

Architekturentscheidung und Vertrag, providerneutral. Keine Implementierung,
keine Ports/Modelle, kein Store, kein Adapter, keine Route, keine OIDC-Bibliothek,
kein Schema, keine Persistenz und keine Freigabe einer Laufzeitumgebung. Baut auf
LQ-129 (Identitätsgrenze), LQ-130 (Persistenzgrenze) und LQ-131
(`ExternalIdentity` + read-only Lookup) auf.

## Ziel

Definiere den Vertrag für **kontrollierte Admission** und die **erstmalige
Bindung** einer vollständig verifizierten `ExternalIdentity(issuer, subject)` an
einen internen `UserId`.

## Kernentscheidung

Eine erfolgreiche externe Authentifizierung beweist **nur** eine Identität. Sie
erzeugt **niemals** allein einen `UserId`, eine Identitätsbindung, eine
Workspace-Mitgliedschaft, eine Rolle oder eine Berechtigung.

## Auflösen einer bestehenden Bindung vs. erstmalige Bindung

- Eine bereits gebundene `ExternalIdentity` wird **ausschließlich** auf den
  vorhandenen `UserId` aufgelöst (read-only, LQ-131). Es entsteht keine neue
  Bindung und keine neue Berechtigung.
- Eine **ungebundene** `ExternalIdentity` darf **nur nach einer gültigen internen
  Admission** an einen `UserId` gebunden werden.

## Admission

- Admission muss **vor** der Bindung geprüft werden und stammt aus einem
  **expliziten internen Onboarding-/Einladungsprozess** — nicht aus externen
  Claims und nicht aus der bloßen Tatsache einer erfolgreichen Authentifizierung.
- Eine Admission ist **einmalig konsumierbar**: nach erfolgreichem Konsum kann sie
  keine weitere Bindung mehr autorisieren.
- Eine Admission begrenzt mindestens **Zweck, Ablauf (Gültigkeitszeit) und
  Zielkontext**. Konkrete Speicherung und technische Repräsentation bleiben
  späteren Slices vorbehalten.
- Veränderliche OIDC-Claims wie E-Mail oder Anzeigename sind **weder** dauerhafter
  Identitätsschlüssel **noch** alleinige Admission-Berechtigung.

## Eindeutigkeit der Bindung

- Die Bindung `(issuer, subject) -> UserId` ist **eindeutig**.
- Sie wird **niemals** stillschweigend überschrieben oder auf einen anderen
  `UserId` umgebogen.

## Atomarität

Admission-Prüfung, Konsum der einmaligen Admission und Anlage der
Identitätsbindung erfolgen als **eine** atomare, fail-closed Operation. Es gibt
keinen beobachtbaren Zwischenzustand, in dem eine Admission konsumiert, aber keine
Bindung angelegt wäre (oder umgekehrt).

## Idempotenz

Die Wiederholung **derselben, bereits erfolgreich abgeschlossenen** Operation wird
sicher und idempotent behandelt: dieselbe verifizierte `ExternalIdentity` löst auf
denselben `UserId` auf, ohne die Admission erneut zu konsumieren und ohne eine
zweite Bindung zu erzeugen.

## Neutrale Fehlergrenze

Die folgenden Fälle enden mit einem **neutralen Fehler ohne Offenlegung interner
Zustände** (kein Hinweis darauf, ob eine Identität, ein Nutzer, eine Admission
oder eine Bindung existiert):

- eine Kollision bei der Bindungsanlage,
- eine bereits konsumierte oder abgelaufene Admission,
- eine `ExternalIdentity`, die bereits an einen **anderen** `UserId` gebunden ist.

## Autorisierungstrennung

- Workspace-Mitgliedschaft und Rollen werden **ausschließlich** durch interne
  Liquent-Regeln erzeugt.
- Eine Identitätsbindung allein gewährt **noch keinen** Workspace-Zugriff.

## Bewusst nicht enthalten

Vertraglich ausgeklammert und als spätere, eigene Entscheidungen markiert:

- Account-Linking, Rebinding, Merge zweier Benutzerkonten und Entfernen einer
  Identitätsbindung,
- Multi-Issuer- und Enterprise-SSO-Erweiterungen.

Technisch ausgeklammert (dieser Slice ist reine Dokumentation):

- keine neuen Python-Modelle oder Ports,
- kein schreibender Binding-Store,
- kein Adapter oder In-Memory-Store,
- keine Login-/Callback-Route,
- keine OIDC-Bibliothek,
- kein Schema, keine Migration und keine Persistenz,
- keine Workspace-Mitgliedschaftsimplementierung,
- kein Account-Linking oder Rebinding,
- kein Production-Wiring, kein Provider und kein Deployment.

## Nächster Schritt

Ein späterer Slice kann — nach der LQ-130-Persistenzentscheidung — einen
schreibenden Admission-/Binding-Pfad als kleinen, isoliert getesteten Slice
definieren, der diesen Vertrag umsetzt: atomare Admission-Prüfung, Einmal-Konsum
und eindeutige Bindungsanlage.
