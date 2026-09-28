# LQ-495 — Current Supervisor Control-Directory Cleanup Clearance Resolution Contract

## Ergebnis

LQ-495 definiert die aktuelle fail-closed Auflösung aller fachlichen
Voraussetzungen vor dem Start oder der Fortsetzung eines physischen
Supervisor-Control-Directory-Cleanups.

Der Slice implementiert noch keine Werte, Ports, Persistenz oder Dateioperation.

## Keine einzelne Allowentscheidung

Cleanupfreigabe ist kein Boolean und keine Rolle.

Sie entsteht nur aus mehreren unabhängigen aktuellen System-of-Record-Fakten,
die auf denselben Actor, dasselbe Directory und denselben Handoffscope gebunden
sind.

Kein einzelner Fakt darf einen fehlenden anderen ersetzen.

## Requestgrenze

Ausgangspunkt ist ausschließlich der geschlossene LQ-492-Cleanuprequest aus
Attempt-ID, Actor-User-ID und interner Directory-ID.

Der Request enthält weder Handle, Scope, Workspace, Leaf, Root, Retention-,
Hold-, Recovery- noch Authoritybehauptung.

Alle Zielfakten werden serverseitig aufgelöst.

## Actoridentität

Die Actor-User-ID identifiziert den handelnden internen Nutzer.

Ein `SessionPrincipal` kann an einer vorgelagerten Grenze diese ID liefern,
erteilt aber selbst keine Cleanupauthority.

Unbekannte oder inaktive Actoren scheitern fail-closed.

## Directory als Startpunkt

Die Resolvercomposition liest den aktuellen vollständigen Lifecycle anhand der
Directory-ID.

Nur ein exakt rekonstruierter Retired-Wert darf weitere Prüfungen öffnen.

Reserved, Active, beschädigte oder fremde Bindungen sind nicht cleanupfähig.

## Directory zu Handle

Das Handle stammt ausschließlich aus dem aktuellen Retired-Wert.

Caller können kein Handle auswählen oder ersetzen.

Directory-ID, Handle und Leaf müssen mit der persistenten Registrybindung
übereinstimmen.

## Handle zu Journal

Für das persistierte Handle werden Writer- und Recoveryjournal aktuell
inspiziert.

Genau einer der beiden geschlossenen Views muss vorhanden sein.

Mehrdeutigkeit oder fehlender Journalbestand bei bekanntem Directory ist
technische Divergenz, nicht neutrale Abwesenheit.

## Terminaler Journalfakt

Der eine Journalview muss `TERMINAL_OBSERVED`, Terminal-Observation-ID und ein
geschlossenes Ergebnis desselben Handles tragen.

Prepare, Running, Termination-Requested oder bloße Prozessabwesenheit genügen
nicht.

Retired ersetzt diese erneute Journalprüfung nicht.

## Journal zu Handoffscope

Der Zielscope wird ausschließlich aus
`journal.registration.process_request.binding.scope_id` gewonnen.

Writer und Recovery verwenden dieselbe geschlossene
`ManifestHandoffScopeBinding`-Form.

Ein Caller-supplied Scope oder Workspace wird nicht akzeptiert.

## Scopekonsistenz

Der Scope muss weiterhin als persistenter aktiver Manifest-Handoff-Scope
existieren.

Directoryhandle, Journalregistration, ursprünglicher Claim und Scopebinding
müssen durchgängig zusammengehören.

Eine gleichnamige oder vom Actor verwaltete andere Scope-ID ist kein Ersatz.

## Eigene Cleanupmanagementfähigkeit

Cleanup benötigt eine eigene aktive Managementfähigkeit für genau Actor und
den aus dem Journal aufgelösten Handoffscope.

Diese Fähigkeit ist von normaler Handoffreservation, Ausführung, Recovery,
Research und Onboarding getrennt.

Sie darf später nur durch eine eigene autorisierte Lifecyclegrenze vergeben
oder entzogen werden.

## Bestehende Registryauthority reicht nicht

`manifest_handoff_registry_authorities` erlaubt reservierungsbezogene
Handoffentscheidungen, aber keine Retentionlöschung.

Sie wird nicht stillschweigend als Cleanupmanagement interpretiert.

Ebenso reicht die bestehende Recoveryauthority nicht.

## Membership und Research reichen nicht

Ordentliche Workspace-Membership, `research:read` und `research:write`
erteilen keine Cleanupfähigkeit.

Eine Admin- oder Owner-Rollenbezeichnung aus einem Callerrequest ist keine
System-of-Record-Entscheidung.

LQ-495 erweitert die bestehende Research-Permission-Aufzählung nicht.

## Onboardingmanagement reicht nicht

Workspace-Onboardingmanagement erlaubt Identitätsaufnahmeentscheidungen, nicht
das Entfernen von Supervisorartefakten.

