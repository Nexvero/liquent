# LQ-529 — Atomic Persistent Supervisor Cleanup Retention Operation Store

## Ergebnis

LQ-529 implementiert den LQ-528-Operationstore gegen Revision 0041.

Der Adapter persistiert eine autoritativ erzeugte Retentionevaluation, den
bestehenden Cleanup-Decisionwert und ihre dauerhafte Operationbindung atomar.

Er implementiert keine Retentionpolicy und keinen Operator.

## Adaptergrenze

`DatabaseManifestHandoffSupervisorCleanupRetentionOperations` erhält genau
eine extern besessene SQLAlchemy-Engine und optional eine Clock.

Der Konstruktor führt kein I/O aus.

Die Clock erzeugt ausschließlich die technische Bindungszeit und entscheidet
weder Policyrevision noch Disposition oder Evaluationszeit.

## Geschlossener Eingang

`bind_control_directory_retention_decision` akzeptiert ausschließlich
`BindManifestHandoffSupervisorControlDirectoryRetentionDecision`.

Freie Dicts, Booleans, Rollen, Sessions, Pfade oder Dispositionen werden nicht
akzeptiert.

Die Evaluation ist vor dem Storeaufruf bereits geschlossen und typisiert.

## Retry zuerst

Innerhalb der Schreibtransaktion liest der Adapter zuerst nach Operation-ID.

Eine vorhandene Operation wird vollständig aus Operation, Decision und
Directoryregistry rekonstruiert.

Exakt gleiche Evaluation und Decision-ID liefern denselben gebundenen Wert.

Eine andere Directory-, Retired-, Policy-, Datenklassen-, Dispositions-, Zeit-
oder Decisionbindung derselben Operation-ID liefert detailfreien Conflict.

## Keine erneute Policyevaluation

Ein exakter Retry ruft keine Policyquelle auf und erzeugt keine neue Decision.

Der Adapter besitzt selbst keinen Policyport.

Er berechnet weder Alter noch TTL, Hold, Recovery, Referenzen oder freien
Speicher.

## Decision-ID-Kollision

Existiert die angeforderte Decision-ID bereits ohne dieselbe Operation, wird
sie nicht adoptiert.

Der Adapter liefert detailfreien Conflict.

Damit kann eine Operation keine fremd oder partiell persistierte Decision als
eigenes Ergebnis übernehmen.

## Aktuelle Retiredbindung

Bei einer neuen Operation liest der Adapter die Directoryregistry innerhalb
derselben Transaktion.

Unbekannte Directory-ID bleibt neutral `None`.

Nur ein vollständig rekonstruierter Retired-Wert, der exakt der Evaluation
entspricht, darf fortfahren.

Reserved, Active oder abweichende Lifecyclefakten liefern detailfreien
Conflict.

Der Adapter retirert oder verändert das Directory nicht.

## Append-only Sequenz

Die neue Decision erhält die nächste positive Sequenz ihres Directorys.

Frühere Decisions werden nicht überschrieben, deaktiviert oder gelöscht.

PostgreSQL serialisiert die Sequenzermittlung über feste Tabellenlocks;
Constraints bleiben die letzte Race-Sperre.

## Decisionkonstruktion

Der Adapter konstruiert den bestehenden LQ-492-Decisionwert aus aktuellem
Retired-Wert, Command-Decision-ID, Evaluations-Policyrevision, Disposition und
Evaluationszeit.

Die Adapterclock ersetzt die autoritative Evaluationszeit nicht.

Domainvalidierung belegt erneut, dass die Decisionzeit nicht vor Retirement
liegt.

## Atomarer Doppelappend

Decisioninsert und Operationinsert laufen in derselben Engine-Transaktion.

Die Decision wird zuerst geschrieben, damit der zusammengesetzte Fremdschlüssel
der Operation erfüllt ist.

Erst danach wird die vollständige Operationbindung geschrieben.

Ein Fehler beim zweiten Insert rollt auch den Decisioninsert zurück.

Es gibt keinen Commit oder extern sichtbaren Erfolg zwischen beiden Inserts.

## Persistierte Operationsfakten

