# LQ-438 — Static Manifest Handoff Scope-Binding Resolver

## Ergebnis

LQ-438 implementiert den in LQ-437 geschlossenen Binding-Lookupport als
explizit injizierten statischen Resolver.

Der Resolver führt keine Discovery und keine Mutation aus.

## Konstruktion

`StaticManifestHandoffScopeBindings` erhält beim Aufbau ausschließlich ein
Iterable bereits validierter `ManifestHandoffScopeBinding`-Werte.

Die Werte werden einmal in einen privaten Index kopiert.

Auch ein One-shot-Iterator ist damit nach dem Aufbau vollständig übernommen.

Der Resolver besitzt keine Defaultbinding und keinen parameterlosen
Produktionsaufbau.

## Exakte Scopeauflösung

`get_binding(scope_id)` sucht ausschließlich die exakt übergebene stabile
Registry-Scope-ID.

Ein vorhandener Eintrag liefert dasselbe unveränderliche Bindingobjekt.

Ein unbekannter, leerer oder typfremder Schlüssel liefert neutral `None`.

Es gibt keine Präfix-, Pfad-, Namens-, Actor- oder Case-folding-Suche.

## Keine Reassignmentoberfläche

Der Index wird nur im Konstruktor erzeugt.

Der Adapter bietet keine Add-, Replace-, Remove-, Reload- oder
Aktivierungsoperation.

Ein laufender Resolver kann deshalb keine Scope-ID auf andere Wurzeln
umhängen.

Ein kontrollierter Konfigurationswechsel benötigt später einen neuen
Resolveraufbau außerhalb dieses Slices.

## Eindeutige Scope-IDs

Jede Scope-ID darf in einer Resolverinstanz genau einmal vorkommen.

Auch zwei inhaltlich gleiche Bindings mit derselben Scope-ID werden
abgelehnt.

Dadurch wird weder Eingabereihenfolge noch last-write-wins zu einer
verdeckten Reassignmententscheidung.

## Private Zielnamespaces

Zielwurzeln verschiedener Scopes müssen lexikalisch vollständig getrennt
sein.

Gleiche, über- oder untergeordnete Zielwurzeln werden beim Aufbau abgelehnt.

Damit kann kein Zielnamespace zwei Scope-IDs zugeordnet sein.

## Cross-Scope-Trennung

Jede private Zielwurzel muss zusätzlich von jeder Sourcewurzel eines anderen
Bindings lexikalisch getrennt sein.

Das verhindert, dass der kontrollierte Sourcebaum eines Scopes den privaten
Handoffbaum eines anderen Scopes umfasst oder in ihm liegt.

Die Prüfung ist symmetrisch und unabhängig von der Eingabereihenfolge.

## Geteilte Sourcewurzel

Mehrere Scopes dürfen dieselbe kontrollierte Sourcewurzel verwenden, sofern
ihre privaten Zielwurzeln eindeutig und von allen Sources getrennt bleiben.

Das ist keine Scope-Reassignmententscheidung: Jede Scope-ID bleibt weiterhin
an ihr vollständiges Source-/Zielpaar gebunden.

So können getrennte private Handoff-Namespaces bewusst aus derselben
kontrollierten Manifestquelle bedient werden.

## Rein lexikalische Konfigurationsprüfung

Der Resolver verwendet ausschließlich die bereits geprüften absoluten
`Path`-Werte und lexikalische `relative_to`-Beziehungen.

Er führt keinen `resolve`, `stat`, `open`, Directory-Scan oder Symlinkzugriff
aus.

Existenz, Owner, Modus, echte Verzeichnisse, Symlinks und Inodes bleiben wie
in LQ-437 festgelegt Aufgabe des direkten LQ-426-Writeraufrufs.

## Keine Environment-Discovery

LQ-438 liest keine Environmentvariable, Kommandozeile, Arbeitsdirectory,
Konfigurationsdatei, Datenbank oder Plattformkonvention.

Es gibt keinen Fallback aus Scope-ID, Handoffname oder Pfadbestandteilen.

