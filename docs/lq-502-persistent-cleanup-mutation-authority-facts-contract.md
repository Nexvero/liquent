# LQ-502 — Persistent Cleanup Mutation Authority Facts Contract

## Ergebnis

LQ-502 definiert die persistenten Authority-Fakten, die vor einem autorisierten
LQ-500-Schreibadapter für Management-, Hold-, Recovery- und
Referenzrevisionen fehlen.

Der Slice implementiert noch keine Werte, Ports, Tabellen, Migration oder
Mutation.

## Vier Authority-Domänen

Jede Revisionsquelle besitzt eine eigene Mutationsauthority-Domäne:

- Cleanupmanagement-Lifecycle;
- Holdentscheidung;
- Recoveryentscheidung;
- Referenzentscheidung.

Keine Authority impliziert eine der anderen.

## Keine generische Adminrolle

LQ-502 führt weder Super-Admin noch frei benannte Capability ein.

Ein gemeinsamer technischer Algorithmus darf später intern wiederverwendet
werden, nicht aber IDs, Ports, Tabellen oder Entscheidungen vermischen.

Caller können keine Authority-Art als String auswählen.

## Scopegebundene Authority

Alle vier Authority-Domänen gelten ausschließlich für genau einen persistenten
Manifest-Handoff-Scope.

Eine Authority in Scope A darf keine Revision für ein Ziel aus Scope B
erzeugen.

Es gibt keine globale Fallbackauthority.

## Management-Mutationsauthority

Die Management-Mutationsauthority erlaubt ausschließlich append-only
Änderungen der Cleanupmanagementfähigkeit für Actoren im selben Handoffscope.

Die zu verwaltende Cleanupmanagementfähigkeit selbst erteilt diese
Lifecycleauthority nicht.

Ein aktiver Cleanupmanager kann sich ohne eigene Mutationsauthority weder
selbst reaktivieren noch weitere Manager vergeben.

## Hold-Mutationsauthority

Hold-Mutationsauthority erlaubt ausschließlich das Append autoritativer Clear-
oder Blocked-Holdrevisionen für Ziele im gebundenen Scope.

Sie erteilt keine Cleanupmanagement-, Recovery- oder Referenzauthority.

Ein Hold-Actor darf keinen physischen Cleanup starten.

## Recovery-Mutationsauthority

Recovery-Mutationsauthority erlaubt ausschließlich Recoveryrevisionen im
gebundenen Scope.

Journalterminalität oder Recoveryausführung allein verleiht diese Authority
nicht.

Hold- und Referenzentscheidungen bleiben getrennt.

## Referenz-Mutationsauthority

Referenz-Mutationsauthority erlaubt ausschließlich vollständige
Referenzentscheidungen für Ziele im gebundenen Scope.

Sie darf fehlende Hold- oder Recoveryfreigabe nicht ersetzen.

Eine Tabellen- oder Artefaktinspektion ist kein Authoritynachweis.

## Authority-Set-Revisionen

Jede Domäne und jeder Scope besitzt eine eigene aktuelle stabile
Authority-Set-Revision.

Die Revision bezeichnet den vollständigen Satz historischer Zuordnungen und
ihrer Active-/Inactive-Status nach einem Commit.

Sie ist intern erzeugt, repr-frei, nicht wiederverwendbar und nicht aus Inhalt,
Zeit oder User-ID abgeleitet.

## Vollständige Set-Mitglieder

Jede Set-Revision bindet alle für diese Domäne und diesen Scope bekannten
Authority-User samt Status.

Caller reichen nie einen vollständigen Authoritysatz ein.

Die kontrollierte Lifecyclegrenze erzeugt die neue vollständige Revision aus
einem eng begrenzten zielbezogenen Intent.

## Aktiver User und Scope

Wirksame Authority verlangt gleichzeitig:

- existierenden aktiven persistenten User;
- existierenden aktiven Handoffscope;
- aktive Zuordnung in der aktuellen Set-Revision der exakten Domäne.

Inactive in irgendeiner dieser drei Ebenen scheitert fail-closed.

## SessionPrincipal

Der `SessionPrincipal` identifiziert nur den authentifizierten Actor.

