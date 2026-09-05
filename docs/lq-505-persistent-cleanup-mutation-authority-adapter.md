# LQ-505 — Persistent Cleanup Mutation Authority Adapter

## Ergebnis

LQ-505 implementiert die sechzehn LQ-503-Ports gegen die vier getrennten
Authority-Inventare der Revision `20260826_0038`.

Der Adapter erzeugt keine Cleanuprevision, Clearance oder physische Wirkung.

## Ein interner Algorithmus

`DatabaseManifestHandoffSupervisorCleanupMutationAuthorities` verwendet einen
gemeinsamen internen Algorithmus für Setrekonstruktion und Transaktionen.

Die sechzehn öffentlichen Methoden wählen ihre Quelle fest im Code.

Caller können keine Authority-Art oder Tabelle als Parameter übergeben.

## Vier read-only Lookups

Management, Hold, Recovery und Referenzen besitzen eigene Lookupmethoden.

Jeder Lookup bindet Principal und Scope an den Current-Pointer, ein Active-
Member, einen aktiven persistenten User und einen aktiven Handoffscope.

Fehlender oder entzogener Bestand liefert `False`.

## Bool nur als Resultat

Das Bool wird ausschließlich serverseitig aus dem System of Record erzeugt.

Es wird von keiner Schreibmethode als Authorityinput akzeptiert.

Der spätere Quellmutationsadapter muss Authority innerhalb seiner eigenen
Schreibtransaktion erneut prüfen.

## Getrennte Bootstrapmethoden

Jede Authority-Domäne besitzt eine eigene Bootstrapmethode und eigene Tabelle.

Bootstrap validiert exakt den typgleichen Command.

Ein Command einer Schwesterquelle ist technische Fehlverwendung.

## Bootstrap-Retry zuerst

Eine vorhandene Bootstrap-ID wird vor aktuellen Foundationprüfungen gelesen.

Exakt gleiche Target-/Scopebindung liefert das bereits persistierte Set.

Abweichende Wiederverwendung liefert den detailfreien Authoritykonflikt.

## Bootstrap nur bei leerer Historie

Ein neuer Bootstrap ist nur zulässig, wenn im exakten Domänen-/Scope-Inventar
noch keine Setrevision existiert.

Target-User und Scope müssen aktuell aktiv sein.

Der Adapter erzeugt Setsequenz 1 mit genau einem Active-Member.

## Atomarer Bootstrap

Neue Setrevision, Member, Current-Pointer und Bootstrapentscheidung committen in
derselben Transaktion.

Die Ergebnisrevision und serverseitige UTC-Zeit werden intern erzeugt.

Fehler hinterlassen keinen Teilbestand.

## Bootstrap ist nicht verdrahtet

Die persistente Methode ist noch keine Productionfreigabe.

Sie wird weder durch Appfactory, Route, CLI noch Operator aktiviert.

Ein kontrolliertes owner-only Bootstrap-Wiring bleibt separat.

## Vier Lifecyclemethoden

Jede Domäne besitzt eine eigene principalgebundene Lifecyclemethode.

Sie akzeptiert ausschließlich den typgleichen Changecommand.

Principal und Commandactor können nicht durch Callerrollen ersetzt werden.

## Lifecycle-Retry zuerst

Eine vorhandene Change-ID wird vor aktueller Actorauthority gelesen.

Actor, Target, Scope, erwartete Revision und Intent müssen exakt der
persistierten Entscheidung entsprechen.

Exakte Wiederholung liefert dasselbe Ergebnis-Set ohne zweite Mutation.

## Aktuelle Lifecycle-Authority

Für einen neuen Change liest dieselbe Transaktion Current-Pointer, erwartete
Setrevision, Actor-Member, aktiven Actor, aktiven Target-User und aktiven Scope.

Actor muss Active-Member des erwarteten aktuellen Sets derselben Domäne sein.

Ein Holder einer Schwesterquelle genügt nicht.

## Geschlossene Transitionen

Grant verlangt fehlende Zielhistorie im vollständigen Set.

Deactivate verlangt Active, Reactivate verlangt Inactive.

Andere Zustandsmatrizen liefern detailfreien Konflikt und schreiben nichts.

## Vollständige Setkopie

Jeder erfolgreiche Lifecyclechange kopiert sämtliche bekannten Member des
aktuellen Sets und verändert ausschließlich den Targetstatus.

Die neue positive Sequenz folgt auf die aktuelle Sequenz.

Historische Sets und Members werden nicht aktualisiert oder gelöscht.

## Effektiver Lockoutschutz

Vor Commit einer Deaktivierung muss im Ergebnis-Set mindestens ein Active-
Member verbleiben, dessen persistenter User und Scope aktuell aktiv sind.

Eine bloß Active markierte Zuordnung eines inaktiven Users reicht nicht.

Selbstdeaktivierung des letzten wirksamen Holders wird abgelehnt.

## Atomarer Lifecyclecommit

Neue Setrevision, vollständige Members, Lifecycleentscheidung und
Current-Pointer werden atomar geschrieben.

Expected- und Resultrevision bleiben verschieden.

