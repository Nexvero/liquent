# LQ-222 — Lifecycle Management Authority Sets

## Ergebnis

LQ-222 implementiert Verankerung und regulären Lifecycle für die beiden in
LQ-219 getrennt entschiedenen globalen Management-Authorities:

- User-Lifecycle-Management;
- Workspace-Lifecycle-Management.

Beide Domänen erhalten eigene stabile Set-Revisionen, Change-IDs, persistente
Inventare und Ports. Es entsteht keine gemeinsame Administratorrolle und keine
domänenübergreifende Authority.

Der Slice erzeugt, deaktiviert oder reaktiviert noch keinen Nutzer oder
Workspace. Er verwaltet ausschließlich, wer spätere Lifecycle-Entscheidungen
der jeweiligen Domäne treffen darf.

## Trennung von Status- und Authority-Revisionen

Die LQ-220-Revisionen beschreiben den vollständigen aktiven oder inaktiven
Nutzer- beziehungsweise Workspacebestand.

LQ-222 führt davon getrennte Authority-Set-Revisionen ein. Sie beschreiben den
vollständigen aktiven oder inaktiven Managerbestand einer globalen
Lifecycle-Authority-Domäne.

Eine Nutzerstatusrevision darf deshalb niemals als User-Lifecycle-Authority-
Revision verwendet werden. Dasselbe gilt für Workspace-Status und Workspace-
Lifecycle-Authority.

Current-Pointer, Change-Entscheidungen und historische Mitglieder bleiben für
alle vier Revisionsdomänen strukturell getrennt.

## Stabile interne Identitäten

Die User-Domäne erhält:

- `UserLifecycleAuthoritySetRevisionId`;
- `UserLifecycleAuthorityChangeId`.

Die Workspace-Domäne erhält:

- `WorkspaceLifecycleAuthoritySetRevisionId`;
- `WorkspaceLifecycleAuthorityChangeId`.

Alle Typen sind frozen, slotted und repr-frei. Sie akzeptieren nur nichtleere
exakte Strings und enthalten keine Rolle, Person, Authority-Entscheidung oder
Statusbehauptung.

Der sichere Materialgenerator zieht jede ID unabhängig mit mindestens 32 Byte
Entropie. Keine ID wird aus Actor, Ziel, Vorgängerrevision, Zeit oder Inhalt
abgeleitet.

## Additive Persistenz

Revision `20260813_0015` ergänzt für jede Domäne vier leere Tabellen:

- unveränderliche vollständige Authority-Set-Revisionen;
- Mitglieder jeder Revision mit active/inactive;
- einen globalen Current-Pointer;
- immutable Anchor- und Lifecycle-Change-Entscheidungen.

Die Migration verändert keine bestehende Lifecycle-Authority. Sie erzeugt
keine Revision, keinen Pointer, keine Change-Entscheidung und keinen Seed.

Die durch LQ-221 vorhandenen ersten Authority-Zeilen bleiben unverankert, bis
ein aktuell autorisierter Actor die jeweilige Anchor-Grenze explizit nutzt.

## Zwei getrennte Ports

Jede Domäne besitzt einen eigenen Anchor-Port und einen eigenen regulären
Lifecycle-Store.

Die User-Domäne akzeptiert ausschließlich User-Domänen-IDs und -Revisionen.
Die Workspace-Domäne akzeptiert ausschließlich Workspace-Domänen-IDs und
-Revisionen.

Ein intern geteilter Algorithmus ändert diese öffentliche Trennung nicht. Er
arbeitet nur mit fest eingebauten Tabellenkonfigurationen; Caller können keine
Tabelle, Authority-Art oder Capability-Bezeichnung wählen.

## Kontrollierte Verankerung

Anchor verlangt eine domänenspezifische Change-ID und einen
`SessionPrincipal`. Der Principal identifiziert nur den Actor.

Die persistente Grenze prüft atomar:

- Actor existiert und ist aktiv;
- Actor besitzt aktuell aktive Authority exakt derselben Domäne;
- Authority-Inventar ist vorhanden;
- Set-Revision, Current-Pointer und Change-Inventar sind noch leer.

Erfolg schreibt den vollständigen aktuellen Authority-Bestand unverändert in
die erste Set-Revision, setzt den Current-Pointer und speichert eine immutable
`anchor`-Entscheidung.

Anchor verleiht, entzieht oder reaktiviert keine Authority. Fehlende aktuelle
Authority, leerer oder bereits verankerter Bestand endet neutral.

## Reguläre Übergänge

Die regulären Stores kennen genau:

- `GRANT` für einen noch nie enthaltenen aktiven Zielnutzer;
- `DEACTIVATE` für eine aktuell aktive historische Zuordnung;
- `REACTIVATE` für eine aktuell inaktive historische Zuordnung.

Grant ist kein Upsert. Eine inaktive historische Zuordnung verlangt
`REACTIVATE`; ein aktiver Bestand kann nur als exakter Retry derselben
Change-ID aufgelöst werden.

Es gibt kein Delete, Rollenupgrade, Transfer durch Umdeutung oder implizite
Vergabe aus Onboarding, Membership, Trust oder Session.

## Aktuelle Autorisierung

Für jede neue Change-ID prüft dieselbe Schreibtransaktion:

- authentifizierter Actor ist aktuell aktiv;
- Zielnutzer ist aktuell aktiv;
- Actor besitzt aktuell die aktive Authority derselben Domäne;
- erwartete Set-Revision entspricht exakt dem Current-Pointer;
- Zielübergang ist für den aktuellen Authority-Bestand zulässig.

