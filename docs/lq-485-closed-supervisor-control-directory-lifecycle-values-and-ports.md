# LQ-485 — Closed Supervisor Control-Directory Lifecycle Values and Ports

## Ergebnis

LQ-485 implementiert die geschlossenen Domainwerte und minimalen Ports des
LQ-484-Control-Directory-Lifecycles.

Der Slice implementiert noch keine Persistenz oder Dateisystemwirkung.

## Leafwert

`ManifestHandoffSupervisorControlDirectoryLeaf` trägt ausschließlich ein
repr-freies opakes internes Leaf.

Die geschlossene Form verlangt 256 Bit kleingeschriebenes Hexmaterial.

Der Wert enthält keinen Slash, Pfadseparator oder lesbare Jobidentität.

## Keine Leafwahl im Reservecommand

`ReserveManifestHandoffSupervisorControlDirectory` enthält nur Directory-ID
und Supervisorhandle.

Caller können kein Leaf, keinen Pfad und keinen Rootwert liefern.

Das spätere Store-/Generator-Adapterpaar erzeugt das Leaf intern.

## Zustandsenum

`ManifestHandoffSupervisorControlDirectoryState` besitzt exakt Reserved,
Active und Retired.

Jeder Ergebniswert setzt seinen Zustand konstruktiv mit `init=False`.

Freie Statusstrings sind ausgeschlossen.

## Reserved-Ergebnis

Reserved bindet Directory-ID, Handle, opakes Leaf und aware UTC
Reservationszeit.

Alle Identitäten und das Leaf bleiben repr-frei.

Die Zeit darf weder naiv noch Nicht-UTC sein.

## Activate-Request

Aktivierung akzeptiert ausschließlich den vollständigen Reserved-Wert.

Directory-ID, Handle oder Leaf können beim Übergang nicht ersetzt werden.

Ein freier Filesystem-Beweis oder Allowwert ist kein Requestfeld.

## Active-Ergebnis

Active trägt die vollständige Reservation unverändert und ergänzt nur die aware
UTC Aktivierungszeit.

Aktivierung darf zeitlich nicht vor Reservation liegen.

Directory-ID, Handle und Leaf werden read-only aus der Reservation projiziert.

## Retire-Request

Retirement akzeptiert ausschließlich den vollständigen Active-Wert.

Reserved kann nicht direkt retired werden.

Ein bereits Retired-Wert kann nicht als neuer Retirementrequest dienen.

## Retired-Ergebnis

Retired trägt Active vollständig weiter und ergänzt nur die aware UTC
Retirementzeit.

Retirement darf zeitlich nicht vor Aktivierung liegen.

Die ursprüngliche Reservation bleibt vollständig erreichbar.

## Lifecycleunion

`ManifestHandoffSupervisorControlDirectoryLifecycle` ist die geschlossene Union
aus Reserved, Active und Retired.

Lookup liefert keine freie Projection oder Mappingform.

Der konkrete Typ bestimmt den Lifecyclezustand.

## Konflikt

`ManifestHandoffSupervisorControlDirectoryConflict` ist feldlos und detailfrei.

Er kann spätere ID-, Handle-, Leaf-, State- oder physische Divergenz
vereinheitlichen.

Er enthält keinen Pfad oder Infrastrukturwert.

## Storeport

`ManifestHandoffSupervisorControlDirectoryLifecycleStore` besitzt genau
Reservation, Aktivierung und Retirement.

Jede Methode akzeptiert ausschließlich ihren geschlossenen Requesttyp.

Es gibt kein Update, Delete, Reactivate, Rotate, Adopt oder Cleanup.

## Reserveausgang

Reservation liefert Reserved, detailfreien Konflikt oder neutrales `None` für
eine autoritativ fehlende Voraussetzung vor Wirkung.

Technische Unverfügbarkeit bleibt an der bestehenden Exceptiongrenze.

Der Port behauptet noch keine physische Directoryanlage.

## Activateausgang

Aktivierung liefert Active, Konflikt oder neutrales `None` bei fehlender
persistenter Reservation.

Die spätere Composition muss die physische sichere Anlage vor dem Storeaufruf
belegen.

Der Domainwert selbst enthält keinen caller-gelieferten Beweis.

## Retireausgang

Retirement liefert Retired, Konflikt oder neutrales `None` bei fehlendem
passenden Activebestand.

Die spätere Composition prüft Terminal- und Lifecyclevoraussetzungen vor dem
Storeaufruf.

Retirement ist keine Löschoperation.

## Lookupport

Der Lookupport löst entweder nach Directory-ID oder Supervisorhandle auf.

Beide Methoden liefern die vollständige Lifecycleunion oder neutral `None` für
autoritative Unbekanntheit.

Es gibt keine Liste, Pfadauflösung oder Active-Filteroption.

## Warum Lookup alle Zustände liefert

Restart-Reconciliation muss Reserved, Active und Retired unterscheiden.

Ein Active-only Registrylookup würde Reserved und Retired fälschlich als
Unbekanntheit normalisieren.

Der spätere Filesystemresolver darf separat ausschließlich Active akzeptieren.

## Kein Root oder Path

Kein neuer Domainwert und keine Portmethode importiert oder akzeptiert `Path`.

Root, Directorydescriptor und Hostpfad bleiben reine Adaptercomposition.

Leaf ist kein allgemein auflösbarer Pfad.

## Keine Authority

Werte und Ports akzeptieren keine Session, User-ID, Workspace-ID, Rolle,
Permission oder Allowentscheidung.

Directorybindung erteilt keine Supervisor- oder Cleanupfähigkeit.

Aktuelle Authority bleibt vor späteren Mutationsaufrufen.

## Repr und Fehler

Directory-ID, Handle und Leaf bleiben repr-frei.

Validierungsfehler nennen keine konkreten Werte.

Konflikt besitzt keine Felder.

## Keine Persistenz oder Datei

LQ-485 ergänzt keine Tabelle, SQL, Migration, Generatorimplementation,
Filesystemadapter oder Resolver.

Es findet keine Directoryanlage, fsync, Auflösung oder Retirementwirkung statt.

Head bleibt `20260825_0033` mit 33 linearen Migrationen.

## Kein Wiring

Die LQ-481-Factory, Settings, Appfactory, Entrypoint und Deploymentdateien
bleiben unverändert.

Es gibt keinen CLI-, Route-, Operator-, Compose- oder Environmentpfad.

Productionaktivierung bleibt geschlossen.

## Tests

Fokussierte Tests belegen opakes repr-freies Leaf, drei Zustände, typisierte
Transitionen, monotone UTC-Zeiten, vollständige Lifecycleunion, feldlosen
Konflikt, drei Storemethoden, zwei Lookups und fehlende Pfad-/Authoritymacht.

## Nächster Slice

LQ-486 sollte die persistente Registryfoundation mit nicht wiederverwendbaren
Directory-, Handle- und Leafbindungen sowie Reserved/Active/Retired-Zeiten
definieren.

Filesystemadapter und Lifecyclecomposition folgen getrennt.
