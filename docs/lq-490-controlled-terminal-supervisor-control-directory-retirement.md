# LQ-490 — Controlled Terminal Supervisor Control-Directory Retirement

## Ergebnis

LQ-490 komponiert die persistente Control-Directory-Registry mit dem
persistenten Supervisorjournal zu einem kontrollierten Retirement-Lifecycle.

Nur ein aktuell Active Directory mit genau einem passenden dauerhaft
terminalen Journalview darf nach Retired überführt werden.

## Operation

Der Slice besitzt genau die Operation `retire`.

Sie akzeptiert ausschließlich eine interne
`ManifestHandoffSupervisorControlDirectoryId`.

Caller liefern weder Active-Wert, Handle, Terminalstatus noch
Retiremententscheidung als Boolean.

## Konstruktive Abhängigkeiten

Registry und Journal werden explizit injiziert.

Der Konstruktor führt keine Datenbank-, Datei- oder Prozesswirkung aus.

Die Composition besitzt keine Engine, Rootconfiguration oder Clock direkt.

## Aktueller Registryfakt

Jeder Aufruf löst die Directory-ID genau einmal über die vollständige
Lifecycle-Registry auf.

Die Registry bleibt System of Record für Directory-ID, Handle, Leaf und
Reserved-/Active-/Retired-Zeiten.

Der Caller kann keinen älteren Active-Snapshot zur Mutation einreichen.

## Autoritative Unbekanntheit

Eine autoritativ unbekannte Directory-ID liefert neutral `None`.

In diesem Ausgang wird kein Journal gelesen und keine Transition versucht.

Die Composition erfindet keine Handlebindung.

## Reserved

Ein bekannter Reserved-Bestand ist für Retirement zu früh.

Er liefert den bestehenden detailfreien Control-Directory-Konflikt.

Reserved wird weder aktiviert noch direkt nach Retired übersprungen.

## Retired-Retry

Ein bereits Retired-Bestand wird unverändert idempotent zurückgegeben.

Der Retry liest kein Journal erneut und erzeugt keine neue Retirementzeit.

Retired kann nicht reaktiviert oder einer anderen Handlebindung zugeordnet
werden.

## Active

Nur ein vollständiger aktueller Active-Domainwert öffnet die Terminalprüfung.

Die Composition verwendet dessen persistiertes Handle für alle Journalreads.

Directory-ID, Handle, Leaf, Reserved- und Activated-Zeit bleiben unverändert.

## Writer- und Recoveryjournal

Die Composition inspiziert sowohl den Writer- als auch den Recoveryview für
dasselbe persistierte Handle.

Genau einer der beiden Views muss autoritativ vorhanden sein.

Der Capabilitytyp wird nicht vom Caller gewählt oder geraten.

## Kein Journal

Active ohne passenden Journalview ist keine neutrale Abwesenheit.

Die Registry besitzt eine dauerhafte Journalbindung; fehlender Bestand ist
daher technische Divergenz.

Es wird keine Retirementtransition ausgeführt.

## Mehrdeutiges Journal

Sind Writer- und Recoveryview gleichzeitig vorhanden, ist der Bestand
technisch inkonsistent.

Die Composition wählt keinen View nach Reihenfolge oder Callerpräferenz.

Retirement bleibt fail-closed.

## Geschlossene Viewtypen

Der vorhandene View muss exakt Writer- oder Recoveryjournalview sein.

Freie Mappings, Dicts oder Statusstrings werden nicht akzeptiert.

Seine Registration muss dasselbe Handle wie Active tragen.

## Terminalzustand

Nur `TERMINAL_OBSERVED` ist ein ausreichender dauerhafter Endfakt.

Prepare-, Launch-, Gated-, Release-, Running- und Termination-Requested-
Zustände liefern Konflikt und führen keine Registrymutation aus.

Timeout, Containerabwesenheit oder angeforderte Terminierung sind kein Ende.

## Vollständiger Terminalbeweis

Der terminale View muss eine Terminal-Observation-ID und sein geschlossenes
Writer- oder Recoveryergebnis tragen.

Das Ergebnis muss dasselbe persistierte Handle tragen.

Partielle oder strukturell beschädigte Terminalfakten sind technische
Unverfügbarkeit.

## Warum das Journal autoritativ ist

