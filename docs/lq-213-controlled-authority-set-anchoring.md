# LQ-213 — Controlled Authority-Set Anchoring

## 1. Status und Ziel

LQ-213 implementiert die einmalige kontrollierte Verankerung der bereits durch
LQ-200 beziehungsweise LQ-208 erzeugten Bootstrap-Authorities.

Die Verankerung überführt vorhandene Authority-Fakten in die mit LQ-212
bereitgestellten vollständigen Set-Revisionsinventare. Sie erfindet keine
frühere Historie und verändert keinen Authority-Status.

Globale OIDC-Trust-Authority und workspacebezogene Membership-Management-
Authority besitzen weiterhin getrennte Modelle, Ports, Adapter, IDs,
Persistenzinventare und Fehlergrenzen.

## 2. Zwei explizite Ports

`OidcTrustAuthoritySetAnchor` akzeptiert ausschließlich:

- eine stabile `OidcTrustAuthorityLifecycleChangeId`;
- einen bereits authentifizierten `SessionPrincipal`.

`WorkspaceMembershipAuthoritySetAnchor` akzeptiert ausschließlich:

- eine stabile `WorkspaceMembershipAuthorityLifecycleChangeId`;
- einen bereits authentifizierten `SessionPrincipal`;
- den exakten `WorkspaceId`-Scope.

Kein Port akzeptiert Zielnutzer, Authority-Liste, Status, Rolle, Capability-
Namen, Allow-Boolean, erwartete Revision oder resultierende Revision.

Der Principal identifiziert nur den Actor. Authority und vollständiger Bestand
werden innerhalb derselben persistenten Entscheidung aktuell aufgelöst.

## 3. Ergebnisidentitäten

Eine erfolgreiche globale Verankerung liefert ein
`AnchoredOidcTrustAuthoritySet` mit Change-ID und erzeugter Set-Revision.

Eine erfolgreiche Workspace-Verankerung liefert ein
`AnchoredWorkspaceMembershipAuthoritySet` mit Change-ID, erzeugter
Set-Revision und Workspace-Scope.

Die Ergebnisse sind unveränderlich, slotted und enthalten keine Rollen,
Permissions oder übertragbare Authority.

## 4. Zulässiger globaler Ausgangsbestand

Die globale Verankerung ist nur zulässig, wenn:

1. mindestens ein persistenter OIDC-Trust-Authority-Fakt existiert;
2. der Actor als aktiver interner Nutzer existiert;
3. der Actor aktuell eine aktive OIDC-Trust-Management-Authority besitzt;
4. noch keine globale Set-Revision existiert;
5. kein globaler Current-Pointer existiert;
6. keine globale Lifecycle-Entscheidung existiert;
7. keine globale Recovery-Entscheidung existiert.

Unbekannter oder inaktiver Actor, fehlende oder inaktive Actor-Authority und
ein bereits belegtes Lifecycle-Inventar enden neutral mit `None`.

## 5. Zulässiger Workspace-Ausgangsbestand

Die Workspace-Verankerung bindet alle Voraussetzungen an genau den gelieferten
Workspace. Sie ist nur zulässig, wenn:

1. dort mindestens ein persistenter Membership-Management-Authority-Fakt
   existiert;
2. Actor und Workspace aktuell aktiv sind;
3. der Actor dort aktuell aktive Membership-Management-Authority besitzt;
4. für diesen Workspace keine Set-Revision existiert;
5. für diesen Workspace kein Current-Pointer existiert;
6. für diesen Workspace keine Lifecycle-Entscheidung existiert;
7. für diesen Workspace keine Recovery-Entscheidung existiert.

Bestände anderer Workspaces schließen diesen Scope nicht. Eine Revision oder
Entscheidung eines anderen Workspace wird weder gelesen noch adoptiert.

## 6. Vollständiger Snapshot

Der Adapter liest alle vorhandenen Authority-Zeilen des exakten Scopes selbst.
Der Aufrufer kann keine Mitglieder auswählen oder auslassen.

Aktive und inaktive historische Authority-Fakten werden mit unverändertem
Status in die erste vollständige Set-Revision kopiert. UserIds und Status
werden nicht normalisiert, umgeschrieben oder neu interpretiert.

Die aktuelle Authority-Tabelle bleibt unverändert. Verankerung erzeugt weder
Grant noch Deactivate oder Reactivate und besitzt keine Nebenwirkung auf
Nutzer- oder Workspace-Status.

## 7. Atomarer Commit

Eine neue erfolgreiche Verankerung erzeugt atomar:

1. genau eine neue unveränderliche Set-Revision;
2. genau ein Set-Mitglied je bestehendem Authority-Fakt des Scopes;
3. den ersten Current-Pointer des Scopes;
4. genau eine Lifecycle-Entscheidung mit Intent `anchor`;
5. Actor und Zielnutzer der Anchor-Entscheidung als dieselbe intern
   authentifizierte UserId;
