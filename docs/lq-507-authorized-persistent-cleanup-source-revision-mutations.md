# LQ-507 — Authorized Persistent Cleanup Source Revision Mutations

## Ergebnis

LQ-507 implementiert die vier autorisierten LQ-500-Quellmutationsports gegen
Revisionen 0036, 0037, 0038 und 0039.

Jeder neue Commit schreibt Ergebnisrevision, Changebinding und
Authorizationbinding atomar.

## Vier feste Methoden

Management, Hold, Recovery und Referenzen besitzen jeweils eine eigene
öffentliche Methode.

Die Quelle ist fest im Code ausgewählt.

Caller können weder Tabellenname noch Authority-Art als Parameter liefern.

## Principalbindung

Jede Methode akzeptiert einen `SessionPrincipal` separat vom typisierten
Command.

Der Principal identifiziert den Authorizer, erteilt aber allein keine
Authority.

Seine User-ID wird bei erfolgreichem Commit dauerhaft in Revision 0039 gebunden.

## Retry-first

Vor jeder aktuellen Authority- oder Vorgängerprüfung wird eine vorhandene
Change-ID aus Change-, Ergebnis- und Authorizationtabelle rekonstruiert.

Exakte Übereinstimmung von Principal, Ziel, Scope beziehungsweise Directory,
Vorgänger und gewünschtem Zustand liefert dasselbe committed Resultat.

Abweichung liefert den feldlosen Mutationskonflikt.

## Retry nach Entzug

Ein bereits committierter exakter Retry bleibt nach späterem Authorityentzug
auflösbar.

Ein neuer Change liest dagegen immer das aktuelle Authority-Set und scheitert
nach Entzug fail-closed.

Es gibt keinen positiven Authoritycache.

## Aktuelle Source-Authority

Neue Writes lesen Current-Pointer, Setzeit, Active-Member, aktiven persistenten
Authorizer und aktiven Handoffscope innerhalb derselben Schreibtransaktion.

Das Set muss aus der exakt passenden Management-, Hold-, Recovery- oder
Referenz-Authorityfamilie stammen.

Ein früheres Lookup-True wird nicht akzeptiert.

## Managementziel

Der Managementcommand bindet Target-User und Handoffscope direkt als interne
IDs.

Target-User und Scope müssen aktuell aktiv sein.

Der Authorizer benötigt aktuelle Management-Mutationsauthority im selben Scope.

## Aktuelle Managementrevision

Der Adapter liest die höchste Managementrevision für exakt Target-User und
Scope.

None als erwartete Revision ist nur bei leerer Historie zulässig.

Ansonsten muss die erwartete Revision exakt der höchsten Revision entsprechen.

## Managementappend

Eine neue Managementrevision erhält intern erzeugte stabile Revision-ID,
nächste positive Sequenz und serverseitige UTC-Zeit.

Status ist ausschließlich Active oder Inactive aus dem geschlossenen Command.

Historische Revisionen werden nicht verändert oder gelöscht.

## Serverseitige Ziel-Scopeableitung

Hold-, Recovery- und Referenzcommands tragen nur die interne Directory-ID.

Der Adapter liest innerhalb derselben Transaktion das aktuelle Directory, sein
gebundenes Journaljob und die höchste Journaltransition.

Nur ein vollständig Retired Directory mit terminaler letzter Transition öffnet
die Scopeableitung.

## Kein Caller-Handle oder Scope

Handle und Handoffscope stammen ausschließlich aus Directory und Journaljob.

Caller können keinen Scope, Handle, Leaf oder Journalzustand ergänzen.

Inkonsistenter oder nichtterminaler Bestand ist technische Unverfügbarkeit.

## Aktuelle Zielrevision

Jede Zielquelle liest ausschließlich ihre höchste Revision für das Directory.

None als erwartete Revision gilt nur bei leerer Quellhistorie.

Holdrevision kann keine Recovery- oder Referenzvorgängerrevision erfüllen.

## Zielappend

Neue Hold-, Recovery- und Referenzrevisionen erhalten jeweils ihre eigene
intern erzeugte ID, nächste Sequenz, Clear/Blocked und serverseitige UTC-Zeit.

