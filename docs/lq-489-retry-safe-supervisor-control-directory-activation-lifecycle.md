# LQ-489 — Retry-Safe Supervisor Control-Directory Activation Lifecycle

## Ergebnis

LQ-489 komponiert die persistente LQ-487-Registry und den sicheren lokalen
LQ-488-Adapter zu einem schmalen Reserve/Create/Activate-Lifecycle.

Der Slice besitzt genau die Operation `ensure_active`.

## Request

`ensure_active` akzeptiert ausschließlich den bestehenden geschlossenen
`ReserveManifestHandoffSupervisorControlDirectory`-Wert.

Der Request enthält genau stabile Directory-ID und Supervisorhandle.

Caller liefern weder Leaf, Root, Pfad, Zeit noch physischen Beweis.

## Konstruktive Abhängigkeiten

Registry und lokaler Directoryadapter werden explizit injiziert.

Der Konstruktor führt keine Datenbank- oder Dateisystemwirkung aus.

Der Lifecycle besitzt weder Engine noch Rootconfiguration unmittelbar.

## Feste Reihenfolge

Jeder Aufruf führt ausschließlich diese Reihenfolge aus:

1. persistente Reservation derselben Directory-ID und desselben Handles;
2. sichere physische Anlage exakt des persistierten Leafs;
3. persistente Aktivierung exakt der vollständigen Reservation.

Keine spätere Stufe darf vor erfolgreicher früherer Stufe wirken.

## Durable Reservation vor Datei

`create_reserved` wird nur mit einem vollständigen Reserved-Ergebnis der
Registry aufgerufen.

Fehlende Journalvoraussetzung liefert vor jeder Dateioperation neutral
`None`.

Ein Konflikt der Reservation beendet den Aufruf ebenfalls vor Dateiwirkung.

## Persistiertes Leaf

Die Composition erzeugt kein Leaf und nimmt keines vom Caller entgegen.

Sie reicht den unveränderten Reserved-Wert an den lokalen Adapter weiter.

Damit bleibt LQ-487 alleinige Quelle der dauerhaften Leafbindung.

## Sichere Create-Stufe

Nur ein vom lokalen Adapter bestätigter Pfad erlaubt die Aktivierungsstufe.

Die Composition interpretiert den Pfad nicht, öffnet ihn nicht und gibt ihn
nicht als Authority aus.

Ein physischer Konflikt wird unverändert als bestehender detailfreier
Control-Directory-Konflikt geliefert.

## fsync vor Active

LQ-488 bestätigt eine Neuanlage erst nach Leaf- und Root-fsync.

LQ-489 ruft die Registryaktivierung erst nach dieser Bestätigung auf.

Damit kann kein regulärer Active-Fakt vor durablem physischem Directory
entstehen.

## Vollständige Aktivierung

Die Composition konstruiert den bestehenden Activate-Request ausschließlich
aus der vollständigen Reservation.

Directory-ID, Handle, Leaf und Reserved-Zeit können nicht ersetzt werden.

Das Active-Ergebnis muss exakt dieselbe Reservation tragen.

## Neutralität vor Wirkung

Nur eine autoritativ fehlende Journalvoraussetzung der ersten
Reservationstufe bleibt neutral `None`.

In diesem Ausgang wurde kein Leaf erzeugt oder angelegt.

Die Composition erfindet keine unbekannte Directorybindung.

## Keine Neutralität nach Wirkung

Nachdem die Registry eine Reservation geliefert hat, ist ein fehlender
Aktivierungsbestand keine neutrale Abwesenheit mehr.

Ein `None` der Aktivierungsstufe wird detailfrei als technische
Unverfügbarkeit behandelt.

So wird ein persistiertes oder physisch angelegtes Directory nicht als nie
begonnener Lifecycle dargestellt.

## Reservationkonflikt

Cross-ID-, Cross-Handle- oder persistente Bindungsdivergenz liefert den
bestehenden feldlosen Konflikt.

Die Composition startet danach weder Create noch Activate.

Sie versucht kein Rebind und keine neue Directory-ID.

## Create-Konflikt

Unsicherer oder fremder physischer Bestand liefert denselben detailfreien
Konflikt.

Die Composition aktiviert in diesem Ausgang nicht.