Die Schreibtransaktion muss dessen aktuellen Userstatus und Authority im
passenden Set aus dem System of Record lesen.

Principal, Session, Cookie oder CSRF-Nachweis enthalten keine Authority.

## Scopeauflösung für Management

Der Managementcommand trägt eine interne Scope-ID als Mutationsziel.

Der Store prüft genau die Management-Mutationsauthority des Principals in
diesem Scope.

Ein Caller kann keinen alternativen Authorityscope behaupten.

## Scopeauflösung für Zielquellen

Hold-, Recovery- und Referenzcommands tragen nur eine interne Directory-ID.

Der Store muss den Scope serverseitig über aktuelles Directory, vollständiges
Retired-Ziel und genau ein terminales Journal ableiten.

Ein Requestscope, Workspace oder Handle wird nicht akzeptiert.

## Durchgängige Zielbindung

Directory, Retired-Handle, Journalregistration, Journalergebnis und
Handoffscope müssen vollständig zusammengehören.

Erst danach darf im abgeleiteten Scope die quellenspezifische Authority geprüft
werden.

Inkonsistenz ist keine neutrale Scopewahl.

## Reguläre Lifecycle-Intents

Jede der vier Authority-Domänen kennt ausschließlich:

- Grant für einen noch nie zugeordneten aktiven User;
- Deactivate für eine aktuell aktive historische Zuordnung;
- Reactivate für eine aktuell inaktive historische Zuordnung.

Es gibt kein Upsert, Delete, Transfer oder Rollenupgrade.

## Erwartete Set-Revision

Jede reguläre Authorityänderung verlangt die exakt erwartete aktuelle
domänen- und scopegebundene Set-Revision.

Abweichung schreibt nichts und endet detailarm.

Last-write-wins und blinde Statusupdates sind ausgeschlossen.

## Lifecycle-Actor

Eine reguläre Authorityänderung darf nur ein aktuell wirksamer Holder genau
derselben Authority-Domäne im selben Scope ausführen.

Das ist kein Selbst-Grant: Ohne bereits wirksame Authority ist regulärer Grant
geschlossen.

Eine Authority aus einer anderen Domäne kann den Lifecycle nicht übernehmen.

## Schutz vor Lockout

Reguläre Deaktivierung darf im betroffenen Domänen-/Scope-Set niemals den
letzten aktuell wirksamen Authority-User entfernen.

Prüfung, Statusänderung und neue vollständige Set-Revision committen atomar.

Selbstdeaktivierung ist nur mit mindestens einem anderen wirksamen Holder
zulässig.

## Authority-Change-ID

Jede Verankerung und reguläre Grant-, Deactivate- oder Reactivate-Entscheidung
besitzt eine eigene domänenspezifische nichtwiederverwendbare Change-ID.

Ein exakter Retry liefert dieselbe Ergebnisrevision ohne zweite Mutation.

Wiederverwendung mit anderem Actor, Scope, Ziel, Intent oder Vorgänger ist
Konflikt.

## Initialer Bootstrap

Leere Authority-Historie autorisiert keinen regulären First Write.

Jede Domäne benötigt pro Scope eine eigene kontrollierte einmalige
Bootstrapgrenze für ihre erste Authority-Set-Revision.

Bootstrap darf keine Authority aus Membership, Research, Registry, Cleanup oder
einer Schwesterquelle ableiten.

## Bootstrap-Separation

Die vier Bootstrapentscheidungen bleiben getrennte persistente Fakten.

Sie dürfen denselben aktiven internen User binden, falls ein späterer
kontrollierter Betriebsentscheid dies ausdrücklich vorsieht; daraus entsteht
keine domänenübergreifende Authority.

LQ-502 entscheidet noch keinen Operatorinput oder Credentialmechanismus.

## Bootstrap schließt dauerhaft

Sobald für eine Domäne und einen Scope Authority-Historie existiert, bleibt ihre
Bootstrapgrenze dauerhaft geschlossen.

Deaktivierung aller durch User-Lifecycle unwirksam gewordenen Holder öffnet sie
nicht erneut.

Migration, Appstart und Deployment erzeugen keine Bootstrapfacts.