Die serverseitige UTC-Zeit wird einmal pro Commit bestimmt.

## Vier Offline-Recoverymethoden

Jede Domäne besitzt eine eigene Recoverymethode ohne `SessionPrincipal`.

Sie akzeptiert ausschließlich den typgleichen Recoverycommand.

Die Methode wird nicht automatisch als Online- oder Browserroute geöffnet.

## Recovery-Retry zuerst

Eine vorhandene Recovery-ID wird vor aktueller Closed-Scope-Prüfung gelesen.

Exakt gleiche Target-, Scope- und Vorgängerbindung liefert dasselbe Ergebnis-
Set.

Abweichende Wiederverwendung ist detailfreier Konflikt.

## Recovery nur im geschlossenen Set

Ein neuer Recoverycommit verlangt den exakt erwarteten Current-Pointer und null
aktuell wirksame Holder derselben Domäne und desselben Scopes.

Target muss bereits Mitglied des erwarteten vollständigen Sets sein.

Target-User und Scope müssen aktuell aktiv sein.

## Recovery verändert nur Authoritystatus

Recovery kopiert das vollständige erwartete Set und setzt ausschließlich das
historische Targetmember auf Active.

User- und Scopestatus werden nicht verändert.

Neue Personen oder Scopewechsel sind ausgeschlossen.

## Atomarer Recoverycommit

Neue Setrevision, vollständige Members, Recoveryentscheidung und Current-
Pointer committen gemeinsam.

Die Recovery-ID bleibt dauerhaft an ihren Intent gebunden.

Teilbestand wird an der bestehenden technischen Fehlergrenze vereinheitlicht.

## Current-Pointer-Update

Der Pointer wird erst nach dem Insert der vollständigen neuen Set- und
Memberzeilen auf die Ergebnisrevision gesetzt.

Beim ersten Bootstrap wird er neu angelegt.

Unique- und Foreign-Key-Constraints bleiben zusätzliche Integritätssperren.

## PostgreSQL-Konkurrenzordnung

Schreibvorgänge sperren aktive User-/Scope-Foundations und alle sechs Tabellen
der exakten Authorityquelle in einer festen Reihenfolge.

Andere Quellen bleiben fachlich getrennt.

SQLite wird für lokale fokussierte Tests unterstützt; andere Dialekte scheitern
detailfrei.

## Keine positiven Caches

Lookups und neue Mutationen lesen den aktuellen persistenten Bestand bei jedem
Aufruf erneut.

Nach committiertem Entzug liefern spätere Lookups False und neue Lifecycle-
Intents keine Authority.

Nur bereits committierte exakte Retry-IDs bleiben rekonstruierbar.

## IDs und Zeiten

Neue Setrevisionen werden über einen intern kontrollierten Generator erzeugt.

Tests können Generator und aware-UTC-Uhr injizieren.

Ungültige Generator- oder Uhrwerte werden als technische Unverfügbarkeit
behandelt.

Lifecycle- und Recoveryzeiten dürfen nicht vor der aktuellen Setzeit liegen.

## Neutrale Ergebnisse und Konflikt

Unbekannte oder inaktive Foundations und fehlende aktuelle Authority liefern an
den nichtoffenlegenden Grenzen None beziehungsweise False.

Stale Revision, unzulässige Transition, Lockout und ID-Kollision liefern den
feldlosen Authoritykonflikt.

Persistenz- und Strukturfehler bleiben getrennte detailfreie technische
Unverfügbarkeit.

## Keine Quellrevisionmutation

LQ-505 schreibt keine Cleanupmanagement-, Hold-, Recovery- oder
Referenzrevision aus LQ-497.

Die LQ-501-Changebindings bleiben unverändert.

Der autorisierte Revisionsadapter folgt separat.

## Keine Clearancecreation

Der Adapter erzeugt weder Cleanupattempt noch Clearance.

Er liest kein Directory, Journal oder Retentionentscheid.

Atomare Attempt-/Clearancecreation bleibt ein späterer Slice.

## Keine Datei oder Productionverdrahtung

Es gibt keine Pfad-, Datei-, Unlink-, Rmdir- oder physische Cleanupoperation.

Settings, Appfactory, Route, CLI, Operator, Compose und Deployment bleiben
unverändert.

Head und Migrationsanzahl bleiben `20260826_0038` und 38.

## Tests

Fokussierte Prüfungen belegen sechzehn öffentliche Methoden, fest codierte
Quellwahl, aktive Lookupjoins, Retry-first-Reihenfolge, leeren Bootstrap,
Current-/Expected-Vergleich, geschlossene Transitionen, vollständige Setkopie,
effektiven Lockoutschutz, geschlossene Recovery und atomare Pointerupdates.

Sie belegen außerdem Detailfreiheit sowie fehlende Quellrevision-, Clearance-,
Datei- und Wiringwirkung.

## Nächster Slice

LQ-506 sollte die vier autorisierten append-only Quellrevisionmutationen gegen
Revisionen 0036/0037 und die aktuellen LQ-505-Authority-Sets implementieren.

Atomare Attempt-/Clearancecreation und physischer Cleanup folgen getrennt.
