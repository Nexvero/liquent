# LQ-219 — Persistent User and Workspace Lifecycle Contract

## 1. Ergebnis

LQ-219 definiert den kleinsten sicheren Vertrag für die reguläre Anlage und
Stilllegung persistenter interner Nutzer und Workspaces.

Der Slice schließt noch keine Implementierung. Er entscheidet ausschließlich,
welche Fakten, Autoritäten, Vorbedingungen, Revisionen und Ergebnisse spätere
Slices sicher umsetzen müssen.

Zwei neue globale Management-Domänen werden getrennt festgelegt:

- User-Lifecycle-Management;
- Workspace-Lifecycle-Management.

Keine der beiden Autoritäten folgt aus Login, Session, gewöhnlicher
Membership, Research-Permission, Onboarding-Management, Membership-Management,
OIDC-Trust-Management oder Datenbankzugriff.

## 2. Nicht verhandelbare Identitätsfakten

`UserId` und `WorkspaceId` sind interne, stabile und nicht wiederverwendbare
Systemfakten.

Ihre Bedeutung darf nach Erzeugung weder auf eine andere Person noch auf einen
anderen Workspace übertragen werden. Umbenennung externer Anzeigenamen,
Provider-Wechsel oder organisatorische Änderungen verändern diese IDs nicht.

Eine stillgelegte ID bleibt dauerhaft reserviert. Löschen, Überschreiben,
Recycling und erneute Anlage unter derselben ID sind nicht zulässig.

Historische Entscheidungen, Sessions, Admissions, Memberships und Authorities
behalten ihre Referenz auf den ursprünglichen internen Fakt.

## 3. Status und Fail-closed-Wirkung

Nutzer besitzen genau einen aktuellen Lifecycle-Status: aktiv oder inaktiv.
Workspaces besitzen ebenfalls genau einen aktuellen Lifecycle-Status: aktiv
oder inaktiv.

Unbekannt, inaktiv, widersprüchlich oder technisch nicht eindeutig lesbar darf
niemals als aktiv behandelt werden.

Ein inaktiver Nutzer darf keine spätere Session-, Onboarding-, Trust-,
Membership-, Research- oder Managemententscheidung autorisieren.

Ein inaktiver Workspace darf keine spätere workspacebezogene Onboarding-,
Membership-, Research- oder Managemententscheidung autorisieren.

Die jeweiligen konsumierenden Grenzen müssen den aktuellen Systembestand
lesen. Ein früherer positiver Entscheid, ein Token, eine Session oder ein
zwischengespeicherter Snapshot ersetzt diese aktuelle Prüfung nicht.

## 4. SessionPrincipal ist keine Authority

Ein authentifizierter `SessionPrincipal` identifiziert ausschließlich den
Actor durch seine interne `UserId`.

Er enthält und gewährt keine Lifecycle-Authority, Rolle, Membership,
Permission oder pauschale Administratorstellung.

Jede Lifecycle-Entscheidung muss den Actor aus dem Principal nehmen und dessen
aktuellen aktiven Nutzerstatus sowie die passende dedizierte Authority aus dem
System of Record auflösen.

Caller-supplied Allow-Booleans, Rollen, Statusbehauptungen, Authority-Snapshots
oder frei gewählte Actor-IDs sind unzulässig.

## 5. Getrennte globale Lifecycle-Authorities

User-Lifecycle-Management autorisiert ausschließlich reguläre Nutzeranlage,
Nutzerdeaktivierung und Nutzerreaktivierung.

Workspace-Lifecycle-Management autorisiert ausschließlich reguläre
Workspace-Anlage und terminale Workspace-Deaktivierung.

Beide Authorities sind globale, persistente, explizite Fähigkeiten. Eine
Authority impliziert die andere nicht.

Sie implizieren ebenso wenig OIDC-Trust-, Onboarding-, Membership-Management-
oder Research-Rechte. Umgekehrt impliziert keine vorhandene Authority eine der
neuen Lifecycle-Authorities.

Ihre spätere Vergabe, Rotation, Deaktivierung, Verankerung und Recovery müssen
dem bereits entschiedenen revisionsgebundenen Lockout-Schutz folgen, bleiben
aber eigene Implementierungsslices.

## 6. Autoritative Zielbindung

Eine Nutzerentscheidung bindet Actor und Zielnutzer atomar an den aktuellen
persistenten Bestand.

Eine Workspace-Entscheidung bindet Actor und Zielworkspace atomar an denselben
aktuellen Bestand. Bei Workspace-Anlage wird zusätzlich genau ein bestehender
aktiver Zielnutzer als erster Onboarding-Manager gebunden.

Die Grenze darf keine caller-supplied Aussage akzeptieren, dass Actor, Ziel,
Workspace oder erster Manager existiert, aktiv oder zulässig sei.

IDs sind Eingaben zur Auswahl des Zieles, keine Beweise über dessen Zustand
oder über Authority.

