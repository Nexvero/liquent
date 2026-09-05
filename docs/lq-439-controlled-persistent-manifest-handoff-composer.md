# LQ-439 — Controlled Persistent Manifest Handoff Composer

## Ergebnis

LQ-439 implementiert die in LQ-436 definierte kontrollierte Composition auf
den geschlossenen Typen und Ports aus LQ-437 sowie dem statischen Resolver aus
LQ-438.

Ein Aufruf kann den direkten Writer höchstens einmal öffnen.

## Öffentliche Grenze

`ControlledPersistentManifestHandoff.handoff(request)` akzeptiert nur den
geschlossenen `ManifestHandoffCompositionRequest`.

Der Caller liefert Reservierungs-ID, authentifizierten Actor, Scope-ID und
Handoffnamen.

Pfade, Attempt-/Observation-IDs, Fakten, Outcome, Rollen und Allow-Booleans
sind keine Eingaben.

## Explizite Abhängigkeiten

Der Konstruktor erhält ausschließlich:

- Binding-Lookup;
- autorisierte Attemptreservierung;
- Writer-Observation-Appender;
- Reconciliation-Observation-Appender;
- direkten Writer;
- direkten Reconciler;
- kontrollierte Observation-ID-Factory.

Es gibt keinen Service-Locator, Defaultresolver, Engineaufbau oder globalen
Dateipfad.

## Nebenwirkungsfreier Aufbau

Der Konstruktor speichert nur die injizierten Abhängigkeiten.

Er liest weder Binding noch Datenbank, Dateisystem, Environment, Clock oder
Randomquelle.

Writer und Reconciler werden erst innerhalb eines bewussten `handoff`-Aufrufs
erreichbar.

## Reihenfolge

Der Composer führt streng aus:

1. exakte aktive Scopebinding auflösen;
2. Attempt mit Requestbindung reservieren;
3. neue Start-Observation-ID intern erzeugen;
4. `writer_started` durable bestätigen;
5. Writer genau einmal mit den gebundenen Wurzeln und persistentem Namen
   aufrufen;
6. direkten Writerausgang durable sichern;
7. nur bei Bedarf frisch reconciliieren und das direkte Ergebnis sichern.

Kein späterer Schritt läuft vor seinem bestätigten Vorgänger.

## Neutrale Binding-Abwesenheit

Fehlende Binding liefert neutral `None` vor jeder Reservierung.

Sie wird nicht aus Request, Environment, aktuellem Verzeichnis oder
Handoffnamen rekonstruiert.

Es erfolgt kein Writer- oder Reconciliationaufruf.

## Autorisierte Reservierung

Die persistente Reservierungsgrenze löst aktuelle User-, Scope- und
Scopeauthority aus dem System of Record auf.

Neutrales `None` beendet den Aufruf ohne Dateizugriff.

Ein `ManifestHandoffReservationConflict` wird zum leeren sichtbaren
`ManifestHandoffCompositionConflict`.

Der Composer prüft, dass der zurückgegebene Attempt exakt an Reservation,
Actor, Scope und Namen des Requests gebunden ist.

## SessionPrincipal und Authority

Der Actor im Request identifiziert nur die authentifizierte Person.

Er trägt keine Authority in den Composer und kann weder Binding noch
Reservierungs- oder Startentscheidung ersetzen.

Ein Authorityentzug vor Reservierung oder Startappend verhindert den Writer
über die aktuellen persistenten Grenzen.

## Startobservation

Die Observation-ID wird unmittelbar vor `record_writer_started` intern
erzeugt und gegen ihren geschlossenen Typ geprüft.

Der Composer akzeptiert keine caller-gelieferte ID.

Nur ein eindeutig zurückgegebenes passendes
`AppendedManifestHandoffObservation` öffnet den Writer.

Neutraler Startappend oder Konflikt startet keine Dateimutation.

## Unklarer Startcommit

Bei detailfreier Registry-Unverfügbarkeit wird derselbe Startappend genau
einmal mit derselben Observation-ID wiederholt.

Bleibt auch der Retry unklar, endet der Aufruf detailfrei technisch
unverfügbar.

Der Writer bleibt in diesem Fall gesperrt.

Die Begrenzung verhindert eine interne Endlosschleife; ein späterer bewusster
Retry bleibt an dieselbe Requestreservierung gebunden.

## Genau ein Writer

Die Composition ruft den Writer nur unmittelbar nach ihrem eigenen
bestätigten Startappend auf.

Sourcewurzel und Zielwurzel kommen ausschließlich aus derselben aufgelösten
Binding; der Name kommt aus dem bestätigten persistenten Attempt.

Der Composer enthält keine Schleife und keinen zweiten Writerpfad.

Nach Writerstart führt auch Reconciliation niemals zu einem Writerretry.

## Direkter Writererfolg

Nur `manifest_handed_off` mit exakt `<handoff_name>.json`, gültigem
SHA-256-Digest und positiver Dateizahl gilt als direkter Erfolg.

Die Fakten werden in `ManifestHandoffFacts` rekonstruiert.

Danach wird `writer_handed_off` mit einer neuen internen Observation-ID
appendiert.

Erst dessen eindeutige Bestätigung erzeugt ein sichtbares bestätigtes
Compositionresult.

## Nicht erfolgreiche Writerausgänge

`target_not_absent` und `source_not_stable` enthalten keine Fakten und führen
nach beendetem Writer direkt zu frischer Reconciliation.

`ManifestHandoffUnavailable` wird ebenfalls als definitiv beendeter
Writeraufruf reconciliiert.