Der bestehende Terminalservice persistiert `TERMINAL_OBSERVED` erst nach
geschlossenem Capabilityoutcome, kanonischem Terminal-Envelope und direkter
terminaler Enginebeobachtung.

LQ-490 wiederholt diese externen Wirkungen nicht.

Er konsumiert ausschließlich ihren aktuellen dauerhaften System-of-Record-
View.

## Retirementrequest

Nach vollständiger Terminalprüfung konstruiert die Composition den bestehenden
Retire-Request aus exakt dem aktuellen Active-Wert.

Kein Feld kann zwischen Prüfung und Storeaufruf ersetzt werden.

Die Registry serialisiert und validiert die vorwärtsgerichtete Transition.

## Ergebnisbindung

Ein erfolgreiches Retired-Ergebnis muss exakt denselben Active-Wert tragen.

Eine abweichende Bindung oder ein unerwarteter Ergebnistyp ist technische
Unverfügbarkeit.

Der Storekonflikt bleibt als bestehender detailfreier Konflikt sichtbar.

## Keine Neutralität nach Active

Nachdem Active und der passende Terminalview festgestellt wurden, ist ein
fehlender Retirementbestand keine neutrale Abwesenheit.

Ein `None` des Stores wird als technische Divergenz behandelt.

So wird eine unklare Transition nicht als nie vorhandenes Directory
dargestellt.

## Parallelität

Wird derselbe Active-Wert parallel bereits retired, liefert der persistente
Store bei exaktem Retry denselben Retired-Wert.

Eine abweichende oder rückwärtsgerichtete Transition bleibt Konflikt.

Die Composition erzeugt keine zweite Zeit und kein neues Leaf.

## Revocation und spätere Entscheidungen

Vor der ersten Retirementwirkung werden Registry und Journal bei jedem Aufruf
aktuell neu gelesen.

Ein nichtterminaler aktueller View erlaubt kein Retirement.

Ein bereits dauerhaft Retired-Fakt bleibt als abgeschlossene irreversible
Transition idempotent.

## Keine physische Wirkung

LQ-490 öffnet, verändert und entfernt kein Root oder Leaf.

Retired sperrt die LQ-488-Active-Auflösung, löscht aber kein Directory.

Filesystembestand ist kein Ersatz für den terminalen Journalfakt.

## Kein Cleanup

Retirement allein erteilt keine Cleanupauthority.

Der Slice besitzt kein Delete, Remove, Rename, Rotate, Prune oder Retention-
Override.

Physischer Cleanup benötigt einen eigenen späteren Vertrag mit Retention und
aktueller Authority.

## Keine Authority

Directory-ID, Handle, Active, Terminalstatus und Retired erteilen keine
Supervisor-, Writer-, Recovery- oder Cleanupauthority.

Die Operation akzeptiert keine Session, User-ID, Workspace-ID, Rolle,
Permission oder caller-gelieferte Allowentscheidung.

Aktuelle Plattformauthority muss vor dem Aufruf aufgelöst sein.

## Technische Fehlergrenze

Unerwartete Registry-, Journal-, Typ-, Ergebnis- und Abhängigkeitsfehler werden
detailfrei über die bestehende technische Grenze vereinheitlicht.

LQ-490 benennt keinen neuen Exceptiontyp.

IDs, Ergebnisse, SQL und Infrastrukturdetails verlassen die Grenze nicht.

## Kein Schema oder Wiring

Der Slice ergänzt keine Tabelle, Migration, Domainklasse oder Portsignatur.

Head bleibt `20260825_0034` mit 34 linearen Migrationen.

Es gibt kein Service-Facade-, CLI-, Route-, Operator-, Compose-, Environment-
oder Production-Wiring.

## Tests

Fokussierte Prüfungen belegen aktuellen ID-Lookup, neutral unbekannt vor
Wirkung, Reserved-Konflikt, Retired-Retry, genau einen Writer-/Recoveryview,
Terminalzustand und vollständige Handle-/Ergebnisbindung vor Storewirkung,
fail-closed Storeabwesenheit und fehlende Datei-/Cleanup-/Authoritymacht.

## Nächster Slice

LQ-491 sollte den Retention- und Cleanupvertrag für dauerhaft Retired-
Directories definieren, noch ohne physische Löschimplementation.

Production-Wiring bleibt separat geschlossen.
