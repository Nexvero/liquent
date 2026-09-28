# LQ-182 — Interne Onboarding-Autorität

## 1. Status, Ziel und Systemgrenze

Architekturentscheidung, **nur Vertrag**. Keine Python-Implementierung, keine
Tests, keine Migration, keine Tabelle, keine Portänderung, keine Route, keine
CLI, kein Wiring.

LQ-181 hat die Provisionierungsgrenze fertiggestellt: `provision_admission`
nimmt einen `ProvisioningRequestId`, einen `UserId`, einen `WorkspaceId` und
eine Lebensdauer und speichert genau eine Admission. Offen blieb, **woher diese
Eingaben autorisiert stammen dürfen**. Heute stammen sie nirgendwoher:
`UserId` und `WorkspaceId` sind `NewType`-Zeichenketten, im gesamten
Produktionscode existiert **keine** Konstruktionsstelle, es gibt weder eine
persistente Nutzer- noch Workspace-Entität, und `WorkspaceMembershipLookup` hat
außerhalb von Testdoubles **keine** Implementierung.

LQ-182 schließt genau diese Lücke — die **Existenz-, Vertrauens- und
Autoritätsgrenze** — und löst dabei das Henne-Ei-Problem des ersten
Entscheiders, ohne eine konkrete Umsetzung vorwegzunehmen.

## 2. Persistente Entitäten

`UserId` und `WorkspaceId` bezeichnen **dauerhafte interne Tatsachen**. Ein
Identifikator darf erst dann Ziel einer Provisionierung sein, wenn dasselbe
interne System of Record zum Entscheidungszeitpunkt bestätigen kann, dass die
Entität **existiert und aktiv ist**.

**Eine Admission wird niemals für eine bloße, unverbürgte Zeichenkette
provisioniert.** Das ist keine Formalie: Die Zusage aus LQ-178 — der Zielnutzer
stammt ausschließlich aus der intern gespeicherten Admission — ist nur so viel
wert wie die Verbürgtheit dieses gespeicherten Ziels. Ein frei erfundener
`target_user_id` machte die gesamte Kette wertlos.

Was LQ-182 **nicht** entscheidet: Tabellen, Spalten, Foreign Keys, Indizes,
Retention, Migrationen und SQL-Strategien. Es wird ausdrücklich **keine
fiktive Datenbankstruktur** vorweggenommen; die Persistenzform folgt in einem
eigenen Slice.

## 3. Reguläre Onboarding-Autorität

Eine reguläre Onboarding-Entscheidung stammt **ausschließlich** aus einer
bestehenden **persistenten, workspacebezogenen Verwaltungsautorität**.

**Research-Permissions reichen dafür ausdrücklich nicht.** Das ist am Bestand
belegbar: `Permission` kennt heute genau `research:read` und `research:write`,
und `permits_research` entscheidet allein über Lesen und Schreiben von
Forschungsdaten. Keine dieser Berechtigungen kann „darf jemanden aufnehmen"
ausdrücken, und keine darf dahin umgedeutet werden. Die Verwaltungsautorität
ist eine **eigene** Fähigkeit, keine stärkere Research-Permission.

Sie entsteht **niemals automatisch**: weder aus einer Membership, noch aus einer
Identitätsbindung, noch aus einer erfolgreichen Admission-Provisionierung, noch
aus einer erfolgreichen Anmeldung. Wer sich anmeldet, wird dadurch nicht zum
Verwalter.

Die Entscheidungsgrenze löst die Autorität **selbst** aus dem System of Record
auf — für den handelnden Prinzipal und den Zielworkspace. Sie nimmt **keinen**
frei übergebenen `UserId`, `WorkspaceId`, Rollennamen und **kein**
Autoritäts-Boolean entgegen; ein solcher Parameter wäre die Autorisierung selbst
und damit ihre Aufhebung.

Die genaue Rollen- beziehungsweise Capability-Form wird hier als **fachliche
Grenze** entschieden — eine benannte, persistente, workspacebezogene
Verwaltungsfähigkeit getrennt von den Research-Permissions —, aber **nicht**
implementiert und nicht modelliert.

## 4. Bootstrap des ersten Entscheiders

Eine autorisierte Entscheidung setzt einen autorisierten Entscheider voraus.
Ohne eine Ausnahme bliebe das System dauerhaft leer. Diese Ausnahme ist eine
**einmalige Offline-Control-Plane-Grenze**:

- **Zulässig nur**, solange **kein** Nutzer-, Workspace- und Autoritätsbestand
  existiert.
- Sie erzeugt **atomar** den ersten persistenten Nutzer, den ersten Workspace
  und dessen Verwaltungsautorität — alles drei oder nichts.