Der Caller kann keinen Allow-Wert, keine Rolle, keinen Authority-Snapshot und
keinen alternativen Actor übergeben.

Entzug einer Authority wirkt auf jede später neu begonnene Entscheidung. Es
gibt keinen Authority-Cache oder Session-Snapshot.

## Vollständige neue Set-Revision

Erfolg erzeugt eine intern generierte neue Revision des vollständigen
Authority-Sets.

Alle bisherigen Zuordnungen und Status werden übernommen; nur der explizite
Zielübergang ändert genau einen Status oder ergänzt beim Grant genau einen
neuen aktiven Fakt.

Authority-Zeile, vollständige neue Revision, Current-Pointer und immutable
Change-Entscheidung committen gemeinsam oder gar nicht.

Der Caller liefert niemals einen vollständigen Manager-Satz und kann keine
anderen Mitglieder aus der Revision entfernen.

## Letzter-Manager-Schutz

Deactivate ist nur erfolgreich, wenn danach mindestens eine aktive Authority
mit aktuell aktivem Nutzer in derselben Domäne verbleibt.

Die Prüfung erfolgt aus dem vollständigen gesperrten Inventory in derselben
Transaktion wie Statusänderung und neue Revision.

Selbstdeaktivierung ist zulässig, wenn ein anderer wirksamer Manager verbleibt.
Die Deaktivierung des letzten wirksamen Managers wird neutral abgelehnt und
zieht keine Revisions-ID.

Eine Nutzerdeaktivierung bleibt wegen des LQ-219-Drain-Vertrags ohnehin
gesperrt, solange irgendeine aktive Lifecycle-Authority besteht.

## Idempotenz und Konflikt

Eine exakte Wiederholung derselben Change-ID mit identischem Actor, Ziel,
Intent und erwarteter Revision liefert das bereits committete Ergebnis.

Dieser Retry wird vor aktueller Actor- und Authority-Prüfung aufgelöst. Damit
bleibt ein unklarer Commit-Ausgang auch nach späterem Authority-Entzug sicher
auflösbar.

Wiederverwendung derselben Change-ID mit abweichendem Inhalt endet als
detailfreier Konflikt. Sie überschreibt keine Entscheidung und erzeugt keine
zweite Revision.

## Konkurrenz und Fail-closed-Verhalten

PostgreSQL sperrt pro Entscheidung Nutzer-, exakte Authority-, Revisions-,
Member-, Current- und Change-Tabellen gemeinsam.

Konkurrierende Änderungen gegen dieselbe erwartete Revision erhalten dadurch
eine Reihenfolge. Nach dem ersten Commit ist die zweite erwartete Revision
veraltet und wird neutral abgelehnt.

Unbekannter oder inaktiver Actor oder Zielnutzer, fehlende oder inaktive
Authority, stale Revision, unzulässiger Übergang und letzter-Manager-Schutz
enden ohne Bestandsdetails neutral.

Abweichende Change-ID-Wiederverwendung bleibt ein detailfreier Konflikt.
Datenbank-, Struktur-, Encoding-, Generator-, Transaktions- und Commitfehler
bleiben getrennte detailfreie technische Nichtverfügbarkeit.

## Nachweise

Die neuen Tests belegen für beide Domänen:

- leere Foundation nach Migration;
- explizite Verankerung des vorhandenen ersten Managers;
- Grant, Deactivate und Reactivate als vollständige Revisionen;
- aktuelle persistente Authority-Zeilen nach allen Übergängen;
- getrennte Revisions- und Change-Inventare;
- neutralen letzter-Manager-Schutz;
- neutrale Ablehnung stale erwarteter Revisionen;
- exakten Retry nach späterem Entzug;
- Konflikt bei abweichender Wiederverwendung.

Die bestehenden Tests der read-only Authority-Lookups bleiben maßgeblich für
die Wirkung committierten Entzugs auf spätere fachliche Entscheidungen.

Die Initial-Bootstrap-Recovery wurde auf die neuen Inventare erweitert. Sobald
eine Authority-Set-Revision, ein Pointer oder eine Change-Entscheidung
existiert, darf sie den Bestand nicht mehr als unveränderten Bootstrap
rekonstruieren.

## Bewusst nicht enthalten

- keine Nutzer- oder Workspace-Anlage, Deaktivierung oder Reaktivierung;
- keine Drain-Prüfung von Session, Admission, Membership oder Authority;
- keine Authority-Recovery nach vollständigem Lockout;
- keine Operator-CLI, Request-/Resultatdatei oder Runbook;
- keine HTTP-Route, Settings-, Startup- oder Runtime-Verdrahtung;
- keine Änderung an OIDC-Trust-, Membership- oder Research-Authorities;
- keine generische Admin-Rolle oder domänenübergreifende Mutation.

## Nächster Schritt

LQ-223 sollte die reguläre autorisierte User-Lifecycle-Mutation implementieren:
Create mit intern erzeugter stabiler UserId sowie drain-gebundenes Deactivate
und explizites Reactivate gegen die vollständige aktuelle Nutzerrevision.

Workspace-Lifecycle-Mutation bleibt anschließend ein eigener Slice, damit die
atomare erste Onboarding-Authority und terminale Deaktivierung getrennt
nachgewiesen werden können.
