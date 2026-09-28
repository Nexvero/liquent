# LQ-433 — Controlled Manifest Handoff Observation Append Contract

## 1. Zweck und Status

LQ-433 definiert den kontrollierten Appendvertrag für historiesichere
Beobachtungen eines persistent reservierten Manifest-Handoffattempts.

Der Vertrag verbindet später intern kontrollierte Writer-, Reconciliation-
und Cleanupausgänge mit der LQ-431-Observationhistorie.

Dieser Slice implementiert keinen Port, Adapter oder Compositionpfad.

## 2. Keine frei beschreibbare Eventgrenze

Es gibt keinen generischen Aufruf `append(attempt, kind, payload)` für
Transport, Operator oder untrusted Applicationcode.

Ein Caller darf insbesondere nicht liefern:

- Observationkind oder Erfolgsboolean;
- Sequenznummer oder aktuelle Registryrevision;
- Digest oder Dateizahl;
- finalen oder temporären Pfad;
- Scope, Namen oder Actor als Override des Attempts;
- bereits genehmigte Authority.

Jede Observationart benötigt eine intern kontrollierte quellenspezifische
Grenze.

## 3. Autoritative Quellen

Zulässige Quellen sind ausschließlich:

- der direkte kontrollierte Aufruf des LQ-426-Writers;
- dessen intern gefangener Erfolg oder Outcome-unknown;
- ein im selben kontrollierten Ablauf frisch erzeugtes LQ-427-Ergebnis;
- der direkte kontrollierte Aufruf des LQ-428-Cleanups;
- dessen intern gefangener Erfolg oder Cleanup-unknown.

CLI-JSON, Exitcode allein, Logzeile, Datei des Callers oder rekonstruierter
Dictionarywert sind keine autoritative Quelle.

## 4. Attemptbindung

Vor jedem Append wird das Attempt aus der Registry anhand seiner stabilen
`ManifestHandoffAttemptId` geladen.

Scope, Handoffname, ursprünglicher Actor und Reservierungsentscheidung stammen
ausschließlich aus diesem persistenten Fakt.

Der kontrollierte Dateiaufruf verwendet genau den registrierten Namen und den
zum Scope kontrolliert konfigurierten privaten Zielpfad.

Ein frei gelieferter Pfad oder Name kann keine Observation für das Attempt
erzeugen.

## 5. Startbeobachtung

`writer_started` muss durable committed sein, bevor der Writer erstmals eine
mögliche Dateisystemmutation ausführt.

Der Startappend ist nur nach:

- vorhandener initialer `reserved`-Observation;
- aktueller aktiver User-, Scope- und exakter Scopeauthority;
- kontrollierter Scope-zu-Zielwurzel-Bindung

zulässig.

Ohne bestätigten Startappend wird der Writer nicht aufgerufen.

## 6. Kein zweiter Writerlauf

Sobald `writer_started` historiesicher existiert, darf weder Retry noch
Prozessneustart einen zweiten Writeraufruf für dieses Attempt auslösen.

Ein verlorener oder technisch unklarer Writerausgang routet ausschließlich zu
frischer read-only Reconciliation.

Auch `manifest_absent` nach einem gestarteten Attempt gibt den Namen nicht frei
und erlaubt keinen neuen Writerlauf.

## 7. Direkte Writerausgänge

Ein kontrollierter `manifest_handed_off`-Erfolg des Writers wird als
`writer_handed_off` angehängt.

Digest und Dateizahl werden ausschließlich aus dem unveränderten Writerresultat
übernommen, das seinerseits aus kanonischen Bytes abgeleitet wurde.

Ein intern gefangener `ManifestHandoffUnknown` wird ohne zusätzliche Details
als `writer_outcome_unknown` angehängt.

Andere Writerausgänge erzeugen keinen erfundenen Writerstatus.

## 8. Definitive Writerablehnung oder Unverfügbarkeit

`target_not_absent`, `source_not_stable` und technische Fehler mit definitiv
ausgeschlossenem Bindeeffekt erhalten keine frei ergänzte Observationart.

Nach bereits committetem `writer_started` folgt stattdessen eine frische
LQ-427-Reconciliation.

Nur deren tatsächliche Beobachtung darf anschließend angehängt werden.

Ist Reconciliation technisch unverfügbar, bleibt `writer_started` der letzte
persistente Fakt und jede weitere Mutation gesperrt.

## 9. Reconciliation-Observationen

Die fünf zulässigen dateibasierten Observationen entsprechen exakt LQ-427:

- `manifest_absent`;
- `manifest_handed_off`;
- `manifest_temporary_only`;
- `manifest_handed_off_pending_cleanup`;
- `manifest_handoff_conflict`.

Sie werden ausschließlich aus dem direkt zurückgegebenen typisierten
Reconciliationresultat abgeleitet.

Digest und Dateizahl werden nur übernommen, wenn LQ-427 sie für diesen Ausgang
selbst geliefert hat.

Technische Reconciliation-Unverfügbarkeit erzeugt keine Observation.

## 10. Cleanup-Observationen

Cleanup darf nur aus einer aktuell letzten
`manifest_handed_off_pending_cleanup`-Observation gestartet werden.

Vor der Mutation führt LQ-428 seine eigene frische Reconciliation und
Inodebindung weiterhin vollständig aus.

Belegter Cleanupabschluss wird als `cleanup_completed` angehängt.

Ein intern gefangener technisch unbekannter Ausgang nach möglicher Entfernung
wird als `cleanup_outcome_unknown` angehängt und routet erneut ausschließlich
zu LQ-427.