Nur der explizit injizierte Konstruktorbestand kann aufgelöst werden.

## Keine Authority

Das Binding enthält und erteilt keine Authority.

Der Resolver akzeptiert keinen Actor, keine Rolle, Membership, Capability
oder caller-gelieferte Allow-Entscheidung.

Aktuelle User-, Scope- und Scopeauthority bleiben vor Reservierung und
Startappend bei den persistenten Grenzen aus LQ-432 und LQ-435.

Ein vorhandenes Binding kann deren neutrales `None` niemals überschreiben.

## Fehlende Binding

Ein nicht konfigurierter Scope ist normale neutrale Abwesenheit und liefert
`None`.

Der Resolver unterscheidet dabei nach außen nicht zwischen unbekanntem und
nicht für diesen Prozess aktiviertem Scope.

Das Ergebnis autorisiert weder Writer noch Reconciliation oder Cleanup.

## Beschädigte Konfiguration

Ein typfremder Bindingwert, eine doppelte Scope-ID oder überlappende
Cross-Scope-Wurzeln wird beim Aufbau fail-fast als `ValueError` abgelehnt.

Eine teilweise nutzbare Resolverinstanz wird nicht veröffentlicht.

Die Fehlertexte enthalten keine konkreten Scope-IDs oder Pfade.

Der Slice benennt keine neue technische Exception.

## Repr und Datenabfluss

Der Resolver definiert keinen inhaltlichen `repr`.

Scope-IDs sowie Source- und Zielpfade werden dadurch nicht als
Objektdarstellung ausgegeben.

Die Bindingwerte selbst schließen diese Felder bereits aus ihrem `repr` aus.

Logging, Metrics und Diagnoseausgabe werden nicht ergänzt.

## Porttreue

Der Adapter erfüllt strukturell
`ManifestHandoffScopeBindingLookup.get_binding(scope_id)`.

Es gibt keine zusätzliche öffentliche Lookupmethode und keinen erweiterten
Portparameter.

Der bestehende Port und die LQ-437-Domaintypen bleiben unverändert.

## Nebenwirkungsfreiheit

Konstruktion und Lookup führen keinerlei Datei-, Datenbank-, Netzwerk-,
Clock-, Random- oder Prozesszugriff aus.

Lookup mutiert weder den Index noch ein Binding.

Wiederholte Auflösung derselben Scope-ID ist innerhalb derselben Instanz
stabil.

## Migration und Wiring

Revision und Head bleiben `20260819_0028`.

LQ-438 ergänzt keine Tabelle, SQL-Abfrage, Migration, Seed- oder
Bootstrapdaten.

Der Resolver wird nicht in CLI, Operator, Route, Compose, Factory, CI oder
Production-Wiring eingebaut.

## Tests

Fokussierte Tests belegen:

- exakte Auflösung und neutrales Fehlen;
- Übernahme eines One-shot-Iterators;
- fehlende Mutationsoberfläche und repr-freie Wurzeln;
- Ablehnung doppelter Scope-IDs;
- Ablehnung gleicher oder verschachtelter Zielwurzeln;
- symmetrische Source-/Zieltrennung über Scopegrenzen;
- bewusst zulässige gemeinsame Sourcewurzel;
- strukturelle Erfüllung des geschlossenen Ports;
- Roadmap- und Folgeslicebindung.

## Nichtziele

LQ-438 implementiert keinen Composer, Writerwrapper, Reconciler,
Execution-Claim, Recovery, Cleanup oder Retentiondeleter.

Es gibt keinen Scope-Bootstrap, keine Bestandsverankerung und keine
persistente Bindingmutation.

Keine Manifestdatei wird gelesen, geschrieben, verschoben oder gelöscht.

## Nächster Slice

LQ-439 sollte den kontrollierten Registry-zu-Writer-Composer aus LQ-436 auf
den geschlossenen LQ-437-Ports und dem statischen Resolver implementieren.

Execution-Recovery, Scope-Bootstrap, Bestandsverankerung, Cleanup und finale
Evidence-Retention bleiben separate spätere Slices.