## 7. Reguläre Nutzeranlage

Nutzeranlage erzeugt genau einen neuen aktiven internen Nutzer mit einer vom
System erzeugten stabilen `UserId`.

Der Caller darf die neue `UserId` nicht vorgeben. Eine bereits jemals
verwendete ID darf auch nach Stilllegung nicht erneut vergeben werden.

Die Anlage erzeugt ausdrücklich keine:

- externe Identitätsbindung oder Admission;
- Browser-Session oder Login-Transaktion;
- Workspace-Membership oder Research-Permission;
- Onboarding- oder Membership-Management-Authority;
- OIDC-Trust- oder Lifecycle-Management-Authority;
- Workspace-Anlage.

Damit ist ein neu angelegter Nutzer zunächst nur ein aktiver interner
Zielkandidat für nachfolgende, getrennt autorisierte Prozesse.

## 8. Reguläre Nutzerdeaktivierung

Nutzerdeaktivierung ist nur für einen bekannten aktuell aktiven Zielnutzer
zulässig.

Vor Erfolg muss der aktuelle Systembestand bestätigen, dass der Zielnutzer
vollständig aus allen wirksamen abhängigen Bereichen entfernt wurde:

- keine lebende Browser-Session;
- keine nutzbare ausstehende Admission für diesen Nutzer;
- keine aktive gewöhnliche Workspace-Membership;
- keine aktive Onboarding-Management-Authority;
- keine aktive Membership-Management-Authority;
- keine aktive OIDC-Trust-Management-Authority;
- keine aktive User- oder Workspace-Lifecycle-Management-Authority.

Diese Vorbedingungen sind ein Drain-Vertrag, kein impliziter Cascade. Der
Lifecycle-Entscheid widerruft oder verändert keine Fakten fremder Domänen.

Ist irgendeine Abhängigkeit aktiv, unbekannt oder nicht vollständig prüfbar,
wird die Deaktivierung ohne Statusänderung abgelehnt.

Damit bleiben bestehende letzter-Manager-Sicherungen maßgeblich. Erst sichere
Rotation und expliziter Entzug in der zuständigen Domäne erlauben den späteren
Nutzerabschluss.

## 9. Reguläre Nutzerreaktivierung

Nutzerreaktivierung ist nur für einen bekannten aktuell inaktiven historischen
Nutzer zulässig.

Sie ändert ausschließlich dessen Lifecycle-Status auf aktiv. Sie stellt weder
Memberships noch Sessions, Admissions, Permissions oder Management-
Authorities wieder her.

Da eine sichere Deaktivierung zuvor den vollständigen Drain verlangt, kann
Reaktivierung keine alte abhängige Fähigkeit stillschweigend neu wirksam
machen.

Alle benötigten Folgerechte müssen über ihre eigenen aktuellen, autorisierten
Grenzen erneut erteilt werden.

## 10. Reguläre Workspace-Anlage

Workspace-Anlage erzeugt genau einen neuen aktiven internen Workspace mit
einer vom System erzeugten stabilen `WorkspaceId`.

Der Caller darf die neue `WorkspaceId` nicht vorgeben. Eine historisch bereits
verwendete ID bleibt dauerhaft gesperrt.

Die Anfrage benennt genau einen bestehenden Nutzer als ersten
Onboarding-Manager. Der persistente Entscheid prüft dessen aktuellen aktiven
Status selbst.

Erfolg erzeugt atomar:

- den aktiven Workspace-Fakt;
- genau dessen erste aktive Onboarding-Management-Authority für den explizit
  gebundenen Zielnutzer.

Diese atomare Kopplung verhindert einen neu erzeugten, aber nicht verwaltbaren
Workspace. Sie verleiht dem Actor nicht automatisch dieselbe Authority.

Workspace-Anlage erzeugt keine gewöhnliche Membership, Research-Permission,
Membership-Management-Authority, OIDC-Trust-Authority oder globale
Lifecycle-Authority.

Der bestehende getrennte Membership-Management-Bootstrap bleibt für den neuen
Workspace erforderlich.

## 11. Terminale Workspace-Deaktivierung

Workspace-Deaktivierung ist nur für einen bekannten aktuell aktiven Workspace
zulässig und setzt ihn auf inaktiv.

Sie löscht oder überschreibt keine historischen Membership-, Permission-,
Onboarding- oder Management-Fakten. Deren Wirksamkeit endet fail-closed durch
den aktuellen inaktiven Workspace-Fakt.

Reguläre Workspace-Reaktivierung gehört nicht zu diesem Vertrag. Das verhindert,
dass erhaltene aktive Unterfakten später ohne erneute Einzelprüfung gemeinsam
wieder wirksam werden.

Ein stillgelegter Workspace und seine `WorkspaceId` bleiben dauerhaft
historisch erhalten und nicht wiederverwendbar. Ein neuer organisatorischer
Scope benötigt einen neuen Workspace-Fakt und eine neue ID.

