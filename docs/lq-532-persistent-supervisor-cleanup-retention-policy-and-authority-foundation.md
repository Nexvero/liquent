# LQ-532 — Persistent Supervisor Cleanup Retention Policy and Authority Foundation

## Ergebnis

LQ-532 ergänzt die leere persistente Foundation für die in LQ-530 und LQ-531
geschlossene Retention-Policy und ihre getrennte Administrationsauthority.

Revision `20260826_0042` folgt linear auf `20260826_0041`.

Der Slice implementiert keinen Adapter, keinen Operator und keine Wirkung.

## Geschlossene Datenklasse

Alle neuen Fakten sind ausschließlich an
`supervisor_control_directory` gebunden.

Die Datenklasse ist kein frei wählbarer Namespace und keine Capability.

Constraints weisen andere Werte bereits an der Persistenzgrenze zurück.

## Immutable Policyrevisionen

`mh_supervisor_cleanup_retention_policy_revisions` speichert eine stabile,
nichtleere Revision-ID, Datenklasse, positive Mindestaufbewahrung in ganzen
Sekunden und Erzeugungszeit.

Die Revision enthält keinen Active-Boolean, Actor und Authoritystatus.

Eine gespeicherte Revision wird nicht überschrieben oder wiederverwendet.

Die Foundation setzt keine fachliche Defaultdauer und keinen Maximalwert.

Der positive `BigInteger`-Wert bildet nur die untere Persistenzgrenze ab.

## Aktive Policyprojektion

`mh_supervisor_cleanup_retention_policy_active` hält durch den
Datenklassen-Primärschlüssel höchstens eine aktive Policyrevision.

Die zusammengesetzte Fremdschlüsselbindung verhindert eine Revision aus einer
anderen Datenklasse.

Abwesenheit der Singletonzeile bedeutet später neutral keine aktive Policy.

Die Tabelle ist eine austauschbare aktuelle Projektion, keine History.

## Immutable Policychanges

`mh_supervisor_cleanup_retention_policy_changes` hält eine eigene stabile
Change-ID, Actor, Erwartung, Ergebnis, Intent, optionale Dauer und Zeitpunkt.

`replace` verlangt Ergebnisrevision und positive Dauer.

`deactivate` verlangt eine erwartete Revision und verbietet Ergebnis und Dauer.

Eine null Erwartung bei `replace` bedeutet ausschließlich erwartete Abwesenheit
einer aktiven Policy und niemals Wildcard-Semantik.

Actor und Revisionen sind an Facts des System of Record gebunden.

Die Foundation entscheidet noch keine Autorisierung oder Monotonie.

## Vollständige Authority-Set-Historie

`mh_supervisor_cleanup_retention_policy_authority_sets` speichert immutable
Set-Revisionen mit positiver, pro Datenklasse eindeutiger Sequenz.

`mh_supervisor_cleanup_retention_policy_authority_members` speichert die
vollständigen Member jeder Revision.

Jeder Member bindet einen bestehenden internen User und ausschließlich
`active` oder `inactive`.

Eine User-ID wird innerhalb derselben Set-Revision höchstens einmal geführt.

Die Migration seedet keine erste Menge und errät keine Person.

Die konstruktive Regel mindestens eines aktiven Members bleibt Adapterpflicht,
weil sie nicht als einfache zeilenlokale Constraint ausdrückbar ist.

## Aktuelle Authorityprojektion

`mh_supervisor_cleanup_retention_policy_authority_current` hält höchstens eine
aktuelle Set-Revision für die geschlossene Datenklasse.

Der Fremdschlüssel bindet Revision und Datenklasse gemeinsam.

Abwesenheit ist kein Permit und muss später fail-closed wirken.

Ein späterer Lookup muss die aktuelle Projektion bei jeder Entscheidung neu
lesen; die Foundation führt keinen positiven Cache ein.

## Immutable Authoritychanges

