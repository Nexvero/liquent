# LQ-272 — Persistent Publication Work State and Current Outcome Finalization

## Ergebnis

LQ-272 implementiert die beiden in LQ-271 eingefrorenen persistenten Ports:

- den vollständig gebundenen Publication-Work-State-Lookup;
- den Current-Outcome-Finalizer mit genau einer Providerinspektion.

Damit kann die providerneutrale Einzelarbeits-Composition ihren nächsten
zulässigen Schritt aus dem System of Record bestimmen und ein Unknown-Outcome
ohne doppelte Providerabfrage abschließen.

## Persistenter State-Lookup

`DatabaseReleasePublicationWorkStateLookup` erhält eine Engine und den
vollständigen `ReleasePublicationWorkRequest`.

Der Lookup ist read-only. Er erzeugt weder Execution noch Attempt, Recovery,
Receipt oder Reassessment.

Jeder Aufruf liest den aktuellen Datenbankbestand neu und hält keinen positiven
State- oder Authority-Cache.

## Vollständige Referenzbindung

Die Abfrage löst eine Execution ausschließlich über ihre stabile Execution-ID
auf und vergleicht anschließend exakt:

- Handoff-ID;
- Publisher-Authority-ID;
- Channel-ID;
- Channel-Policy-Revision.

Alle vier Werte müssen in jeder aufgelösten Attempt-Zeile bytegleich derselben
Execution zugeordnet sein.

Ein Caller kann weder durch eine bekannte Execution-ID einen fremden Handoff
adressieren noch Channel oder Publisher austauschen.

## Neutrale Abwesenheit und Mismatch

Eine unbekannte Execution liefert neutral `None` und offenbart keine
Handoff-, Channel- oder Authority-Details.

Eine vorhandene Execution mit nicht passender geschlossener Referenz liefert
den typisierten Zustand `not_actionable`.

Dadurch startet die LQ-271-Composition bei einem Mismatch keinen neuen
Preflight, der den Unterschied als Konfliktdetail sichtbar machen könnte.

Technisch beschädigte oder widersprüchliche Persistenz bleibt davon getrennt
und detailfrei nichtverfügbar.

## Vollständiges Attempt-Inventar

Der Lookup akzeptiert ausschließlich ein oder zwei Attempts.

Attempt-Nummern müssen lückenlos bei 1 beginnen und mit der sortierten
Persistenz übereinstimmen.

Mehr als zwei Attempts, doppelte Nummern, eine fehlende Attempt-1-Bindung oder
unbekannte Statuskombinationen werden fail-closed abgelehnt.

Attempt 3 ist damit auch an dieser persistenten Grenze nicht darstellbar.

## Vorbereiteter Zustand

Execution `prepared` mit Attempt `prepared` wird abhängig von der
Attempt-Nummer als Attempt 1 oder Attempt 2 vorbereitet aufgelöst.

Ein nach Prozessabbruch verbliebener Attempt `write_started` wird ebenfalls an
den passenden bestehenden Creator zurückgegeben.

Der Creator erkennt diesen Zustand, persistiert `outcome_unknown` und führt
keinen weiteren Provider-Create aus.

Damit bleibt Crash-Wiederaufnahme vor der Unknown-Sicherung fail-closed.

## Unknown-Zustand

Execution und aktueller Attempt müssen gemeinsam `outcome_unknown` sein.

Der Attempt darf keine Finish-Zeit tragen und muss der erwarteten Nummer 1 oder
2 entsprechen.

Nur dann liefert der Lookup `attempt_one_unknown` beziehungsweise
`attempt_two_unknown`.

LQ-271 routet diese Zustände direkt zum read-only Current-Outcome-Finalizer und
niemals zu einem Creator.

## Abgeschlossene Attempt-1-Abwesenheit

Attempt 1 wird nur dann als `attempt_one_absence_recovered` aufgelöst, wenn:

- Attempt 1 `reconciled` und abgeschlossen ist;
- genau der Recovery-Fakt `absence_confirmed` gebunden ist;
- kein Receipt an diesem Attempt hängt;
- Execution wieder `prepared` ist;
- die persistierte Current-Authority-Aussage typisiert ist.

