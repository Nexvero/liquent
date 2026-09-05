# LQ-531 — Closed Supervisor Cleanup Retention Policy and Authority Values and Ports

## Ergebnis

LQ-531 implementiert geschlossene Policy-, Bootstrap-, Lifecycle-,
Authority- und Recoverywerte sowie minimale Ports für den LQ-530-Vertrag.

Der Slice implementiert keine Persistenz, Policyberechnung oder Operatorgrenze.

## Getrennte IDs

Bootstrap, Policychange, Authority-Set-Revision, Authoritychange und
Authority-Recovery besitzen fünf getrennte stabile ID-Typen.

Alle IDs sind nichtleer, repr-frei und nicht aus Actor, Dauer oder Zeit
abgeleitet.

Kein ID-Typ kann konstruktiv als anderer Operationstyp verwendet werden.

Die bestehende LQ-492-Policyrevision-ID bleibt der unveränderliche Inhaltstyp.

## Policyrevision

`ManifestHandoffSupervisorCleanupRetentionPolicyRevision` bindet bestehende
Policyrevision-ID, geschlossene Datenklasse, Mindestaufbewahrung und aware UTC
Erzeugungszeit.

Die Datenklasse ist konstruktiv ausschließlich
`supervisor_control_directory`.

Eine Revision enthält keinen Active-Boolean, Actor oder Authoritywert.

## Positive Dauer

Die Mindestaufbewahrung ist exakt ein `timedelta` größer null.

Mikrosekunden sind unzulässig, sodass die erste Semantik eindeutige ganze
Sekunden besitzt.

Integer, Float, String, null und nichtpositive Dauern werden abgelehnt.

Der Domainwert legt keine fachliche Defaultdauer fest.

## Aktive Projektion

`ActiveManifestHandoffSupervisorCleanupRetentionPolicy` bindet genau eine
Policyrevision und eine aware UTC Aktivierungszeit.

Aktivierung darf nicht vor Revisionserzeugung liegen.

Die Projektion ist ein read-only aktueller Wert und keine Mutation.

Abwesenheit einer aktiven Policy wird später neutral als `None` dargestellt.

## Authoritystatus

Authoritymember besitzen ausschließlich `active` oder `inactive`.

Der Lifecycleintent besitzt ausschließlich `grant`, `deactivate` oder
`reactivate`.

Es gibt keine Rolle, Permission, Membership oder freie Capabilityzeichenkette.

## Vollständige Authority-Menge

`ManifestHandoffSupervisorCleanupRetentionPolicyAuthoritySet` bindet eine
eigene Set-Revision und eine nichtleere frozenset-Menge eindeutiger Member.

Jede gültige Menge enthält mindestens einen aktiven Member.

Damit kann ein regulärer Lifecyclewert keinen konstruktiv leeren oder
vollständig inaktiven Erfolgswert darstellen.

Offline-Recovery bleibt für persistente Lockoutzustände separat.

## Initialer Bootstrapcommand

`BootstrapManifestHandoffSupervisorCleanupRetentionPolicy` trägt exakt
Bootstrap-ID, Ziel-User-ID und positive Mindestaufbewahrung.

Er trägt keinen Actorprincipal, keine caller-gelieferte Policyrevision,
Authorityrevision oder Disposition.

Die geschlossene Datenklasse ist implizit und nicht caller-wählbar.

## Bootstrapresultat

`BootstrappedManifestHandoffSupervisorCleanupRetentionPolicy` bindet denselben
Bootstrapcommand, die initial aktive Policy und die initiale Authority-Menge.

Die aktive Policy muss dieselbe Dauer tragen und der Ziel-User muss aktiver
Member der initialen Authority-Menge sein.

Der Wert erzwingt keine Persistenzreihenfolge; eine spätere Adaptergrenze muss
beides atomar schreiben.

Bootstrap erzeugt keine User- oder Membershipfakten.

## Policychange-Intent

Policychanges besitzen ausschließlich `replace` oder `deactivate`.

`replace` verlangt eine positive sekundengenaue Mindestaufbewahrung.

`deactivate` verlangt ausdrücklich `minimum_retention=None`.

Dadurch kann eine Deaktivierung keine versteckte Ersatzdauer tragen.

## Erwartete Policyrevision

`ChangeManifestHandoffSupervisorCleanupRetentionPolicy` bindet Change-ID,
optionale erwartete aktuell aktive Policyrevision, Intent und optionale Dauer.

Eine vorhandene aktive Policy verlangt später ihre exakte erwartete Revision.

`None` ist nur die geschlossene Erwartung, dass aktuell keine Policy aktiv ist;
es ist kein Wildcard oder Ignorewert.

Der Caller liefert keine neue Policyrevision-ID.

## Policychange-Ergebnis

`ChangedManifestHandoffSupervisorCleanupRetentionPolicy` bindet denselben
Changecommand und optional eine aktive Policyprojektion.

Replace verlangt eine neue Revision mit exakt derselben Commanddauer;
Deactivate verlangt weiterhin keine aktive Projektion.

`None` repräsentiert den erfolgreichen geschlossenen Deaktivierungszustand.

Der Wert erzeugt keine Evaluation, Decision oder Retentionoperation.

## Authority-Lifecyclecommand