Sie repariert, ersetzt, chmodded, chowned oder adoptiert den Bestand nicht.

## Aktivierungskonflikt

Retired, eine abweichende Reservation oder eine andere vorwärtsgerichtete
Registrydivergenz liefert den bestehenden Konflikt.

Ein bereits sicher angelegtes Leaf wird dabei nicht gelöscht.

Cleanup ist kein Kompensationsmechanismus für einen unklaren Lifecycle.

## Exakter Retry nach Reservation

Ein Retry mit derselben Directory-ID und demselben Handle erhält von LQ-487
dieselbe ursprüngliche Reservation.

Es wird weder ein neues Leaf noch eine neue Reserved-Zeit erzeugt.

LQ-488 prüft oder erstellt ausschließlich dasselbe Leaf.

## Exakter Retry nach Create

Ist die Dateioperation erfolgreich und die Aktivierung technisch unklar,
bleibt das sichere Leaf bestehen.

Der nächste identische Aufruf erkennt es idempotent und versucht die
Aktivierung mit derselben Reservation erneut.

Es findet keine physische Rotation oder Ersatzanlage statt.

## Exakter Retry nach Active

Hat die Aktivierung bereits committed, rekonstruiert LQ-487 beim
Reservationsretry weiterhin die ursprüngliche Reserved-Stufe.

Create prüft denselben sicheren Bestand erneut.

Activate liefert anschließend exakt denselben bereits gespeicherten
Active-Wert.

## Restart Reserved

Reserved ohne Leaf wird mit demselben Leaf sicher fortgesetzt.

Reserved mit exakt sicherem Leaf wird idempotent aktiviert.

Reserved mit unsicherem Bestand bleibt Konflikt und wird nicht adoptiert.

## Restart Active

Active wird über dieselbe ursprüngliche Reservation und dieselbe physische
Leafprüfung reconciliert.

Fehlender oder unsicherer Active-Bestand bleibt technisch beziehungsweise
fachlich fail-closed.

Ein Ersatzleaf ist verboten.

## Restart Retired

Die Registry liefert zwar die unveränderliche ursprüngliche Reservation für
den exakten Reserve-Retry, Activate erkennt Retired jedoch als Konflikt.

Die Composition reaktiviert nicht.

Das physische Directory wird nicht entfernt.

## Technische Fehlergrenze

Unerwartete Registry-, Dateisystem-, Ergebnis- oder Abhängigkeitsfehler werden
detailfrei über die bestehende technische Grenze vereinheitlicht.

LQ-489 benennt keinen neuen Exceptiontyp.

IDs, Leaf, Pfad, SQL und Betriebssystemdetails verlassen die Grenze nicht.

## Keine Authority

Reservation, physische Anlage und Active erteilen keine Supervisor-, Writer-,
Recovery- oder Cleanupauthority.

Der Request akzeptiert keine Session, User-ID, Workspace-ID, Rolle,
Permission oder caller-gelieferte Allowentscheidung.

Aktuelle Plattformauthority muss vor `ensure_active` aufgelöst sein.

## Kein Retirement oder Cleanup

LQ-489 besitzt kein Retire, Delete, Remove, Rename, Rotate oder Prune.

Er kompensiert einen Fehler nicht durch Dateilöschung oder Registryrollback.

Retirement und physischer Cleanup bleiben getrennte spätere Lifecycles.

## Kein Schema oder Wiring

Der Slice ergänzt keine Tabelle, Migration, Domainklasse oder Portsignatur.

Head bleibt `20260825_0034` mit 34 linearen Migrationen.

Es gibt kein Service-Facade-, CLI-, Route-, Operator-, Compose-, Environment-
oder Production-Wiring.

## Tests

Fokussierte Prüfungen belegen die feste Reserve/Create/Activate-Reihenfolge,
keine Datei vor Reservation, fsync-Bestätigung vor Active, exakte
Reservationweitergabe, neutrale Abwesenheit nur vor Wirkung, fail-closed
Aktivierungsabwesenheit, Retrypfade und fehlende Authority-/Cleanupmacht.

## Nächster Slice

LQ-490 sollte den kontrollierten Retirement-Lifecycle nach terminalen
System-of-Record-Fakten definieren und komponieren.

Physischer Cleanup und Production-Wiring bleiben danach separat.