Bootstrap-, Admission- oder Sessionfakten werden nicht als Cleanupauthority
umgedeutet.

Capabilityseparation bleibt ausdrücklich erhalten.

## Aktuelle Retentionentscheidung

Der Resolver liest die höchste vollständige LQ-494-Decision für dieselbe
Directory-ID erneut.

Sie muss exakt denselben aktuellen Retired-Wert tragen und `eligible` sein.

Eine ältere Eligible-Decision unter einer neueren Retain-Decision ist
wirkungslos.

## Policyrevision

Die Decision muss eine weiterhin gültige autoritative Policyrevision binden.

Der Resolver berechnet keine Frist aus `retired_at`, Dateizeit oder Alter.

Eine unbekannte, ersetzte oder unlesbare Policyrevision bleibt fail-closed.

## Holdquelle

Eine autoritative Holdquelle muss für genau Scope, Directory, Handle und
betroffene Control-Artefaktklasse aktuell No-Hold bestätigen.

Legal-, Incident-, Audit- und Investigation-Holds werden gemeinsam
berücksichtigt.

Fehlende Holdinformation ist kein No-Hold-Nachweis.

## Recoveryquelle

Eine autoritative Recoveryquelle muss bestätigen, dass keine offene
Wiederherstellung, Reconciliation, Incidentanalyse oder forensische Nutzung
die physischen Bytes benötigt.

Terminalität allein schließt diese Vorgänge nicht aus.

Unbekannte oder rückläufige Recoveryfakten sperren Cleanup.

## Referenzquelle

Eine autoritative Referenzentscheidung muss Journal, Runtimebinding,
Gatebinding, Control-Artefaktmetadaten, Claims, Audits und operative Handoffs
gemeinsam berücksichtigen.

Persistente Metadaten können dauerhaft erhalten bleiben, während physische
Bytes nur nach expliziter Freigabe entbehrlich werden.

Tabellenexistenz allein ist weder Sperre noch Freigabe.

## Artefaktklassenspezifische Freigabe

Ready, Release-Token, Release-Consumed und Terminal-Envelope besitzen getrennte
fachliche Rollen.

Eine gemeinsame Cleanupclearance muss alle tatsächlich vorhandenen und alle
persistiert erwarteten Rollen abdecken.

Teilfreigabe autorisiert keine teilweise Löschung.

## Aktuelle physische Vorprüfung

Nach fachlicher Clearance muss eine read-only physische Vorprüfung Root, Leaf
und vollständige geschlossene Inventur aktuell belegen.

Diese Prüfung liefert keine Dateinamen oder Pfade an den Caller.

Unsicherer Bestand bleibt Konflikt oder technische Unverfügbarkeit.

## Atomare Bindungsanforderung

Actorstatus, Scopeaktivität, Cleanupmanagement, aktuelle Decision und die
persistierbaren Clearance-Revisionen müssen mit dem Attemptstart in einer
serialisierbaren Entscheidung gebunden werden.

Ein Check-then-act über unabhängige veraltbare Reads genügt nicht.

In-Process-Locks oder ein früheres Preflightresultat ersetzen diese Bindung
nicht.

## Externe Systeme of Record

Falls Hold-, Recovery- oder Referenzquellen nicht in derselben Transaktion
liegen, müssen sie stabile revisionsgebundene Entscheidungen liefern.

Der Attemptstart muss deren aktuelle Gültigkeit autoritativ prüfen und die
verwendeten Revisionen dauerhaft binden.

Ein caller-geliefertes Snapshotobjekt oder signalloser Cache ist unzulässig.

## Lücke in Revision 0035

Revision 0035 bindet Attempt, Actor, Directory und Retention-Decision, aber
noch keine Cleanupmanagement-, Hold-, Recovery- oder Referenzrevision.

Darum reicht `start_cleanup_attempt` aus LQ-494 allein nicht als
Production-Cleanupfreigabe.

Vor physischer Wirkung ist eine additive Clearancefoundation erforderlich.

## Widerruf vor Attemptstart

Inaktiver Actor, inaktiver Scope, entzogene Cleanupmanagementfähigkeit, neue
Retain-Decision, neuer Hold oder Recovery-/Referenzregression sperren einen
neuen Attempt.

Die Ablehnung bleibt fachlich detailfrei.

Es wird keine Attemptzeile und keine Dateiwirkung erzeugt.

## Widerruf nach Started vor Wirkung

`started` behauptet gemäß LQ-494 noch keine physische Mutation.

Vor der ersten Dateioperation müssen alle aktuellen Voraussetzungen erneut
geprüft werden.

Widerruf sperrt die Fortsetzung; der persistierte Started-Fakt darf nicht als
stale Authority dienen.

## Widerruf während einer Mutationsfolge