Nicht anwendbarer Cleanup, Konflikt oder technische Unverfügbarkeit vor
Mutation erzeugen keine erfundene Cleanup-Erfolgsobservation.

## 11. Authority vor und nach externer Mutation

Aktuelle Registryauthority ist erforderlich, bevor ein neuer Writer- oder
Cleanupvorgang gestartet wird.

Nach Start der kontrollierten Operation muss deren tatsächlicher Ausgang
jedoch auch dann historiesicher angehängt werden können, wenn User, Scope oder
Authority zwischenzeitlich deaktiviert wurden.

Ergebnisappend ist mechanische Evidenzsicherung für ein bereits autorisiertes
Attempt und keine neue fachliche Mutationsauthority.

Entzug sperrt jeden später neu begonnenen Writer-, Cleanup- oder autorisierten
Lookup, darf aber die Sicherung eines bereits eingetretenen Ausgangs nicht
unterdrücken.

## 12. Kontrollierter Retryanker

Jeder Append besitzt eine intern kontrolliert erzeugte stabile
`ManifestHandoffObservationId` als technischen Retryanker.

Die Composition muss dieselbe ID für die exakte Wiederholung nach unklarem
Registry-Commit verwenden.

Ein exakter Retry derselben Observation-ID, Attempt-ID, Quellenart und
abgeleiteten Fakten liefert die bereits committete Observation ohne zweite
Zeile oder neue Sequenz.

Dieselbe Observation-ID mit abweichender Bindung ist ein detailfreier
Konflikt.

Die ID ist kein Transportparameter für untrusted Caller.

## 13. Serverseitige Reihenfolge

Die nächste Sequenznummer wird ausschließlich innerhalb der atomaren
Persistenztransaktion bestimmt.

Der Adapter sperrt oder serialisiert das exakte Attempt und seine aktuelle
Observationhistorie im normativen Persistenzsystem.

Prüfung des erlaubten Übergangs, Vergabe der nächsten positiven Sequenz,
serverseitige UTC-Zeit und Append committen atomar oder vollständig nicht.

Caller-seitiges `max(sequence)+1`, In-Process-Lock oder Last-write-wins ist
unzulässig.

## 14. Erlaubte Übergänge

Die initiale Sequenz 1 bleibt immer `reserved`.

Die Mindestordnung lautet:

- `reserved` → einmalig `writer_started`;
- `writer_started` → Writererfolg, Writer-unknown oder frische
  Reconciliationbeobachtung;
- `writer_outcome_unknown` → ausschließlich frische Reconciliation;
- `manifest_handed_off_pending_cleanup` → Cleanupabschluss,
  Cleanup-unknown oder erneute Reconciliation;
- `cleanup_outcome_unknown` → ausschließlich frische Reconciliation;
- jede dateibasierte Observation → spätere frische read-only
  Reconciliation desselben Attempts.

`writer_handed_off`, `manifest_handed_off` und `cleanup_completed` erlauben
keinen weiteren Writerlauf.

Konflikt erlaubt nur Untersuchung oder spätere read-only Reconciliation.

## 15. Wiederholte Beobachtungen

Eine spätere frische Reconciliation darf denselben sichtbaren Zustand erneut
bestätigen und als neue Observation anhängen, wenn sie zu einem neuen
kontrollierten Untersuchungsvorgang gehört.

Sie überschreibt oder komprimiert ältere Observationen nicht.

Technischer Retry derselben Observation-ID erzeugt dagegen niemals eine neue
Sequenz.

## 16. Neutrale Ablehnung und technische Unverfügbarkeit

Stale Übergang, fehlendes Attempt oder unzulässiger Operationsstart endet
neutral ohne Append und ohne Dateimutationen.

Abweichende Wiederverwendung einer Observation-ID ist ein detailfreier
Konflikt.

Beschädigte Historie, Sequenzlücken, unbekannte Observationart, unbrauchbare
Clock oder Infrastrukturfehler bleiben getrennte detailfreie technische
Unverfügbarkeit.

LQ-433 benennt noch keine neuen Exceptions oder Transportabbildungen.

## 17. Ausgabegrenze

Erfolg darf höchstens Attempt-ID, Observation-ID, Sequenz, Observationart,
serverseitige Zeit und zulässige Manifestfakten zurückgeben.

Scopepfad, Tempname, SQL-, DSN-, Actor- und Authoritydetails bleiben intern.

Kein Ergebnis autorisiert Staging, Commit, Push, Build, Signatur, Promotion,
Publication oder Deployment.

## 18. Retention und Nichtwiederverwendung

Observationen sind append-only und werden weder bei Cleanup noch bei finaler
Manifestretention entfernt oder umgeschrieben.

Sie bleiben mindestens solange erhalten, wie Attempt-Nichtwiederverwendung,
Unknown-Auflösung, Incidentuntersuchung oder Audit davon abhängen.

Die dauerhafte Scope-/Name-Bindung überdauert weiterhin jede Observation- und
Dateievidenz.

Dieser Slice bestimmt keine konkrete Frist oder Archivstrategie.

## 19. Nichtziele

LQ-433 ergänzt keinen Domain-Typ, Port, Adapter, Tabellenwert, Constraint,
Migration, Writerwrapper, Bootstrap, Operator, CLI, Route oder Wiring.

Es wird kein echter Writer, Reconciler oder Cleanup ausgeführt.

Scope-Bootstrap, Bestandsverankerung und finale Evidence-Retention bleiben
separate Entscheidungen.

## 20. Nächster Slice

LQ-434 sollte die geschlossenen Observation-Append-Fakten und
quellenspezifischen Ports konkretisieren, ohne bereits Writer-Composition oder
Production-Wiring einzuführen.