`mh_supervisor_cleanup_retention_policy_authority_changes` speichert eine
eigene Change-ID, Actor, Ziel-User, erwartete und resultierende Set-Revision,
geschlossenen Intent und Zeitpunkt.

Zulässig sind ausschließlich `grant`, `deactivate` und `reactivate`.

Actor und Ziel sind getrennte Foreign Keys auf persistente Userfacts.

Erwartete und resultierende Menge sind vollständig an dieselbe Datenklasse
gebunden.

Die Tabelle speichert weder Rolle noch Membership noch Researchpermission.

## Atomare Bootstrapgrundlage

`mh_supervisor_cleanup_retention_policy_bootstraps` hält eine stabile
Bootstrap-ID, Ziel-User, initiale Policyrevision, initiale Authorityrevision,
positive Dauer und Zeitpunkt.

Damit kann ein späterer Adapter den ersten Policy- und Authoritybestand unter
einer Transaktion erzeugen und nachvollziehbar binden.

Der Bootstrap erzeugt keinen User, Workspace, Membership- oder Rollenfact.

Die Migration führt keinen Bootstrap und keinen Backfill aus.

## Offline-Recoverygrundlage

`mh_supervisor_cleanup_retention_policy_authority_recoveries` hält eine eigene
Recovery-ID, historisches Ziel, erwartete und resultierende Set-Revision sowie
Zeitpunkt.

Das historische Ziel muss als persistenter Userfact existieren.

Recovery enthält keinen SessionPrincipal und keinen freien Status.

Lockout-, History- und Resultatprüfungen bleiben Aufgabe des späteren Adapters.

## Identität und Nichtwiederverwendung

Policyrevision, Authorityrevision, Bootstrap, Policychange, Authoritychange und
Recovery besitzen getrennte Primärschlüsselräume.

Nichtleere IDs sind die technische Untergrenze; Erzeugung und
Nichtwiederverwendung werden später zusätzlich transaktional geprüft.

Historyzeilen sind dauerhafte Auditfacts und werden nicht für neue Vorgänge
umgedeutet.

Die Foundation legt keine konkrete Lösch- oder Archivfrist fest.

## Revocation

Eine neue aktuelle Authorityrevision kann einen bisherigen Member inaktiv
führen, ohne historische Mengen umzuschreiben.

Nach Commit muss jede spätere Permit- oder Mutationsentscheidung die aktuelle
Projektion und ihren vollständigen Memberbestand verwenden.

Ein zuvor ermitteltes Permit darf nicht persistiert oder wiederverwendet
werden.

## Fehlergrenzen

Fehlende aktive Policy oder aktuelle Authority bleibt neutral abwesend und
gewährt keine Wirkung.

Stale Erwartungen, wiederverwendete IDs, verweigerte Lifecyclezustände und
inkompatible Werte werden später detailfrei fachlich zurückgewiesen.

Beschädigte Persistenz oder nicht ausführbare Infrastruktur bleibt davon
getrennte detailfreie technische Nichtverfügbarkeit.

LQ-532 benennt keinen neuen Exceptiontyp.

## Keine DML

Revision 0042 enthält kein `INSERT`, `UPDATE`, `DELETE`, Seed oder Backfill.

Alle neun Tabellen sind nach Upgrade leer.

Der Downgrade entfernt sie in umgekehrter Abhängigkeitsreihenfolge.

## Bewusst nicht enthalten

LQ-532 ergänzt keine SQLAlchemy-Adapterklasse und keine Portimplementation.

Es ergänzt keine Policyevaluation, Clearance, Decision oder Operation.

Es ergänzt keine CLI, Route, Composition, Konfiguration oder Productionwiring.

Es ändert keine bestehenden Domainmodelle oder Signaturen.

## Nächster Slice

LQ-533 implementiert den persistenten atomaren Bootstrap und aktuellen
Policy-/Authority-Lookup auf dieser Foundation.

Reguläre Policy-/Authoritymutation und Recovery bleiben danach ausdrücklich
separate Implementierung.
