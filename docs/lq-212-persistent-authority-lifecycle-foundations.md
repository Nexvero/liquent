# LQ-212 — Persistent Authority Lifecycle Foundations

## 1. Status und Ziel

LQ-212 implementiert die getrennten persistenten Grundlagen für den in LQ-211
entschiedenen Lifecycle zweier Management-Authority-Domänen:

- globale OIDC-Trust-Management-Authority;
- workspacebezogene Membership-Management-Authority.

Der Slice stellt stabile interne Identitäten, leere persistente Inventare und
Scope-Invarianten bereit. Er führt noch keine Verankerung, reguläre Mutation
oder Recovery aus.

Die beiden Domänen bleiben strukturell getrennt. Es entsteht keine generische
Admin-Rolle, keine gemeinsame Capability-Tabelle und kein übergreifender
Authority-Port.

## 2. Stabile interne Identitäten

Die OIDC-Trust-Domäne erhält drei eigene Typen:

- `OidcTrustAuthoritySetRevisionId`;
- `OidcTrustAuthorityLifecycleChangeId`;
- `OidcTrustAuthorityRecoveryId`.

Die Membership-Management-Domäne erhält drei weitere eigene Typen:

- `WorkspaceMembershipAuthoritySetRevisionId`;
- `WorkspaceMembershipAuthorityLifecycleChangeId`;
- `WorkspaceMembershipAuthorityRecoveryId`.

Alle sechs Typen sind unveränderlich, slotted und repr-frei. Leere und
nicht-stringförmige Werte werden bereits an der Modellgrenze abgewiesen.

Die Typtrennung verhindert, dass Set-Revision, reguläre Entscheidung oder
Recovery-Entscheidung miteinander verwechselt werden. Ebenso kann keine ID
der globalen Domäne strukturell in der Workspace-Domäne eingesetzt werden.

## 3. Sichere Erzeugung

Der bestehende `SecureIdentityAuthorityMaterialGenerator` erzeugt jede dieser
Identitäten durch einen unabhängigen Zug aus Betriebssystemzufall.

Es gelten weiterhin mindestens 32 Byte Entropie pro Zug. Identitäten werden
nicht aus UserId, WorkspaceId, vorheriger Revision, Zeit, Prozessdaten oder
fachlichen Inhalten abgeleitet.

Der Generator gewährt keinerlei Authority. Eine erzeugte ID wird erst durch
eine spätere erfolgreich committete persistente Entscheidung zu einem
dauerhaften Fakt.

## 4. Additive Migration

Revision `20260812_0013` baut ausschließlich auf `20260812_0012` auf. Sie
ändert keine vorhandene Authority-, Nutzer-, Workspace-, Membership- oder
Trust-Zeile.

Für globale OIDC-Trust-Authority entstehen fünf leere Tabellen:

- vollständige Authority-Set-Revisionen;
- Mitglieder jeder Set-Revision;
- der aktuelle globale Revisionspointer;
- reguläre Lifecycle-Entscheidungen;
- getrennte Recovery-Entscheidungen.

Für workspacebezogene Membership-Management-Authority entstehen ebenfalls
fünf leere Tabellen:

- vollständige Authority-Set-Revisionen mit Workspace-Bindung;
- Mitglieder jeder Set-Revision;
- ein aktueller Revisionspointer pro Workspace;
- reguläre Lifecycle-Entscheidungen mit Workspace-Bindung;
- getrennte Recovery-Entscheidungen mit Workspace-Bindung.

Die Migration erzeugt keine Seeds, Revisionen, Pointer, Change-Entscheidungen
oder Recovery-Entscheidungen.

## 5. Vollständige unveränderliche Sets

Eine Set-Revision beschreibt später den vollständigen Authority-Bestand eines
Scopes nach genau einem Commit. Ihre Mitglieder tragen ausschließlich
`active` oder `inactive`.

Die globale Domäne besitzt höchstens einen aktuellen Pointer. Die
Membership-Domäne besitzt höchstens einen aktuellen Pointer je Workspace.

Historische Set-Mitglieder sind an ihre Revision gebunden. Das Entfernen oder
Umdeuten einzelner historischer Mitglieder ist nicht Teil dieses Slices.

Die Foundation legt bewusst keine API fest, die einen vom Aufrufer gelieferten
kompletten Allow-Satz übernimmt. Eine spätere Mutation muss aus einer
zielbezogenen Absicht selbst das neue vollständige Set ableiten.

## 6. Workspace-Scope-Integrität

Membership-Authority-Revisionen tragen ihren exakten `WorkspaceId`-Scope.

Aktuelle Pointer, reguläre Entscheidungen und Recovery-Entscheidungen binden
ihre referenzierten Revisionen über Revision und Workspace gemeinsam. Eine
Revision aus Workspace A kann daher nicht als aktueller oder resultierender
Bestand von Workspace B persistiert werden.

Diese Datenbankinvariante ersetzt keine spätere Autorisierungsprüfung. Sie
verhindert zusätzlich beschädigte domänenübergreifende Verknüpfungen im
normativen Persistenzsystem.