## Kontrollierte Offline-Recovery

Jede Domäne benötigt eine getrennte Offline-Recovery-Grenze für den Fall, dass
Historie existiert, aber kein Holder aktuell handeln kann.

Recovery darf ausschließlich einen im selben Domänen-/Scope-Set historisch
bereits autorisierten aktiven User reaktivieren.

Sie darf keinen neuen User auswählen oder Bootstrap wiederholen.

## Recovery-Bindung

Recovery verwendet eine eigene domänenspezifische Recovery-ID und die exakt
erwartete aktuelle oder letzte Set-Revision.

Entscheidung, Reaktivierung und neue Set-Revision committen atomar.

Exakter Retry bleibt möglich; abweichende ID-Wiederverwendung ist Konflikt.

## User-Lifecycle bleibt getrennt

Authority-Lifecycle und Recovery ändern niemals den Status eines Users oder
Handoffscopes.

Ist kein historisch autorisierter User aktiv, bleibt Recovery geschlossen.

Die Wiederaktivierung des Users gehört zur separaten Identity-Lifecycle-Grenze.

## Wirkung auf Revisionmutationen

Jede neue LQ-500-Revisionsmutation liest innerhalb ihrer Schreibentscheidung
die aktuelle Set-Revision und wirksame Authority erneut.

Ein committierter Authorityentzug sperrt alle später begonnenen Mutationen der
betroffenen Domäne und des Scopes.

Es gibt keinen positiven Authoritycache oder Grace-Boolean.

## Retry nach Entzug

Ein bereits committierter exakter technischer Retry derselben
Revisions-Change-ID darf vor erneuter aktueller Authorityprüfung aufgelöst
werden.

So bleibt ein unklarer Commit-Ausgang rekonstruierbar.

Ein neuer Intent nach Entzug bleibt gesperrt.

## Clearancecreation

Die vier Mutationsauthority-Sets erteilen nicht automatisch die fachliche
Cleanupmanagementfähigkeit für Clearancecreation.

Clearancecreation verlangt weiterhin die aktuelle positive LQ-496-
Managementrevision des Request-Actors und alle übrigen Clearancefacts.

Quelladministration und physische Wirkung bleiben getrennt.

## Neutrale Ablehnung

Unbekannter oder inaktiver Actor, User oder Scope, fehlende Authority, stale
Set-Revision, unzulässiger Übergang und Last-Holder-Schutz ergeben dieselbe
nichtoffenlegende fachliche Ablehnung.

Sie verrät weder Setbestand noch Zielstatus.

Der Vertrag benennt keinen neuen Exceptiontyp.

## Technische Unverfügbarkeit

Mehrdeutige Pointer, beschädigte Sets, unmögliche Sequenzen, Ziel-/Journal-
Divergenz und Transaktionsfehler bleiben detailfreie technische
Unverfügbarkeit.

SQL, Identifier, Authoritybestand und ursprüngliche Fehlerdetails verlassen die
Grenze nicht.

## Retention und Nichtwiederverwendung

Set-Revisionen, Mitglieder, Bootstrap-, Lifecycle- und Recoveryentscheidungen
bleiben mindestens so lange erhalten, wie aktuelle Authorityauflösung, Audit,
Retry oder Recovery sie benötigt.

IDs werden nicht gelöscht, neu zugewiesen oder domänenübergreifend adoptiert.

Physischer Cleanup verkürzt diese Untergrenze nicht.

## Keine Umsetzung in diesem Slice

LQ-502 ergänzt keine Domainklasse, Portsignatur, Tabelle, Migration, SQL,
Adapterimplementation, CLI, Route, Settings oder Verdrahtung.

Head und Migrationsanzahl bleiben `20260826_0037` und 37.

Es gibt keinen Bootstrap-, Grant-, Deactivate-, Reactivate- oder Recoverypfad.

## Nächster Slice

LQ-503 sollte die vier getrennten Authority-Set-, Lifecycle-, Bootstrap- und
Recoverywerte sowie die minimalen Lookup- und Mutationsports implementieren.

Persistenzfoundation, autorisierter Revisionsadapter und physischer Cleanup
folgen danach getrennt.