Die Operation speichert unverändert Operation-ID, Directory-ID, Decision-ID,
Policyrevision, Datenklasse, Disposition und Evaluationszeit.

`bound_at` stammt aus der Adapterclock und darf nicht vor `evaluated_at`
liegen.

Der Store ergänzt keine Actor-, Membership-, Rollen- oder Authorityspalte.

## Gebundenes Ergebnis

Nach beiden Inserts liefert der Adapter
`BoundManifestHandoffSupervisorControlDirectoryRetentionDecision`.

Das Domainmodell prüft Retired-Wert, Policyrevision, Disposition und Zeit
zwischen Evaluation und Decision erneut exakt.

Operation-ID und Directory bleiben über den ursprünglichen Request gebunden.

## Rekonstruktion

Der Retryjoin liest Operation, referenzierte Decision und aktuelle
Directoryregistry gemeinsam.

Operation- und Decision-Policyrevision, Disposition und Zeit werden getrennt
dekodiert und anschließend durch den Bound-Wert auf Gleichheit geprüft.

Beschädigte, partielle oder cross-gebundene Zeilen sind technische
Unverfügbarkeit und werden nicht neutralisiert.

## Zeitregeln

Evaluations-, Decision- und Bindungszeiten werden als aware UTC validiert.

Decisionzeit muss exakt Evaluationszeit sein.

Bindungszeit muss gleich oder später sein.

Eine regredierende Clock ist technische Unverfügbarkeit und schreibt nichts.

## PostgreSQL-Serialisierung

Writes sperren Directoryregistry, Cleanup-Decisions und Retention-Operations
in einer festen Reihenfolge mit Share-Row-Exclusive.

Retryprüfung, Decision-ID-Kollision, aktuelle Retiredbindung, Sequenz und beide
Inserts liegen unter derselben Sperr- und Transaktionsgrenze.

## SQLite-Testgrenze

SQLite bleibt ausschließlich unterstützte lokale Testgrenze ohne
PostgreSQL-Tabellenlock.

Andere Dialekte werden detailfrei abgelehnt.

Es gibt keinen In-Memory- oder Dateifallback im Adapter.

## Fehlergrenze

SQL-, Lock-, Decode-, UTC-, Clock-, Constraint- und Strukturfehler werden über
die bestehende `ManifestHandoffRegistryUnavailable`-Grenze vereinheitlicht.

LQ-529 ergänzt keinen technischen Exceptiontyp.

Conflict, neutrale Abwesenheit und technische Unverfügbarkeit bleiben
getrennt.

## Keine Löschung oder Mutation anderer Quellen

Der Adapter führt kein `UPDATE` oder `DELETE` aus.

Er verändert keine Authority-Sets, Management-, Hold-, Recovery- oder
Referencequellen.

Er startet keine Clearance und keinen Cleanup-Attempt.

## Keine Dateisystemwirkung

Das Modul importiert weder `Path` noch `os`.

Es öffnet, inventarisiert, verändert oder entfernt kein Control-Artefakt.

Eine `eligible`-Decision bleibt ohne spätere aktuelle Clearance wirkungslos.

## Kein Wiring

Es gibt keinen Policyadapter, Operator, Entry Point, HTTP-, Appfactory-,
Compose-, Worker-, Scheduler-, Runbook- oder Deploymentpfad.

Das Paketinventar bleibt bei 63 Entry Points und 68 Operatorfiles.

## Kein Schema

LQ-529 ergänzt keine Migration und ändert Revision 0041 nicht.

Head bleibt `20260826_0041` mit 41 linearen Migrationen.

## Tests

Statische Tests prüfen geschlossenen Eingang, Retry-vor-Current, Kollision,
Retiredbindung, Sequenz, Insertreihenfolge, eine Transaktion, Rekonstruktion,
UTC-/Clockregeln, Locks, Dialekte und ausgeschlossene Wirkungen.

Sie behaupten keine ausgeführte PostgreSQL-Evidence.

## Nächster Slice

LQ-530 definiert die autoritative Retention-Policy-Quell- und
Administrationsgrenze.

Policyadapter, Retentionoperator, Retirement, Deployment und verpflichtende
PostgreSQL-Evidence bleiben separat.
