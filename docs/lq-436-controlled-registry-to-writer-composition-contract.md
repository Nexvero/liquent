# LQ-436 — Controlled Registry-to-Writer Composition Contract

## 1. Zweck und Status

LQ-436 definiert die kontrollierte Composition von persistenter
Handoffreservierung, stabilem Registry-Scope, privater Zielwurzel,
`writer_started`, LQ-426-Writer und LQ-427-Reconciliation.

Der Slice implementiert noch keinen Composer, Resolver oder Operator.

Cleanup bleibt außerhalb dieser Composition.

## 2. Verantwortungsgrenzen

Die Registry verantwortet dauerhafte Scope-/Name-/Attempt-Bindung und
Observationhistorie.

Der Scopebinding-Resolver verantwortet ausschließlich die stabile Zuordnung
eines Registry-Scopes zu kontrollierten Source- und Zielwurzeln.

Der Writer erzeugt und bindet ausschließlich das kanonische Manifest.

Der Reconciler beobachtet ausschließlich den aktuellen Dateizustand.

Die Composition ordnet diese Grenzen, ersetzt aber keine ihrer Entscheidungen.

## 3. Caller-Eingaben

Ein späterer bewusster Compositionaufruf darf ausschließlich erhalten:

- stabile Reservierungs-ID als Retryanker;
- authentifizierten Actor zur Identifikation;
- Registry-Scope-ID;
- validierten neuen Handoffnamen.

Nicht akzeptiert werden Source- oder Zielpfad, Tempname, Attempt-ID,
Observation-ID, Digest, Dateizahl, Outcome, Allow-Boolean, Rolle oder
Authoritysnapshot.

SessionPrincipal identifiziert den Actor, erteilt aber keine Registryauthority.

## 4. Stabile Scopebindung

Ein kontrollierter Resolver bindet jede `ManifestHandoffRegistryScopeId`
höchstens an genau eine Sourcewurzel und eine private Zielwurzel.

Die Bindung ist nicht aus Callerwerten, Environment-Fallback, aktuellem
Arbeitsverzeichnis oder Handoffnamen abgeleitet.

Ein Scope darf während seiner gesamten Lebensdauer nicht auf einen anderen
Namensraum, eine andere Source oder einen anderen Owner reassigned werden.

Umzug oder Ersatz benötigt einen neuen Scope und eine separate
Bestandsverankerung; bestehende Attempts bleiben am alten Scope.

## 5. Resolverausgang

Der Resolver liefert entweder genau eine geschlossene Binding oder neutral
keine aktive Binding.

Mehrdeutige, beschädigte, fremde oder technisch nicht lesbare Binding ist
detailfreie technische Unverfügbarkeit.

Pfade, Ownername, Hostdetails und Konfigurationsquelle werden nicht nach außen
gegeben.

Fehlende oder inaktive Binding verhindert Reservierung und Writerstart.

## 6. Pfadgrenzen bleiben beim Writer

Die Binding ersetzt keine LQ-426-Pfadvalidierung.

Unmittelbar beim Writeraufruf werden Source und Ziel erneut komponentenweise
auf echte Verzeichnisse, Owner, Symlinkfreiheit, Trennung und Zielmodus `0700`
geprüft.

Die Composition repariert oder erstellt keine Wurzel und folgt keinem
Symlink.

## 7. Kontrollierte Abhängigkeiten

Die Composition erhält explizit:

- Scopebinding-Resolver;
- autorisierte LQ-432-Reservierung;
- LQ-435-Observation-Appender;
- direkten LQ-426-Writer;
- direkten LQ-427-Reconciler;
- getrennte sichere Factories für jede benötigte Observation-ID.

Sie erzeugt keine Engine, liest keinen DSN und entdeckt keine Abhängigkeit
global oder aus einem Service-Locator.

Aufbau führt weder Datenbank- noch Dateisystemzugriff aus.

## 8. Kontrollierte Reihenfolge

Für einen neuen Versuch gilt exakt:

1. aktive stabile Scopebinding read-only auflösen;
2. Namen über LQ-432 durable reservieren;
3. intern stabile Start-Observation-ID erzeugen;
4. `writer_started` über LQ-435 durable appendieren;
5. nur nach eindeutig bestätigtem Startappend den Writer genau einmal direkt
   mit gebundener Source, Ziel und registriertem Namen aufrufen;
6. tatsächlichen Writerausgang mit neuer kontrollierter Observation-ID sichern;
7. falls erforderlich frisch reconciliieren und dieses direkte Ergebnis
   appendieren.

Kein Schritt wird übersprungen oder aus Callerbehauptungen ersetzt.

## 9. Reservierungsretry

Eine Wiederholung verwendet dieselbe Reservierungs-ID, Actor-, Scope- und
Namensbindung.

LQ-432 liefert bei exakter Wiederholung dasselbe Attempt ohne zweite
Reservierung.

Divergenter Retry oder dauerhaft belegter Name endet detailfrei ohne
Writerstart.

Ein reserviertes Attempt ist keine Erlaubnis, den Writer aufzurufen; erst der
committete Startappend bildet diese Grenze.

## 10. Startappend und unklarer Registry-Commit

Der Startappend verwendet eine intern kontrollierte stabile Observation-ID.

Bei technischer Unverfügbarkeit oder unklarem Commit wird ausschließlich
derselbe Startappend mit derselben ID wiederholt.

Der Writer bleibt gesperrt, bis LQ-435 eindeutig denselben committeten
`writer_started`-Fakt liefert.

Konflikt, neutrales Stale oder nicht auflösbare Unverfügbarkeit startet keinen
Writer.

## 11. Genau ein Writeraufruf

Die aktuelle Compositioninstanz darf den Writer nur unmittelbar nach ihrem
eigenen eindeutig bestätigten neuen Startappend aufrufen.

Ein Retry, Prozessneustart oder eine andere Instanz, die bereits
`writer_started` vorfindet, darf den Writer niemals erneut aufrufen.

Diese Grenze gilt auch bei `manifest_absent`, Sourceänderung, Timeout oder
fehlender Finaldatei.

Die Attempt- und Namensbindung bleibt dauerhaft verbraucht.

## 12. Crashfenster und Ausführungseigentum

Zwischen committetem `writer_started` und gesichertem Ausgang kann der
ursprüngliche Prozess noch laufen oder abgestürzt sein.

Die Registry enthält derzeit keinen persistenten Execution-Claim, keine Lease
und keinen Prozessabschlussnachweis.

Eine zweite Instanz darf deshalb nicht allein aufgrund von Zeitablauf parallel
reconciliieren oder Recovery starten.

Recovery ist nur owner-kontrolliert zulässig, nachdem das Ende des
ursprünglichen Prozesses außerhalb dieser Composition eindeutig belegt wurde.

LQ-436 führt keinen Timeout, Heartbeat, Claim oder Scheduler ein.

## 13. Writererfolg

Nur ein direkt zurückgegebenes `manifest_handed_off` wird mit Digest und
Dateizahl in `ManifestHandoffFacts` überführt und als `writer_handed_off`
appendiert.

Filename muss dem registrierten Namen plus `.json` entsprechen.

Fehlende, zusätzliche oder widersprüchliche Writerfakten sind technische
Unverfügbarkeit und kein Erfolg.

Ist der Ergebnisappend technisch unklar, wird nur derselbe Append mit derselben
Observation-ID wiederholt; der Writer wird nicht wiederholt.

## 14. Writer-unknown

Ein direkt gefangener `ManifestHandoffUnknown` wird zuerst als
`writer_outcome_unknown` mit stabiler Observation-ID gesichert.

Erst nach eindeutigem Commit dieser Observation folgt frische LQ-427-
Reconciliation gegen exakt dieselbe Binding und denselben registrierten Namen.

Kein unbekannter Ausgang wird als Erfolg, Abwesenheit oder Retryfreigabe
interpretiert.

## 15. Andere Writerausgänge

`target_not_absent`, `source_not_stable` und
`ManifestHandoffUnavailable` erzeugen keinen erfundenen Writererfolg.