## 12. Revisionen und idempotente Entscheidungen

Jede Domäne besitzt eine eindeutige aktuelle vollständige Lifecycle-Revision:
eine für den Nutzerbestand und eine für den Workspacebestand.

Jede Mutation verlangt die erwartete aktuelle Revision. Erfolg erzeugt
atomar genau eine neue vollständige Revision und genau einen neuen Current-
Pointer.

Jede Anfrage besitzt eine stabile, domänenspezifische Change-ID. Exakte
Wiederholung derselben ID mit identischem Inhalt liefert dasselbe bereits
committete Ergebnis, auch wenn sich der Bestand später geändert hat.

Wiederverwendung derselben Change-ID mit abweichendem Inhalt ist ein
detailfreier Konflikt. Konkurrenz gegen dieselbe erwartete Revision erlaubt
höchstens einen neuen Folgezustand.

Revisionen und Change-Entscheidungen werden mindestens so lange bewahrt, wie
irgendein Audit, Retry, historischer Nutzer oder Workspace darauf Bezug nehmen
kann. Ihre IDs dürfen niemals neu vergeben werden.

## 13. Widerruf und spätere Entscheidungen

Entzug einer Lifecycle-Authority muss jede später begonnene Entscheidung der
betroffenen Domäne sperren.

Eine bereits atomar committete Entscheidung bleibt historisch gültig. Eine
exakte Wiederholung ihrer Change-ID darf weiterhin dasselbe Ergebnis auflösen,
ohne aktuelle Authority erneut zu behaupten.

Neue Change-IDs müssen immer aktuellen aktiven Actor, aktuelle dedizierte
Authority, aktuellen Zielzustand und erwartete Revision gemeinsam prüfen.

Es gibt keinen Authority-Cache und keine aus einer früheren Session abgeleitete
Fortgeltung.

## 14. Neutrale Ablehnung und technische Nichtverfügbarkeit

Unbekannter oder inaktiver Actor, fehlende oder entzogene Authority,
unbekanntes Ziel, falscher Zielstatus, nicht erfüllter Drain, inaktiver erster
Onboarding-Manager und veraltete erwartete Revision enden als neutrale
fachliche Ablehnung ohne Bestandsdetails.

Abweichende Wiederverwendung einer Change-ID endet als detailfreier Konflikt.

Kann der persistente Bestand nicht vollständig, konsistent oder atomar gelesen
oder geschrieben werden, endet die Grenze separat als detailfreie technische
Nichtverfügbarkeit.

Dieser Slice benennt dafür bewusst keinen neuen Exception-Typ und entscheidet
keine Transportabbildung.

## 15. Bootstrap und bestehende Bestände

Der bestehende initiale Bootstrap bleibt geschlossen und wird nicht als
reguläre Lifecycle-Grenze wiederverwendet.

Ein späterer Bootstrap-Erweiterungsslice darf beim vollständig leeren Start
atomar den ersten Nutzer, ersten Workspace, dessen ersten Onboarding-Manager
und die ersten User- sowie Workspace-Lifecycle-Authorities erzeugen.

Migrationen dürfen diese Fakten weder seeden noch aus vorhandenen Daten
erraten. Bereits bestehende Installationen benötigen eine getrennte,
kontrollierte einmalige Verankerung der beiden neuen Authority-Domänen.

Die reguläre Persistenz und Mutation dieser Authorities bleibt ausdrücklich
spätere Arbeit.

## 16. Ausdrücklich nicht entschieden

LQ-219 entscheidet keine:

- Tabelle, Spalte, Constraint, SQL-Anweisung oder Migration;
- Domainklasse, Portsignatur, Adapter- oder Fehlertyp;
- CLI, Requestdatei, Route, Settings- oder Runtime-Verdrahtung;
- konkrete ID-Erzeugung oder Revisionsrepräsentation;
- automatische Session-, Admission-, Membership- oder Authority-Bereinigung;
- Self-Sign-up-, Einladungs- oder OIDC-Provisionierungsfunktion;
- Rolle, Gruppenmodell oder generische Administratorfähigkeit;
- Workspace-Reaktivierung oder physische Löschung.

## 17. Folgeplan und LQ-177

Der nächste Slice ist die additive persistente Foundation für Nutzer- und
Workspace-Lifecycle-Revisionen, Change-Entscheidungen und die zwei getrennten
globalen Authorities, ohne Seed und ohne Mutation.

Danach folgen getrennt Bootstrap-Erweiterung beziehungsweise Verankerung,
autorisierte Lifecycle-Mutationen und kontrollierte Offline-Bedienung.

Erst ein Mehrnutzer-/Multi-Workspace-Nachweis mit sicherer Rotation, Drain und
terminaler Stilllegung kann den verbleibenden LQ-177-Blocker schließen.
