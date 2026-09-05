# LQ-488 — Safe Local Supervisor Control-Directory Adapter

## Ergebnis

LQ-488 implementiert die lokale physische Grenze des in LQ-484 bis LQ-487
definierten privaten Supervisor-Control-Directory-Lifecycles.

Der Adapter legt ausschließlich ein bereits persistent reserviertes Leaf an
und löst ausschließlich einen aktuell persistenten Active-Bestand auf.

## Konstruktives Root

Das private Root wird als absoluter `Path` konstruktiv injiziert.

Kein Request kann Root, Parent, Leaf oder einen anderen Pfad wählen.

Der Konstruktor führt kein Dateisystem-I/O aus und legt das Root nicht an.

## Rootverantwortung

Deployment und Process-Setup müssen das Root vor Nutzung bereitstellen.

Das Root muss ein echtes Directory im Besitz der effektiven Prozess-UID mit
Modus `0700` sein.

Ein fehlendes, verlinktes, ausgetauschtes, fremdes oder zu weit geöffnetes
Root ist technische Unverfügbarkeit.

## Prüfung bei jedem Zugriff

Jede Anlage und Auflösung öffnet das Root erneut mit Directory-, No-follow-
und Close-on-exec-Semantik.

`lstat`- und Deskriptorfakten müssen dasselbe Device und denselben Inode
bezeichnen.

Damit wird kein beim Konstruktor gewonnener Sicherheitszustand gecacht.

## Keine caller-gelieferte Leafwahl

`create_reserved` akzeptiert ausschließlich den vollständigen geschlossenen
Reserved-Domainwert.

Das Leaf stammt unverändert aus der persistenten LQ-487-Reservation.

Directory-ID, Handle oder Leaf werden nicht aus einem Pfad rekonstruiert.

## Relative Anlage

Die Anlage erfolgt mit `mkdir` relativ zum geöffneten Rootdeskriptor.

Das Leaf wird nie durch absolute Verkettung, `chdir` oder Shellwirkung
interpretiert.

Der Domainwert begrenzt es bereits auf 64 kleingeschriebene Hexzeichen.

## Privates Leaf

Ein neu angelegtes Leaf erhält Modus `0700`.

Es wird anschließend mit Directory- und No-follow-Semantik geöffnet.

Typ, effektiver Eigentümer und exakter Modus werden aus dem Deskriptor erneut
geprüft.

## Bindung des geöffneten Leafs

Der nach Name ohne Symlinkfolge gelesene Eintrag und der geöffnete
Directorydeskriptor müssen dasselbe Device und denselben Inode besitzen.

Ein Austausch zwischen Anlage, Öffnung und Faktenprüfung wird nicht
toleriert oder adoptiert.

## Durable Anlage

Nach einer neuen Anlage werden zuerst das Leafdirectory und danach das
Rootdirectory synchronisiert.

Erst danach liefert der Adapter den konstruktiven absoluten Pfad zurück.

Die spätere Composition darf erst nach diesem Erfolg Active persistieren.

## Exakter Retry

Existiert das reservierte Leaf bereits, öffnet und prüft der Adapter exakt
diesen Bestand erneut.

Ein privates Directory derselben Rootbindung ist idempotenter Erfolg.

Der Retry erzeugt kein neues Leaf und verändert weder Modus noch Eigentümer.

## Physischer Konflikt

Ein vorhandener Symlink, Nicht-Directory, fremder Eigentümer, falscher Modus
oder während der Prüfung ausgetauschter Eintrag liefert den bestehenden
detailfreien Control-Directory-Konflikt.

Der Adapter chmodded, chowned, ersetzt oder adoptiert unsicheren Bestand nicht.

## Active-only Registryprüfung

`resolve_active` akzeptiert ausschließlich eine interne Directory-ID.

Der Adapter fragt den injizierten vollständigen Lifecyclelookup bei jedem
Aufruf genau einmal neu ab.

Caller können keinen Active-Wert, kein Leaf und kein Allow-Bit vorgeben.

## Neutrale Nichtauflösung

Eine autoritativ unbekannte Directory-ID liefert neutral `None`.

Ein bekannter Reserved- oder Retired-Bestand liefert ebenfalls keinen
publizierbaren Pfad.

Diese Nichtauflösung erteilt keine Information über den konkreten Zustand.

## Active-Prüfung

Nur der vollständige Active-Domainwert gibt sein persistiertes Leaf zur
physischen Prüfung frei.

Root und Leaf werden über dieselben aktuellen Deskriptorfakten wie bei der
Anlage geprüft.

Erst nach vollständigem Erfolg wird `root / leaf` ausgegeben.

## Active-Divergenz

Ein fehlendes, verlinktes, ausgetauschtes oder unsicheres Leaf bei aktuellem
Active-Fakt ist technische Unverfügbarkeit.

Der Adapter normalisiert diese Divergenz weder zu `None` noch zu einem neuen
Directory.

Er legt bei Active niemals ein Leaf an.

## Fehlergrenze

Root-, Lookup-, Deskriptor-, fsync- und unerwartete Betriebssystemfehler werden
detailfrei über die bestehende technische Grenze vereinheitlicht.

Der Slice benennt keinen neuen Exceptiontyp.

Pfad-, Leaf-, Eigentümer- und Infrastrukturdetails verlassen die Grenze nicht.

## Keine Authority

Directory-ID, Reserved, Active, Rootbesitz und ein sicherer physischer Bestand
erteilen keine Supervisor-, Writer-, Recovery- oder Cleanupauthority.

Der Adapter akzeptiert keine Session, User-ID, Workspace-ID, Rolle,
Permission oder caller-gelieferte Allowentscheidung.

Aktuelle Authority bleibt vor der späteren Lifecyclecomposition.

## Kein Cleanup

LQ-488 besitzt kein Remove, Delete, Retire, Rotate, Rename oder Prune.

Retired verhindert Auflösung, entfernt aber kein physisches Directory.

Retention und Cleanupauthority bleiben separate spätere Slices.

## Keine Registrymutation

Der Adapter reserviert, aktiviert und retired keine Lifecyclezeile.

Er schreibt keine SQL-Daten und besitzt keine Engine oder Transaktion.

Reservation und Active bleiben Fakten des persistenten LQ-487-Adapters.

## Kein Schema oder Wiring

LQ-488 ergänzt keine Tabelle, Migration, Portsignatur oder Domainklasse.

Head bleibt `20260825_0034` mit 34 linearen Migrationen.

Es gibt kein Service-, CLI-, Route-, Operator-, Compose-, Environment- oder
Production-Wiring.

## Tests

Fokussierte Prüfungen belegen konstruktives absolutes Root, No-follow-
Deskriptorzugriff, `0700`/Owner-/Inodeprüfung, relative idempotente Anlage,
beide fsyncs, genau einen aktuellen Lookup, Active-only-Auflösung, neutrale
Nichtauflösung und fehlende Cleanup-/Authoritymacht.

## Nächster Slice

LQ-489 sollte Registry und lokalen Adapter zu einem retry-sicheren
Reserve/Create/Activate-Lifecycle komponieren.

Retirement, Cleanup und Production-Wiring bleiben danach getrennt.