Da `writer_started` bereits committet ist, folgt nach definitiv beendetem
Writeraufruf eine frische Reconciliation.

Ist der Writerprozess nicht nachweisbar beendet, gilt weiterhin die
Ausführungseigentumsgrenze aus Abschnitt 12.

## 16. Reconciliation-Routing

Der Reconciler erhält ausschließlich Zielwurzel und Namen aus der Binding und
dem persistenten Attempt.

Seine fünf direkten Ergebnisse werden exakt auf die fünf getrennten LQ-434-
Methoden abgebildet.

Digest und Dateizahl werden nur für die drei manifesttragenden Ergebnisse
übernommen.

Technische Reconciliation-Unverfügbarkeit erzeugt keine Observation und keine
weitere Mutation.

## 17. Reconciliation-Append-Retry

Vor jedem Append erzeugt die kontrollierte Composition genau eine stabile
Observation-ID.

Ein unklarer Registry-Commit wird mit derselben ID, Attemptbindung, Methode und
denselben direkt abgeleiteten Fakten wiederholt.

Der Reconciler muss dafür nicht erneut laufen, solange sein typisiertes
Ergebnis im selben aktiven kontrollierten Aufruf unverändert vorliegt.

Nach Prozessverlust benötigt ein neuer Reconciliationlauf eine neue
Observation-ID und eine neue frische Dateibeobachtung.

## 18. Authority und Entzug

Reservierung und neuer Startappend lösen aktuelle Authority aus dem System of
Record auf.

Entzug vor Start verhindert jede Dateimutationsgrenze.

Entzug nach Start verhindert nicht die mechanische Sicherung des bereits
eingetretenen Writer- oder Reconciliationausgangs.

Er autorisiert jedoch weder Cleanup noch einen neuen Writer- oder
Recoveryvorgang.

## 19. Sichtbarer Ausgang

Die Composition darf höchstens neutral abgelehnt, detailfrei konfliktbehaftet,
detailfrei technisch unverfügbar, Reconciliation erforderlich oder
manifest-handoff bestätigt unterscheiden.

Ein bestätigter Handoff enthält nur Attempt-ID, finalen Dateinamen, Digest und
Dateizahl sowie explizite Nichtautorisierung von Staging und Commit.

Interne Scopebinding, Pfade, Observation-IDs, Actor-, Authority-, SQL- und
Fehlerdetails bleiben verborgen.

## 20. Keine Cleanup-Composition

Pending-cleanup ist ein sichtbarer reconciled Zustand, aber LQ-436 ruft
LQ-428 nicht auf.

Cleanup benötigt einen separaten bewussten Operationsstart mit aktueller
Authority und eigener Composition.

Die Writer-Composition löscht keine Temp- oder Finaldatei.

## 21. Retention und Nichtwiederverwendung

Reservierung, Start und alle Outcomeobservationen bleiben append-only erhalten.

Kein Compositionausgang gibt Scope, Namen oder Attempt zur Wiederverwendung
frei.

Finale Manifestdatei bleibt einer separaten owner-kontrollierten
Retentionentscheidung unterworfen.

Der Vertrag bestimmt keine Frist oder Löschoberfläche.

## 22. Nichtziele

LQ-436 ergänzt keinen Domain-Typ, Port, Adapter, Resolver, Composer, Claim,
Lease, Migration, Tabelle, Constraint, Bootstrap, Operator, CLI, Route oder
Wiring.

Er führt keinen echten Writer, Reconciler, Handoff oder Dateizugriff aus.

Es gibt keine Staging-, Commit-, Push-, Build-, Signatur-, Promotion-,
Publication- oder Deploymentauthority.

## 23. Nächster Slice

LQ-437 sollte geschlossene Scopebinding- und Compositiontypen sowie Ports
konkretisieren, ohne bereits Dateimutationen oder Production-Wiring
einzuführen.

Execution-Claim/Recovery, Scope-Bootstrap, Bestandsverankerung, Cleanup-
Composition und finale Evidence-Retention bleiben separat.