Der vollständige Resultwert wird mit dem aktuellen Retired-Domainwert
rekonstruiert.

Die drei Quellen bleiben getrennt.

## Monotone Zeiten

Managementzeit darf nicht vor Vorgängerrevision oder verwendeter
Authority-Set-Zeit liegen.

Zielentscheidungszeit darf nicht vor Retirement, terminaler Journalobservation,
Vorgängerrevision oder Authority-Set-Zeit liegen.

Rückläufige Uhren scheitern technisch fail-closed.

## Atomarer Dreifachcommit

Ein erfolgreicher neuer Intent schreibt in derselben Transaktion:

1. die append-only Ergebnisrevision;
2. das LQ-501-Changebinding aus Change-ID, Ziel und Vorgänger;
3. das LQ-506-Authorizationbinding aus Current-Set, Scope und Authorizer.

Entweder alle drei Fakten committen oder keiner.

## Authorizationzeit

Revisionzeit und Authorizationzeit verwenden denselben serverseitig validierten
UTC-Zeitpunkt.

Caller können keine Zeit liefern.

Die Zeit ersetzt weder Current-Pointer noch Active-Member-Prüfung.

## Sequenzierung

Die nächste Sequenz wird aus der höchsten Revision innerhalb der gesperrten
Schreibtransaktion bestimmt.

Caller liefern keine Sequenznummer.

Unique-Constraints bleiben zusätzliche Konkurrenzsperren.

## PostgreSQL-Sperrordnung

Schreibvorgänge sperren User, Scopes, Directory-/Journalgrundlagen, das exakte
Authority-Inventar sowie Revisions-, Change- und Authorizationtabellen in
fester Reihenfolge.

SQLite bleibt für lokale fokussierte Tests unterstützt.

Andere Dialekte scheitern detailfrei.

## Neutrale Ablehnung

Fehlender aktiver Authorizer, inaktiver Target-User oder Scope liefert an der
nichtoffenlegenden Grenze neutral None.

Stale Vorgänger, ID-Wiederverwendung und abweichender Retry liefern den
detailfreien Mutationskonflikt.

Struktur-, Generator-, Uhr- oder Datenbankfehler bleiben technische
Unverfügbarkeit.

## Keine Selbstautorisierung

Eine neu geschriebene Active-Managementrevision autorisiert ihren eigenen
Commit nicht.

Der Commit benötigt vorher aktuelle LQ-505-Management-Mutationsauthority.

Hold-, Recovery- und Referenzrevisionen können ihre Source-Authority ebenfalls
nicht erzeugen.

## Keine Authority-Set-Mutation

LQ-507 verändert keine Setrevision, Member, Pointer, Bootstrap-, Lifecycle- oder
Recoveryentscheidung aus Revision 0038.

Es liest diese Fakten ausschließlich zur aktuellen Autorisierung.

Authorityverwaltung bleibt beim LQ-505-Adapter.

## Keine Clearancecreation

Der Adapter schreibt weder Cleanupattempt noch Clearance.

Eine positive Quellrevision autorisiert keine physische Wirkung.

Atomare Attempt-/Clearancecreation folgt separat.

## Keine Datei oder Verdrahtung

Es gibt keine Pfad-, Datei-, Unlink-, Rmdir- oder Cleanup-Executionoperation.

Settings, Appfactory, Route, CLI, Operator, Compose und Deployment bleiben
unverändert.

Head und Migrationsanzahl bleiben `20260826_0039` und 39.

## Tests

Fokussierte Prüfungen belegen vier feste Methoden, Retry-first über drei
Faktklassen, Principalvergleich, aktuelle Source-Authority, Management-
Targetbindung, serverseitige Directory-/Terminal-/Scopeableitung, erwartete
höchste Revision, monotone Zeiten, Sequenzappend und atomaren Dreifachcommit.

Sie belegen außerdem fehlende Clearance-, Datei-, Authority-Lifecycle- und
Wiringwirkung.

## Nächster Slice

LQ-508 sollte die atomare Attempt-/Clearancecreation aus aktuellem Retired-,
Journal-, Retention-, Management-, Hold-, Recovery- und Referenzbestand
implementieren.

Physischer Cleanup und Production-Wiring bleiben getrennt.
