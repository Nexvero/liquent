# LQ-263 — Read-only Release Publication Attempt-Two Reconciliation

## Ergebnis

LQ-263 erweitert die bestehende Unknown-Outcome-Reconciliation kontrolliert
auf Attempt 2.

Nach einem möglichen LQ-262-Provider-Effekt kann das System nun bestätigten
bytegleichen Erfolg, bestätigte Abwesenheit, Konflikt und technisch weiterhin
unklaren Zustand unterscheiden, ohne erneut zu schreiben.

## Wiederverwendete Grenze

Der bestehende Port `ReleasePublicationUnknownOutcomeReconciliation` bleibt
unverändert.

`reconcile_unknown_outcome` akzeptiert weiterhin ausschließlich:

- bestehende Execution-ID;
- bestehende Attempt-ID.

Es gibt keinen caller-gelieferten Attempt-Typ, Retry-Boolean, Zielkontext,
Provider, Hashwert, Rollen- oder Authority-Snapshot.

## Zulässiger Attempt-2-Zustand

Die externe Inspektion ist für Attempt 2 nur möglich, wenn persistent gilt:

- Attempt 2 gehört zur Execution;
- Attempt-Nummer ist exakt 2;
- Attempt 2 ist `outcome_unknown`;
- Attempt 2 besitzt keine Finish-Zeit;
- Execution ist `outcome_unknown`;
- Attempt 1 derselben Execution ist `reconciled` und abgeschlossen;
- für Attempt 1 existiert ein bestätigter Absence-Recovery-Abschluss;
- für den Handoff existiert noch kein Receipt.

Ein vorbereiteter, unbekannter oder ungebundener Attempt erreicht den Provider
nicht.

## Attempt 1 bleibt unverändert

Die bisherige LQ-258-Semantik für Attempt 1 bleibt bestehen.

Die persistente Abfrage unterscheidet Attempt 1 und Attempt 2 geschlossen.
Attempt 2 kann nicht allein aufgrund seiner Nummer oder eines Callerhinweises
zugelassen werden.

## Historisches Ziel

Wie bei Attempt 1 wird das Ziel aus der unveränderlichen Handoff-Bindung und
der historischen Channel-Revision rekonstruiert:

- Channel-ID und Revision;
- Providerart;
- kanonischer Zielname;
- Paketname und Paketversion;
- erwarteter Wheel-SHA-256.

Damit bleibt die Feststellung externer Realität auch nach einer späteren
Authority-Revocation möglich.

## Ausschließlich read-only

LQ-263 verwendet nur `ReleasePublicationTargetInspector`.

Der Port besitzt keine Create-, Upload-, Replace-, Delete-, Yank- oder
Overwrite-Methode. Pro Reconciliation-Aufruf wird das historisch gebundene
Ziel höchstens einmal gelesen.

Der LQ-262-Creator ist an dieser Grenze nicht erreichbar.

## Geschlossene Ergebnisse

Die bestehenden drei Reconciliation-Arten gelten nun ebenso für Attempt 2:

- `PUBLISHED_CONFIRMED`;
- `ABSENCE_CONFIRMED`;
- `CONFLICT`.

Technische Unklarheit ist kein positives viertes Ergebnis.

## Bytegleicher Erfolg

`PUBLISHED_CONFIRMED` verlangt weiterhin:

- extern sichtbar;
- exakt erwarteter Paketname;
- exakt erwartete Paketversion;
- exakt erwarteter Wheel-SHA-256.

Die Observation bindet außerdem externe Artefaktidentität und unveränderliche
Providerrevision.

Das read-only Ergebnis ist noch kein Receipt und kein persistenter
Publication-Abschluss.

## Bestätigte Abwesenheit

Ein `None` des kontrollierten Inspectors bedeutet bestätigte Abwesenheit.

LQ-263 erzeugt daraus weder Attempt 3 noch einen weiteren Create. Die
Execution und Attempt 2 bleiben `outcome_unknown`, bis ein späterer
persistenter Recovery-Slice eine bewusste Entscheidung trifft.

## Konflikt

Ein abweichender Wheel-Hash, Paketname, Paketversion oder nicht bestätigte
Sichtbarkeit ergibt `CONFLICT`.

Das externe Ziel wird nicht verändert, gelöscht oder überschrieben. Es gibt
keinen automatischen Retry.

## Aktuelle Authority als Begleitfakt

LQ-263 prüft parallel read-only den aktuellen Stand von:

- Channel und exakter Revision;
- Publisher-Zuordnung;
- Registry-Policy;
- Signer und Signing-Key;
- fehlendem `pending` Reassessment.

Dieser Stand wird als `current_authority` im kurzlebigen Ergebnis mitgeführt.

## Revocation und externe Realität

Eine Revocation verhindert nicht die historische Zielinspektion.

Ein bytegleich sichtbares Artefakt bleibt `PUBLISHED_CONFIRMED`, während
`current_authority=False` den späteren persistenten Abschluss zu einer
fail-closed Security-Entscheidung zwingt.

Revocation wird weder als Abwesenheit noch als technischer Providerfehler
maskiert.

## Technische Unklarheit

Timeout, Verbindungsabbruch, untypisierte Providerantwort oder ein technisch
nicht sicher auswertbarer Read wird detailfrei als bestehende
`ReleasePublicationReconciliationUnavailable` gemeldet.

Execution und Attempt 2 bleiben dabei unverändert `outcome_unknown`.

Der Fehler enthält keine Provider-, Netzwerk-, SQL-, Registry-, Hash-, ID-,
Pfad- oder Credentialdetails.

## Keine Mutation

LQ-263 ändert keine Datenbankzeile und keinen Providerzustand.

Insbesondere entstehen nicht:

- Receipt oder Receipt-Reconciliation;
- Recovery-Entscheidung;
- Reassessment;
- Finish-Zeit;
- Attempt 3;
- Create- oder Upload-Aufruf.

## Keine Migration

Der Slice liest ausschließlich bestehende Publication-, Recovery- und
Authority-Fakten.

Es gibt keine neue Tabelle, Spalte, Constraint, Migration oder Bootstrap-
Mutation. Head bleibt `20260818_0023` mit 23 linearen Migrationen.

## Nachweis

Tests belegen für Attempt 2:

- bytegleicher sichtbarer Effekt ergibt `PUBLISHED_CONFIRMED`;
- bestätigte Abwesenheit ergibt `ABSENCE_CONFIRMED` ohne Retry;
- Hash-, Name-, Versions- und Sichtbarkeitsabweichung ergeben `CONFLICT`;
- Revocation verschweigt externe Realität nicht und setzt Authority false;
- Prepared- und unbekannte Attempts erreichen den Provider nicht;
- Providerfehler bleiben detailfrei und persistent unknown;
- Execution, Attempt und Receipt-Bestand bleiben unverändert;
- dieselbe read-only Semantik nach dem realen LQ-262-Ablauf auf PostgreSQL 16.

Die vollständige Pflichtsuite mit PostgreSQL 16 besteht:

```text
3224 passed, 445 warnings
```

Der nächste Slice LQ-264 persistiert den Attempt-2-Abschluss atomar. Published
muss als Receipt bewahrt werden; Absence und Conflict benötigen getrennte,
fail-closed Recovery-Regeln ohne automatischen Attempt 3.