`ChangeManifestHandoffSupervisorCleanupRetentionPolicyAuthority` trägt eigene
Change-ID, Ziel-User-ID, erwartete Authority-Set-Revision und geschlossenen
Intent.

Der Actor bleibt außerhalb im `SessionPrincipal` der Mutationsmethode.

Der Command enthält keine Policyrevision oder Mindestdauer.

## Offline-Recoverycommand

`RecoverManifestHandoffSupervisorCleanupRetentionPolicyAuthority` trägt
Recovery-ID, historisch bekannte Ziel-User-ID und erwartete Set-Revision.

Er enthält keinen `SessionPrincipal`, keine neue Person und keinen freien
Status.

Die persistente Recoveryimplementation muss die historischen und
Lockoutvoraussetzungen aus LQ-530 später erneut prüfen.

## Detailfreier Conflict

`ManifestHandoffSupervisorCleanupRetentionPolicyConflict` ist feldlos.

Er vereinheitlicht stale, denied, reused, lockout oder inkompatible fachliche
Mutationen ohne interne Ursache.

Er ist kein technischer Exceptiontyp.

## Aktiver Policylookup

`ManifestHandoffSupervisorCleanupRetentionPolicyLookup` besitzt genau
`resolve_active_cleanup_retention_policy` ohne Parameter.

Die Datenklasse ist durch den Port fest gebunden und nicht caller-wählbar.

Der Port liefert genau eine aktive Projektion oder neutral `None`.

Er besitzt keine History-, List-, Search- oder Mutationsmethode.

## Policyadministrationsport

`ManifestHandoffSupervisorCleanupRetentionPolicyAdministration` besitzt genau
Bootstrap und reguläre Policyänderung.

Bootstrap akzeptiert keinen Principal; seine owner-kontrollierte
Prozessgrenze folgt separat.

Reguläre Änderung akzeptiert einen `SessionPrincipal` nur als Actoridentität
und den geschlossenen Changecommand.

Beide Methoden liefern Erfolg, detailfreien Conflict oder neutral `None`.

## Authorityadministrationsport

`ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityAdministration`
besitzt aktuelle Permit-Auflösung, regulären Authority-Lifecycle und
Offline-Recovery.

Permit akzeptiert ausschließlich `SessionPrincipal` und gibt einen internen
aktuellen booleschen Adapterentscheid zurück; kein Caller liefert diesen Wert.

Lifecycle akzeptiert Principal und Authoritycommand.

Recovery akzeptiert ausschließlich den Recoverycommand ohne Principal.

## Warum Permit bool sein darf

Der boolesche Permitwert ist ein Ergebnis des aktuellen System-of-Record-
Lookups innerhalb der internen Portgrenze.

Er ist kein Feld eines Requests, kein persistierter Rollenwert und keine
öffentliche Allowbehauptung.

Die spätere Policyadministration muss Authority in derselben Mutation erneut
prüfen und darf keinen früheren Permitwert cachen.

## Monotone Dauer bleibt Adapterregel

Der Domaincommand kann eine positive Ersatzdauer ausdrücken.

Die spätere persistente Mutation muss sie gegen die aktuelle beziehungsweise
letzte Policyrevision prüfen und reguläre Verkürzung detailfrei ablehnen.

Diese system-of-record-Abhängigkeit wird nicht durch einen isolierten
Commandkonstruktor vorgetäuscht.

## Keine Evaluationsemantik im Adminmodul

Das Modul berechnet weder `retired_at + minimum_retention` noch `retain` oder
`eligible`.

Es importiert keinen Directory-, Filesystem- oder Clockadapter.

Die read-only Evaluationimplementation folgt nach Persistenz separat.

## Keine technische Exception

Validierungsfehler nennen keine konkreten IDs, User oder Dauern.

Technische Persistenzfehler bleiben später an der bestehenden
`ManifestHandoffRegistryUnavailable`-Grenze.

LQ-531 benennt keinen neuen technischen Exceptiontyp.

## Keine Persistenz oder Wirkung

Der Slice ergänzt keine Tabelle, SQL oder Migration.

Es gibt keinen Policy-, Authority-, Bootstrap-, Lifecycle-, Recovery- oder
Evaluationsadapter.

Keine Decision, Retentionoperation, Clearance, Retirement- oder Dateiwirkung
wird erzeugt.

## Kein Wiring

Operator, Entry Point, HTTP, Appfactory, Compose, Worker, Scheduler, Runbook
und Deployment bleiben unverändert.

Das Paketinventar bleibt bei 63 Entry Points und 68 Operatorfiles.

Head bleibt `20260826_0041` mit 41 linearen Migrationen.

## Tests

Fokussierte Tests prüfen getrennte repr-freie IDs, positive sekundengenaue
Dauer, geschlossene Datenklasse, aktive Projektion, Authority-Mengeninvarianten,
Bootstrap, replace/deactivate-Matrix, getrennte Lifecycle-/Recoverycommands,
feldlosen Conflict und exakte minimale Ports.

## Nächster Slice

LQ-532 definiert die persistente Policy-, Aktivierungs-, Change-, Authority-
Set-, Bootstrap- und Recoveryfoundation.

Adapter, Evaluation, Operator, Retirement und Deployment bleiben getrennt.
