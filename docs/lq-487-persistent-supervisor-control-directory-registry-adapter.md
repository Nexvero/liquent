# LQ-487 — Persistent Supervisor Control-Directory Registry Adapter

## Ergebnis

LQ-487 implementiert die LQ-485-Store-/Lookupports gegen Revision 0034.

Der Adapter verwaltet ausschließlich persistente Lifecyclefakten und führt
keine Dateisystemwirkung aus.

## Interner Leafgenerator

Neue Reservationen verwenden standardmäßig kryptographisches `token_hex(32)`
und konstruieren daraus den geschlossenen 256-Bit-Leafwert.

Ein Generator kann nur konstruktiv für Tests injiziert werden.

Requests enthalten weiterhin kein Leaf.

## Feste Kollisionsgrenze

Der Adapter prüft höchstens vier intern erzeugte Leafkandidaten.

Eine belegte Kandidatin wird nicht adoptiert.

Nach Ausschöpfung bleibt der Ausgang technische Unverfügbarkeit und erzeugt
keine unbeschränkte Schleife.

## Journalvoraussetzung

Neue Reservation verlangt einen bestehenden Journaljob desselben Handles.

Fehlt dieser vor Insertwirkung autoritativ, liefert der Store neutral `None`.

Leaf und Reservationszeit werden erst nach dieser Prüfung erzeugt.

## Atomare Reservation

Directory-ID, Handle, Leaf, Reservedzustand und aware UTC-Zeit werden in einer
Transaktion geschrieben.

Activated und Retired bleiben null.

Es entsteht kein partieller erfolgreicher Registryrecord.

## Exakter Reservationretry

Lookup nach Directory-ID und Handle wird vor neuer Reservation durchgeführt.

Exakt dieselbe Bindung liefert die ursprüngliche Reserved-Stufe selbst dann,
wenn die persistente Zeile inzwischen Active oder Retired ist.

Retry schreibt weder Leaf noch Zeit neu.

## Reservationkonflikt

Belegte Directory-ID oder Handle mit anderer Bindung liefert den feldlosen
Directorykonflikt.

Mehrdeutiger beschädigter Bestand ist technische Unverfügbarkeit.

Es gibt kein Last-write-wins oder Rebind.

## Aktivierung

Activate liest die Zeile nach Directory-ID und vergleicht die vollständige
Reservation einschließlich Leaf und Zeit.

Reserved wird genau einmal mit serverseitiger aware UTC-Zeit nach Active
überführt.

Eine rückwärts laufende Clock wird detailfrei abgelehnt.

## Aktivierungsretry

Ein bereits exakt Active Record liefert denselben Active-Wert.

Retired kann nicht reaktiviert werden und liefert Konflikt.

Fehlende Reservation liefert neutral `None`.

## Retirement

Retire vergleicht den vollständigen Active-Wert einschließlich Reservation und
Aktivierungszeit.

Active wird genau einmal nach Retired überführt und erhält eine monotone aware
UTC Retirementzeit.

Reserved kann nicht übersprungen werden.

## Retirementretry

Ein bereits exakt Retired Record liefert denselben Retired-Wert.

Retry verändert keine Zeit und löscht keine Zeile.

Abweichender Activebestand liefert Konflikt.

## Vollständige Lookups

Lookup nach Directory-ID und Handle rekonstruiert jeweils Reserved, Active oder
Retired vollständig.

Unbekannter autoritativer Schlüssel liefert neutral `None`.

Mehrdeutige oder strukturell beschädigte Zeilen bleiben technische
Unverfügbarkeit.

## Zeit- und Zustandsprüfung

Persistierte Zeiten werden als aware UTC validiert.

Die Domainkonstruktoren prüfen zusätzlich Reserved→Activated→Retired.

State-/Nullmatrix wird bei Rekonstruktion erneut fail-closed geprüft.

## PostgreSQL-Serialisierung

Writes sperren Journaljob- und Control-Directory-Tabelle in fester Reihenfolge
mit Share-Row-Exclusive.

Damit werden Handle-, Directory- und Leafentscheidungen serialisiert.

Uniqueconstraints bleiben letzte Race-Sperre.

## SQLite-Testgrenze

SQLite bleibt ausschließlich unterstützte lokale Testgrenze.

Andere Dialekte als PostgreSQL und SQLite werden abgelehnt.

Read-only Lookups nehmen keinen PostgreSQL-Write-Lock.

## Fehlergrenze

SQL-, Lock-, Decode-, Clock-, Generator-, State- und Strukturfehler werden über
die bestehende `ManifestHandoffRegistryUnavailable`-Grenze vereinheitlicht.

IDs, Leaf, SQL und Infrastrukturdetails verlassen den Adapter nicht.

LQ-487 benennt keinen neuen technischen Exceptiontyp.

## Keine Datei

Der Adapter importiert weder Path noch os und öffnet, erstellt, prüft oder
entfernt kein Directory.

Active ist hier nur ein persistenter Lifecyclefakt.

Die Filesystemcomposition muss vor Aktivierung separat sichere Fakten belegen.

## Keine Authority oder Cleanup

Der Adapter akzeptiert keine Session, Nutzer-, Workspace-, Rollen-, Permission-
oder Allowentscheidung.

Er besitzt kein Delete, Reactivate, Rotate, Adopt oder Cleanup.

Retired-Zeilen bleiben erhalten.

## Kein Schema oder Wiring

LQ-487 ändert Revision 0034 nicht und ergänzt keine Migration.

Head bleibt `20260825_0034` mit 34 linearen Migrationen.

Es gibt keinen Service-, CLI-, Route-, Operator-, Compose- oder
Production-Wiring-Entscheid.

## Tests

Fokussierte Prüfungen belegen Journalvoraussetzung, intern begrenzte
Leafgenerierung, exakte Retries, vorwärtsgerichtete Transitionen, vollständige
Lookups, Locks, UTC-/Stateprüfung und fehlende Datei-/Authoritymacht.

## Nächster Slice

LQ-488 sollte den sicheren lokalen Filesystemadapter für Reserved-Leaf-Anlage,
Active-only-Auflösung und vollständige Root-/Directory-Faktenprüfung
implementieren.

Die Lifecyclecomposition folgt anschließend.