6. keine erwartete Vorgängerrevision.

Alles committet oder nichts. Der Revisionsgenerator wird erst nach allen
neutralen Vorbedingungen aufgerufen.

## 8. Stabile technische Wiederholung

Ein bereits committierter Anchor wird zuerst über seine Change-ID aufgelöst.

Stimmen Actor und im Membership-Fall Workspace exakt überein, liefert der
Adapter dieselbe resultierende Revision. Er erzeugt keine zweite Revision und
prüft aktuelle Authority nicht erneut.

Damit ist ein unklarer Commit-Ausgang auch dann auflösbar, wenn der Actor oder
seine Authority nach dem ursprünglichen Commit deaktiviert wurde.

Die Wiederverwendung derselben Change-ID mit anderem Actor oder Workspace ist
ein detailfreier Konflikt. Bestehende Fakten werden niemals überschrieben.

## 9. Konkurrenzordnung

PostgreSQL ordnet Authority-, Foundation-, Set-, Pointer-, Lifecycle- und
Recovery-Inventare unter einer gemeinsamen Schreibsperre.

Nach dem Warten wird dieselbe Change-ID erneut geprüft. Zwei konkurrierende
exakte Wiederholungen konvergieren dadurch auf dieselbe Revision.

Konkurrierende unterschiedliche Anchor-Entscheidungen für denselben Scope
haben genau einen Erfolg. Der spätere Versuch sieht das belegte Inventar und
endet neutral.

Unterschiedliche Workspace-Scopes bleiben fachlich unabhängig, auch wenn die
aktuelle konservative Tabellenordnung ihre Schreibvorgänge technisch
serialisieren kann.

## 10. Fehler- und Offenlegungsgrenzen

Neutrales `None` umfasst unbekannte oder inaktive Foundation, fehlende oder
inaktive Actor-Authority und einen nicht mehr verankerbaren Scope.

Change-ID-Wiederverwendung mit anderem Inhalt besitzt je Domäne einen
detailfreien Conflict-Typ.

Nicht unterstützte Datenbankdialekte, fehlendes Schema, unbrauchbare
Generatorergebnisse, Encoding-, Decoding-, Struktur-, Constraint- und
Transaktionsfehler werden je Domäne als detailfreie technische
Nichtverfügbarkeit vereinheitlicht.

Exceptions enthalten keine UserId, WorkspaceId, Change-ID, Revision,
Authority-Zeile, SQL-, Tabellen-, Constraint-, Treiber- oder DSN-Details.
`BaseException` bleibt ungefangen.

## 11. Sicherheitswirkung

Nach Verankerung existiert eine explizite aktuelle Authority-Set-Revision als
Vorbedingung späterer regulärer Lifecycle-Änderungen.

Der Slice verleiht jedoch keine neue Authority. Nur der schon aktuell
autorisierte Bootstrap-Manager kann den Bestand verankern.

Ein bereits vor Verankerung verlorener letzter wirksamer Bootstrap-Manager
kann diese Grenze nicht verwenden. Der Zustand bleibt wie in LQ-211
festgelegt ein manueller Identity-/Security-Lifecycle-Blocker.

Bootstrap wird durch Verankerung nicht wieder geöffnet. Seine bestehenden
History-Prüfungen bleiben unverändert und dauerhaft geschlossen.

## 12. Bewusst nicht enthalten

LQ-213 implementiert keine:

- reguläre Grant-, Deactivate- oder Reactivate-Entscheidung;
- Lockout-Prüfung für spätere Deaktivierung;
- Offline-Recovery;
- Nutzer-, Workspace-, Membership- oder Permission-Mutation;
- OIDC-Trust-Konfigurationsmutation;
- Migration, Seed oder Änderung bestehender Tabellen;
- Route, CLI, Settings-, Environment- oder Startup-Verdrahtung;
- automatische Ausführung während Login, Callback oder App-Start.

## 13. Nachweis

SQLite-Tests belegen vollständige statusgetreue Snapshots, unveränderte
Authority-Fakten, Workspace-Isolation, neutrale Ablehnung, späte
Generatorziehung, exakte Wiederholung nach Entzug, Konflikte und detailfreie
technische Nichtverfügbarkeit.

PostgreSQL-Integrationsnachweise prüfen die gemeinsame Konkurrenzordnung:
exakte globale Retries konvergieren, während unterschiedliche konkurrierende
Workspace-Anker genau eine Entscheidung erzeugen.

Die gesamte bestehende Suite bleibt unverändert ausführbar.

## 14. Nächster Slice

LQ-214 soll die reguläre autorisierte Authority-Lifecycle-Mutation für Grant,
Deactivate und Reactivate implementieren.

Sie muss die exakt aktuelle Set-Revision verlangen, Actor und Scope aus dem
System of Record binden, den letzten wirksamen Manager schützen, vollständige
neue Set-Revisionen erzeugen und exakte Change-ID-Retries sicher auflösen.