Der Boolean wird nicht als Worker-Allow übernommen. Der bestehende Attempt-2-
Preflight prüft alle aktuellen Fakten erneut und kann neutral ablehnen.

## Attempt-2-Bindung

Ein zweiter Attempt ist nur gültig, wenn Attempt 1 als bestätigte Abwesenheit
vollständig reconciled vorliegt.

Erst danach kann Attempt 2 als `prepared`, `write_started` oder
`outcome_unknown` aufgelöst werden.

Die State-Abfrage erfindet keine Retry-Berechtigung und erzeugt keine neue
Attempt-ID.

## Terminale Zustände

Der Lookup bildet ausschließlich persistierte terminale Fakten ab:

- `published` mit passender Receipt-Reconciliation;
- `published_reassessment_required` mit passender Receipt-Reconciliation;
- `not_published` mit abgeschlossener Absence-Recovery;
- `publication_conflict` mit abgeschlossener Conflict-Recovery.

Attempt und Finish-Zeit müssen zum terminalen Zustand passen.

Der historische Attempt-1-Konflikt bleibt kompatibel: Seine reconciled
Conflict-Recovery wird auch bei dem älteren Execution-Status
`outcome_unknown` als terminaler `publication_conflict` aufgelöst.

## Strukturelle Beschädigung

Als technische Nichtverfügbarkeit gelten insbesondere:

- mehr als zwei Attempts;
- lückenhafte Attempt-Nummern;
- unbekannte Execution- oder Attempt-Statuswerte;
- Finish-Zeit im offenen Zustand oder fehlende Finish-Zeit im Abschluss;
- Attempt 2 ohne bestätigte Attempt-1-Abwesenheit;
- terminaler Published-Status ohne passende Receipt-Reconciliation;
- terminale Absence-/Conflict-Behauptung ohne Recovery-Fakt;
- ungültig codierte oder leere persistente IDs.

Keine dieser Situationen wird als neutrale Abwesenheit oder Uploadfreigabe
interpretiert.

## Current-Outcome-Finalizer

`DatabaseReleasePublicationCurrentOutcomeFinalizer` komponiert:

- die bestehende read-only Unknown-Outcome-Reconciliation;
- den bestehenden Receipt-Finalizer;
- den bestehenden Recovery-Finalizer.

Er implementiert den LQ-271-Port ohne Provider- oder Ergebnisfamilien zu
duplizieren.

## Exakter Retry vor Providerzugriff

Vor einer neuen Inspection fragt der Current-Outcome-Finalizer nach einem
bereits vorhandenen Receipt- oder Recovery-Abschluss für exakt Execution und
Attempt.

Ein vorhandener Abschluss wird unverändert zurückgegeben.

Dabei werden weder Inspector noch ID-Generator oder Clock aufgerufen.

## Genau eine Reconciliation

Liegt kein Abschluss vor, wird
`reconcile_unknown_outcome(execution_id, attempt_id)` genau einmal aufgerufen.

Das typisierte Ergebnis entscheidet den einzigen Commitpfad:

- `published_confirmed` erreicht ausschließlich den Receipt-Finalizer;
- `absence_confirmed` oder `conflict` erreicht ausschließlich den Recovery-
  Finalizer;
- neutral `None` bleibt pending und erzeugt keine Mutation.

Success- und Recovery-Finalizer werden nicht probeweise nacheinander mit
eigenen Providerinspektionen aufgerufen.

## Commit eines bereits reconcilierten Outcomes

Beide bestehenden Finalizer besitzen nun additive interne öffentliche Methoden
für:

- read-only Auflösung eines exakten vorhandenen Abschlusses;
- Commit eines bereits typisierten reconcilierten Outcomes.

Diese Methoden prüfen Execution-, Attempt- und Outcome-Art erneut und verwenden
dieselben bestehenden atomaren `_commit`-Pfade.