Unbekannte oder widersprüchliche Resulttypen und angebliche Erfolge mit
falschem Filename oder Fakten scheitern technisch fail-closed.

Sie werden nicht in Erfolg umgedeutet.

## Unbekannter Writerausgang

Ein `ManifestHandoffUnknown` wird zuerst als `writer_outcome_unknown` mit
neuer stabiler Observation-ID gesichert.

Nur nach bestätigtem Append folgt frische read-only Reconciliation.

Ist dieser Append neutral, konfliktbehaftet oder nach Retry technisch unklar,
läuft kein Reconciler.

Der Writer wird in keinem Fall wiederholt.

## Frische Reconciliation

Der Reconciler erhält nur Zielwurzel und Namen aus Binding beziehungsweise
bestätigtem Attempt.

Seine fünf geschlossenen Ausgänge werden exakt geroutet:

- `manifest_absent`;
- `manifest_temporary_only`;
- `manifest_handed_off`;
- `manifest_handed_off_pending_cleanup`;
- `manifest_handoff_conflict`.

Es gibt keine erfundene Observation für technische
Reconciliation-Unverfügbarkeit.

## Faktenmatrix

Nur temporary-only, handed-off und handed-off-pending-cleanup tragen Digest
und Dateizahl.

Handed-off und pending-cleanup müssen zusätzlich den exakten finalen
Filename tragen.

Absent und conflict dürfen weder Filename noch Fakten liefern.

Jede Abweichung endet detailfrei technisch unverfügbar vor einem Append.

## Reconciliationresult

Bestätigtes handed-off und handed-off-pending-cleanup liefern das geschlossene
`manifest_handed_off`-Result mit Filename und Fakten.

Absent, temporary-only und conflict liefern nach bestätigtem Append
`reconciliation_required` ohne Filename oder Fakten.

Auch pending-cleanup autorisiert keinen Cleanup.

## Append-Retry und Konflikte

Jeder Outcomeappend erhält genau eine neue kontrollierte Observation-ID.

Technische Registry-Unverfügbarkeit wird einmal mit derselben ID, Methode,
Attemptbindung und denselben Fakten wiederholt.

Ein persistenter Observationkonflikt wird detailfrei als
`ManifestHandoffCompositionConflict` sichtbar.

Neutrales Ergebnis nach bereits ausgeführtem Writer gilt technisch
unverfügbar, nicht als neue Businessablehnung.

## Detailfreie technische Grenze

`ManifestHandoffCompositionUnavailable` besitzt nur den stabilen Code
`manifest_handoff_composition_unavailable`.

Abhängigkeitsfehler, beschädigte Rückgaben und unklare Commits verlassen den
Composer ohne Scope-, Actor-, Pfad-, Observation-, SQL- oder Dateidetail.

Neutrales `None`, Compositionkonflikt und technische Unverfügbarkeit bleiben
getrennte Ausgänge.

## Keine Execution-Recovery

LQ-439 ergänzt keinen persistenten Execution-Claim, Lease, Heartbeat oder
Prozessabschlussnachweis.

Ein neuer Prozess darf ein bereits gestartetes Attempt nicht allein nach
Zeitablauf reconciliieren oder erneut schreiben.

Das offene Crashfenster zwischen Startappend und Outcomesicherung bleibt
explizit erhalten.

## Keine Cleanup-Composition

Der Composer ruft LQ-428 nicht auf.

Pending-cleanup bleibt ein beobachteter Manifestzustand ohne Löschfreigabe.

Cleanup benötigt eine separate aktuelle Authorityentscheidung und eigene
kontrollierte Composition.

## Persistenz und Retention

LQ-439 nutzt ausschließlich die bestehenden LQ-432-/LQ-435-Grenzen und
Revision `20260819_0028`.

Reservierung und Observationen bleiben append-only und geben Scope, Name oder
Attempt nicht wieder frei.

Es gibt keine Tabelle, Migration, Seed-, Bootstrap- oder Retentionmutation.

## Kein Wiring

Der Slice ergänzt keine CLI, Route, Factory, Compose-, CI- oder
Productionverdrahtung.

Der Composer besitzt keine Engine und schließt keine injizierte Ressource.

Der direkte operative Start bleibt einer späteren owner-kontrollierten Grenze
vorbehalten.

## Tests

Fokussierte Tests belegen:

- neutrales fehlendes Binding vor Reservierung;
- exakte Reihenfolge und genau einen gebundenen Writeraufruf;
- Retry desselben Startappend mit derselben Observation-ID;
- Writerblockade bei neutralem oder dauerhaft unklarem Start;
- detailfreie Reservierungs- und Observationkonflikte;
- unknown-Sicherung vor frischer Reconciliation;
- Routing nicht erfolgreicher Writerausgänge;
- geschlossene Fakten- und Filenamevalidierung;
- Roadmap- und Folgeslicebindung.

## Nichtziele

LQ-439 implementiert keinen Scope-Bootstrap, keine Bestandsverankerung,
Execution-Recovery, Cleanup- oder Retentioncomposition.

Es gibt keine reguläre Bindingpersistenz oder Bindingmutation.

Staging, Commit, Push, Build, Veröffentlichung und Deployment werden weder
ausgeführt noch autorisiert.

## Nächster Slice

LQ-440 sollte das offene Execution-Ownership- und Recoveryproblem für bereits
gestartete Attempts als separaten Vertrag definieren.

Scope-Bootstrap, Bestandsverankerung, Cleanup-Composition und finale
Evidence-Retention bleiben danach weiterhin getrennt.