- Ausgeschlossen sind HTTP-Endpunkt, Admin-Header, Environment-Bootstrap,
  Migration-Seed, Self-Sign-up, First-login-Provisioning und direkter
  Datenbankzugriff aus Transportcode.
- Nach erfolgreichem Bootstrap ist sie **dauerhaft geschlossen** und **nicht**
  als allgemeiner Administrationsweg wiederverwendbar.

**Die Schließung folgt aus dem Zustand, nicht aus einer Einstellung.** Die
Vorbedingung ist die Leere des Bestands selbst; sobald eine Verwaltungsautorität
existiert, ist die Grenze zu — es gibt kein Flag, keine Umgebungsvariable und
keinen Schalter, der sie wieder öffnet. Genau das macht sie zu einer
Bootstrap-Grenze statt zu einer Hintertür.

Konkrete CLI, Operator-Authentisierung, Persistenz- und SQL-Strategie bleiben
eigenen Slices vorbehalten. LQ-182 erfindet **keine** Signatur.

## 5. `ProvisioningRequestId`

Der Handle **entsteht atomar mit der autorisierten Onboarding-Entscheidung** und
wird persistent **genau dieser Entscheidung** zugeordnet. Er ist damit die
dauerhafte Wiederholungsidentität eines fachlichen Vorgangs, nicht ein
Nebenprodukt eines Aufrufs.

- Derselbe fachliche Vorgang verwendet bei **jedem** technischen
  Wiederholungsversuch **exakt denselben** Handle.
- Er wird **weder** vom HTTP-Transport **noch** spontan vom Provisioning-Adapter
  neu erzeugt.
- Er ist **kein** öffentlicher Idempotency-Key, **kein** Admission-Handle und
  **kein** OIDC-State.
- Er bleibt `repr`-frei und gelangt **nicht** in Logs, Traces, Metriklabels oder
  Fehlertexte.
- Abweichender Inhalt unter demselben Handle bleibt der bestehende detailfreie
  LQ-181-Konflikt — kein Überschreiben, keine zweite Admission.

Die persistente Zuordnung ist der Grund, warum ein unklarer Ausgang überhaupt
auflösbar ist: Der Aufrufer muss den Handle nicht erinnern, sondern kann ihn aus
der Entscheidung wiedergewinnen.

## 6. Membership und Berechtigungen

Nutzer-, Workspace- und Verwaltungsautoritätserzeugung sind **getrennt** von
Admission-Provisionierung und Identitätsbindung.

- Die Provisionierung erzeugt **keine** Membership, Rolle, Permission oder
  Verwaltungsautorität.
- Eine spätere Identitätsbindung gewährt für sich allein **keinen**
  Workspace-Zugriff (LQ-129, LQ-132 — beide unverändert).
- **Reguläre Membership-Erzeugung** ist eine eigene Grenze und ein eigener
  Slice.
- **Rollen- und Capability-Persistenz** ist eine eigene Grenze und ein eigener
  Slice.

Eine Admission autorisiert die erstmalige Bindung einer externen Identität an
einen bereits bestehenden internen Nutzer — mehr nicht.

## 7. Fehler- und Wiederholungsgrenze

Fachliche Ablehnung und technische Nichtverfügbarkeit bleiben **getrennt und
detailfrei**. Kein ursprünglicher Fehlertext, kein Identifikator und keine
Exceptionkette verlassen die spätere Grenze.

Innerhalb des späteren Onboarding-Anwendungsfalls gibt es **keinen automatischen
Retry**. Bei unklarem Ausgang wird ausschließlich mit **derselben** persistent
zugeordneten Entscheidungs- und Request-Identität wiederholt — keine zweite
Admission, kein neuer Handle, kein Überschreiben einer bestehenden Entscheidung.

## 8. Nicht enthalten

Keine Python-Implementierung, Tests, Migration, Tabelle oder SQL-Strategie,
keine Portänderung, HTTP-Route, konkrete CLI, kein Production-Wiring, keine
Nutzer-, Workspace-, Membership- oder Rollenerzeugung, keine Änderung an LQ-181
und keine Grype-, CI-, Container-, Dependency- oder Lockfile-Arbeit.

## 9. Reihenfolge der Folgeslices

1. **LQ-182** — dieser Autoritätsvertrag.
2. Persistente **Nutzer-, Workspace- und Verwaltungsautoritätsgrundlage**.
3. **Einmaliger Bootstrap** des ersten Entscheiders.
4. **Regulärer autorisierter Onboarding-Anwendungsfall**, der
   `provision_admission` aufruft.
5. Persistente **Login-Transaktionen**.
6. Persistente **Sessions**.
7. **Erst danach** Wiederaufnahme von LQ-177 Production-Wiring.

Kein Slice dieser Kette darf so tun, als existierte ein autorisierter
Entscheider, bevor Schritt 2 und 3 abgeschlossen sind.