Die bisherige API `finalize_reconciliation` beziehungsweise
`finalize_recovery` bleibt unverändert und vollständig kompatibel.

## Aktuelle Fakten beim Commit

Die Weitergabe eines Reconciliation-Objekts ist kein Commit-Ticket.

Die bestehenden Commitpfade sperren und prüfen weiterhin aktuell:

- Execution- und Attempt-Unknown-Zustand;
- Handoff-, Channel- und Zielbindung;
- Paketversion und Wheel-Hash;
- Receipt- und Recovery-Abwesenheit;
- Channel-, Publisher-, Registry-, Signer- und Key-Authority;
- vorhandenes `pending` Reassessment.

Revocation zwischen Inspection und Commit wird deshalb weiterhin korrekt als
Reassessment oder fehlende Retry-Freigabe bewahrt.

## Konkurrenz

Der vorangestellte Existing-Lookup ist eine Optimierung für exakte Retries,
nicht die Atomizitätsgrenze.

Konkurrierende Prozesse werden weiterhin durch die bestehenden PostgreSQL-
Locks, Unique Constraints und erneuten Existing-Prüfungen im Commit
serialisiert.

Es kann höchstens ein Receipt oder Recovery-Fakt für Execution und Attempt
wirksam werden.

## Fehlergrenzen

`ReleasePublicationWorkStateUnavailable` vereinheitlicht State-Abfrage-,
Decode-, Struktur- und Datenbankfehler.

`ReleasePublicationCurrentOutcomeFinalizeUnavailable` vereinheitlicht
Reconciliation-, Finalizer-, Typ- und Infrastrukturfehler.

Beide Fehler tragen ausschließlich ihren stabilen Code. SQL, IDs,
Observations, Providerdetails, Pfade, Hashes und Credentials werden nicht
weitergegeben.

Die LQ-271-Application-Grenze vereinheitlicht sie anschließend weiterhin als
detailfreie `ReleasePublicationWorkUnavailable`.

## Keine neue Persistenz

LQ-272 verwendet ausschließlich die bestehenden Tabellen für:

- Executions und Attempts;
- Recovery-Entscheidungen;
- Receipts und Receipt-Reconciliations;
- Reassessments.

Es gibt keine neue Tabelle, Spalte, Constraint, Migration oder Seed-
Entscheidung.

Der Migration-Head bleibt `20260819_0024` mit 24 Migrationen.

## Bewusst nicht enthalten

LQ-272 ergänzt keine:

- vollständige Engine-/Artifact-/Provider-Composition des Workers;
- owner-only Worker-Requestdatei;
- CLI-, Exitcode- oder Ausgabeentscheidung;
- Scheduler-, Queue-, Daemon- oder Service-Unit-Integration;
- HTTP-, OIDC- oder Research-Verdrahtung;
- Credential-, Provider-, Git- oder Deploymentmutation.

## Nachweis

SQLite-Tests belegen:

- Prepared- und Unknown-Auflösung;
- neutrale unbekannte und mismatched Referenzen;
- genau eine Providerinspektion beim Published-Abschluss;
- genau eine Providerinspektion beim Absence-Abschluss;
- terminale State-Auflösung nach Receipt;
- Attempt-1-Recovery-Auflösung nach Abwesenheit;
- exakten Finalizer-Retry ohne weitere Providerinspektion;
- unveränderte Kompatibilität beider bestehenden Finalizer-APIs.

Ein PostgreSQL-16-Test belegt dieselbe gebundene Unknown-Auflösung, genau eine
Inspection, atomaren Receipt-Commit und terminale Wiederauflösung auf der
maßgeblichen Produktionsdatenbank.

Die vollständige Pflichtsuite besteht mit 3327 Tests und 566 Warnungen ohne
übersprungene PostgreSQL-Pfade.

LQ-273 implementiert als nächsten Slice die vollständige lokale Worker-
Composition aus Engine, Artifact-Integrity, persistenten Publication-Adaptern
und der LQ-269-Package-Index-Composition, weiterhin ohne CLI oder Scheduler.