## 7. Reguläre Lifecycle-Entscheidungen

Das persistente Inventar reserviert genau vier Intents:

- `anchor` für die erste kontrollierte Verankerung;
- `grant` für erstmalige Authority;
- `deactivate` für wirksamen Entzug;
- `reactivate` für historische Wiederaktivierung.

Nur `anchor` besitzt keine erwartete Vorgängerrevision. Grant, Deactivate und
Reactivate müssen eine erwartete Revision tragen. Jede Entscheidung bindet
eine resultierende Revision.

Diese Form ist noch keine ausführbare Mutation. Actor-Authority, aktiver
Nutzerstatus, Workspace-Status, zulässiger Übergang, Lockout-Schutz,
Idempotenz und Konkurrenzordnung bleiben Aufgaben späterer Slices.

## 8. Getrennte Recovery-Inventare

Recovery verwendet eigene IDs und eigene Tabellen. Sie kann dadurch nicht als
regulärer Lifecycle-Change oder technischer Retry ausgegeben werden.

Eine Recovery-Entscheidung bindet Zielnutzer, erwartete Revision und
resultierende Revision. Im Membership-Fall bindet sie zusätzlich den exakten
Workspace.

Die Foundation implementiert weder Offline-Credentials noch Eligibility,
Owner-only Input, Operatorausgabe oder Reaktivierung. Insbesondere wählt sie
keinen neuen Manager und ändert keinen Nutzer- oder Workspace-Status.

## 9. Bestehender Bootstrap bleibt unverankert

LQ-200 und LQ-208 können bereits erste Authority-Fakten erzeugen. Diese Fakten
besitzen historisch keine Authority-Set-Revision.

LQ-212 adoptiert sie nicht stillschweigend. Nach der Migration bleiben alle
neuen Set-, Pointer-, Lifecycle- und Recovery-Inventare leer, selbst wenn
Bootstrap-Authority bereits existiert.

Damit erfindet die Migration weder einen Actor noch einen autorisierten
Commit. Bootstrap bleibt dauerhaft geschlossen, sobald seine bisherige
Authority-Historie existiert; die neue Foundation öffnet ihn nicht erneut.

## 10. Fail-closed und technische Grenzen

Dieser Slice besitzt keinen Lookup- oder Mutationsport und benennt deshalb
keine neue fachliche oder technische Exception.

Spätere Grenzen müssen neutrale Abwesenheit oder Ablehnung von detailfreier
technischer Nichtverfügbarkeit trennen. Weder Ergebnis noch Fehler dürfen
Actor, Ziel, Scope, Authority-Bestand, Revision, SQL oder Verbindungsdetails
offenlegen.

Ein `SessionPrincipal` wird hier weder akzeptiert noch persistiert. In späteren
regulären Entscheidungen identifiziert er ausschließlich den Actor und darf
niemals selbst Authority transportieren.

## 11. Retention und Nichtwiederverwendung

Set-Revisionen, Lifecycle-Change-IDs und Recovery-IDs sind dauerhafte
Entscheidungsidentitäten. Nach Sichtbarkeit dürfen sie innerhalb ihres
jeweiligen Inventars nicht erneut für einen anderen Inhalt verwendet werden.

Historische Revisionen, Mitglieder und Entscheidungen müssen mindestens so
lange erhalten bleiben wie aktuelle Fakten, Retries, Audits oder Recovery auf
sie verweisen können.

Dieser Slice entscheidet keine physische Tabellenpartitionierung,
Archivierungsfrist, Löschstrategie oder konkrete Datenschutzfrist. Eine
spätere Retention-Policy darf die genannten Sicherheitsuntergrenzen nicht
unterlaufen.

## 12. Bewusst nicht enthalten

LQ-212 implementiert insbesondere keine:

- Verankerung vorhandener Bootstrap-Authority;
- Grant-, Deactivate- oder Reactivate-Mutation;
- Lockout- oder Recovery-Entscheidung;
- neue Port-, Adapter- oder Signaturgrenze;
- Route, CLI, Settings-, Environment- oder Startup-Verdrahtung;
- Nutzer-, Workspace-, Membership- oder Research-Permission-Mutation;
- Änderung der bestehenden fachlichen Trust- oder Membership-Mutationen.

## 13. Nachweis

Tests belegen die sechs getrennten repr-freien Identitätstypen, ihre sichere
unabhängige Erzeugung und die leeren neuen Inventare.

Weitere Nachweise sichern, dass Bootstrap-Fakten unverankert bleiben, ein
regulärer Change ohne erwartete Revision scheitert und ein Membership-Pointer
keine Revision eines anderen Workspace referenzieren kann.

## 14. Nächster Slice

LQ-213 soll die kontrollierte einmalige Verankerung bereits vorhandener
Bootstrap-Authority implementieren.

Diese Grenze muss je Domäne Actor, aktive Foundation, existierende Authority,
leeres Lifecycle-Inventar und Scope atomar aus dem System of Record binden.
Sie darf den Authority-Status nicht ändern und genau die erste vollständige
Set-Revision samt aktuellem Pointer und stabiler Anchor-Entscheidung erzeugen.