Vor jeder weiteren irreversiblen Namensmutation müssen Clearancebindung und
physische Fakten gemäß dem späteren Mutationsbudget erneut geprüft werden.

Wird ein Widerruf oder Hold erkennbar, stoppen weitere Wirkungen.

Bereits mögliche Wirkung wird nicht als sicher rückgängig behauptet.

## Exact Retry ohne neue Wirkung

Ein Retry darf bereits persistierte Completed- oder Reconciled-Ergebnisse
ohne neue Cleanupauthority rekonstruieren.

Das ist reine Idempotenz und erzeugt keine weitere Dateiwirkung.

Cross-Attempt-, Actor- oder Directorybindung bleibt Konflikt.

## Started-Retry

Ein exakter Retry eines Started-Attempts darf nur die ursprüngliche Bindung
rekonstruieren.

Für eine noch ausstehende physische Wirkung muss er sämtliche aktuellen
Clearances erneut auflösen.

Er darf weder die frühere Eligible-Decision noch frühere Authority als
Fortsetzungsrecht verwenden.

## Outcome Unknown

`outcome_unknown` erlaubt ausschließlich read-only Reconciliation derselben
Attempt- und Directorybindung.

Es autorisiert keinen zweiten Cleanupversuch und keine verbleibende
best-effort Mutation.

Authorityentzug verhindert nicht die sichere Zustandsfeststellung, erteilt
aber keine neue Wirkung.

## Reconciliation Present

Ein reconciliertes `present` bedeutet nur, dass der gebundene physische Bestand
aktuell noch vorhanden ist.

Eine spätere Löschung benötigt einen neuen Attempt und vollständig neue
aktuelle Clearance.

Der alte Attempt wird nicht zurück auf Started gesetzt.

## Reconciliation Absent

Ein reconciliertes `absent` bestätigt physische Abwesenheit für den alten
Attempt, löscht aber keine Registry-, Decision- oder Clearancefakten.

Es erteilt keine ID-, Handle- oder Leafwiederverwendung.

Evidence-Retention bleibt separat erhalten.

## Neutrale Abwesenheit

Nur eine vor erwarteter Bindung autoritativ unbekannte Directory-ID oder
Attempt-ID darf neutral sein.

Ein bekannter Retired-Bestand ohne Decision, Authority, Holdquelle,
Recoveryquelle oder Referenzclearance ist keine neutrale Abwesenheit.

Diese Fälle werden detailfrei abgelehnt oder technisch gesperrt.

## Fachliche Ablehnung

Inactive, Retain, Hold, Recoverybedarf, Referenzbedarf, fehlende
Cleanupmanagementfähigkeit und nichtterminale Bindung werden nach außen
einheitlich detailfrei abgelehnt.

Der Ausgang verrät nicht, welche Voraussetzung fehlte.

Es werden keine Policy-, Hold- oder Capabilitynamen ausgegeben.

## Technische Unverfügbarkeit

Unlesbare, widersprüchliche, mehrdeutige oder strukturell beschädigte Quellen
bleiben davon getrennte detailfreie technische Unverfügbarkeit.

LQ-495 benennt keinen neuen Exceptiontyp.

Technische Fehler erzeugen keinen stale Fallback.

## Keine lokale Policyberechnung

Der Resolver entscheidet nicht anhand von Uhrzeit, Dateialter, Kosten,
Speicherfüllstand oder heuristischer Inaktivität.

Er erzeugt keine Retention-, No-Hold-, Recovery- oder Referenzentscheidung.

Er konsumiert nur autoritative aktuelle Fakten.

## Keine Implementation

LQ-495 ergänzt keine Klasse, Domainwerte, Ports, Tabelle, SQL, Migration,
Authorityzuordnung, Retentionquelle, Holdsystem, Resolver oder Dateioperation.

Head bleibt `20260825_0035` mit 35 linearen Migrationen.

Es gibt keinen Seed, Backfill oder Bootstrap.

## Kein Wiring

Service-Facade, Settings, Appfactory, CLI, Route, Operator, Compose,
Environment und Deployment bleiben unverändert.

Productioncleanup bleibt geschlossen.

## Tests

Fokussierte Vertragsprüfungen belegen Actor-/Directory-/Handle-/Journal-/Scope-
Ableitung, separate Cleanupmanagementfähigkeit, aktuelle Eligible-/Policy-,
No-Hold-, Recovery- und Referenzclearance, atomare revisionsgebundene
Attemptbindung, Revocation vor Wirkung, read-only Unknown-Reconciliation und
die offene 0035-Clearancefoundation.

## Nächster Slice

LQ-496 sollte geschlossene Cleanupmanagement-, Hold-, Recovery-, Referenz- und
aggregierte Clearancewerte sowie minimale Resolverports definieren.

Persistente Clearancefoundation und physischer Cleanup folgen getrennt.
