# LQ-264 — Persistent Release Publication Attempt-Two Finalization

## Ergebnis

LQ-264 persistiert den kontrollierten Abschluss eines durch LQ-263
reconcilierten Attempt 2.

Bytegleicher Erfolg wird als Receipt bewahrt. Bestätigte Abwesenheit und
Konflikt werden terminal abgeschlossen. Keiner dieser Pfade erzeugt Attempt 3.

## Getrennte Abschlussgrenzen

Die bestehenden Finalizer bleiben fachlich getrennt:

- `finalize_reconciliation` akzeptiert nur `PUBLISHED_CONFIRMED`;
- `finalize_recovery` akzeptiert nur `ABSENCE_CONFIRMED` oder `CONFLICT`.

Beide akzeptieren ausschließlich Execution- und Attempt-ID. Der Caller liefert
keine Observation, Abschlussart, Rolle, Authority-, Retry- oder Allow-
Entscheidung.

## Persistente Attempt-2-Bindung

Ein neuer Abschluss verlangt weiterhin:

- Execution `outcome_unknown`;
- Attempt 2 `outcome_unknown`;
- Attempt-Nummer exakt 2;
- leere Finish-Zeit;
- Attempt gehört zur Execution und zum unveränderten Handoff;
- Attempt 1 derselben Execution ist `reconciled` und abgeschlossen;
- Attempt 1 besitzt einen bestätigten Absence-Recovery-Abschluss;
- noch kein Receipt für den Handoff.

Ein unbekannter oder caller-behaupteter Attempt 2 reicht nicht aus.

## LQ-263 bleibt maßgeblich

Vor jeder neuen Mutation führt der jeweilige Finalizer die read-only LQ-263-
Reconciliation aus.

Das Ergebnis wird nicht als dauerhaftes Commit-Ticket behandelt. Unter
Datenbanksperre werden Unknown-Zustand, Attempt-Bindung, historischer
Zielkontext und Observation erneut geprüft.

## Published-Abschluss

Nur eine weiterhin passende bytegleiche Observation darf den Receipt-Pfad
erreichen.

Atomar entstehen beziehungsweise ändern sich:

- ein Provider-Receipt für den Handoff;
- eine Receipt-Reconciliation für Execution und Attempt 2;
- Attempt 2 zu `reconciled` mit Finish-Zeit;
- Execution zu `published`.

Es gibt keinen weiteren Create und keine Erfolgsbehauptung allein aufgrund der
früheren Provider-Acknowledgement.

## Published nach Revocation

Externe Realität wird auch nach Authority-Revocation bewahrt.

Ist Channel-, Publisher-, Registry-, Signer- oder Key-Authority beim Commit
nicht mehr aktuell, entstehen atomar:

- derselbe bestätigte Receipt;
- Status `published_reassessment_required`;
- ein `pending` Reassessment oder die Bindung an ein bereits vorhandenes;
- die Execution-/Reassessment-Zuordnung.

Revocation löscht oder verschweigt keinen bestätigten externen Effekt.

## Terminale bestätigte Abwesenheit

Bestätigte Abwesenheit erzeugt einen zweiten persistenten Recovery-Fakt für
Attempt 2.

Atomar wechseln:

- Attempt 2 zu `reconciled` mit Finish-Zeit;
- Execution zu `not_published`;
- Recovery-Art zu `absence_confirmed`.

`retry_eligible` ist für Attempt 2 immer `False`, unabhängig vom aktuellen
Authority-Status.

Es entsteht weder Receipt noch Reassessment oder Attempt 3.

## Terminaler Konflikt

Ein bestätigter Konflikt speichert:

- externe kanonische Artefaktidentität;
- unveränderliche Providerrevision;
- ein `pending` Reassessment;
- die Execution-/Reassessment-Bindung.

Attempt 2 wird `reconciled`, und die Execution wechselt atomar zu
`publication_conflict`.

Ein Konflikt ist niemals retry-fähig und erzeugt kein Receipt oder Attempt 3.

## Zwei Recovery-Fakten, eine Historie

Das bestehende Recovery-Inventar besitzt bereits eine eindeutige Bindung pro
Execution und Attempt.

Damit bleiben getrennt erhalten:

- der Absence-Abschluss von Attempt 1, der einmalig Attempt 2 ermöglichte;
- der terminale Absence- oder Conflict-Abschluss von Attempt 2.

Die Fakten werden nicht überschrieben oder zusammengeführt.

## Aktuelle Authority beim Commit

Die von LQ-263 gelieferte `current_authority` wird nicht blind übernommen.

Innerhalb derselben Abschlusstransaktion werden erneut geprüft:

- aktueller Channel und exakte Revision;
- aktive Publisher-Zuordnung;
- aktive Registry-Policy;
- aktiver Signer und Signing-Key;
- vorhandenes `pending` Reassessment.

Für terminale Abwesenheit entsteht aus aktueller Authority ausdrücklich keine
weitere Retry-Berechtigung.

## Atomizität und Konkurrenz

Auf PostgreSQL sperren die Finalizer die beteiligten Publication-, Recovery-,
Receipt-, Reassessment-, Channel- und Registry-Inventare kurzzeitig.

Receipt, Recovery-Fakt, Reassessment, Attempt-Finish und Execution-Status
werden in genau einer Transaktion geschrieben.

Konkurrierende Finalizer können keinen doppelten Receipt, Recovery-Fakt oder
semantisch doppeltes `pending` Reassessment erzeugen.

## Exakter Retry

Vor jeder Providerinspektion sucht der Finalizer den bestehenden Abschluss für
Execution und Attempt 2.

Ein exakter Retry liefert denselben Receipt- oder Recovery-Fakt zurück, ohne
Provider-Read, neue IDs oder weitere Mutation.

Terminale Execution-Zustände werden niemals als neue Upload-Freigabe
interpretiert.

## Additive Migration

Migration `20260819_0024` baut linear auf `20260818_0023` auf und ist der neue
einzige Head.

Sie erweitert ausschließlich die zulässigen Execution-Status um:

- `not_published`;
- `publication_conflict`.

Es entstehen keine neue Tabelle, kein Seed, kein Attempt und keine
Bootstrap-Mutation. Das bestehende Recovery-Inventar bleibt unverändert.

## Bundle-Gate

Das LQ-236-Wheelgate erwartet nun 24 lineare Migrationen bis Head
`20260819_0024`.

Bundleformat, Console Entry Points und Operatormodule bleiben unverändert.

## Neutrale Ablehnung

Ein nicht passender Zustand oder eine nicht zum Finalizer passende
Reconciliation-Art endet neutral ohne Mutation.

Bestätigte Abwesenheit und Konflikt können nicht versehentlich als Receipt
persistiert werden. Published kann nicht als Recovery gespeichert werden.

## Detailfreie technische Nichtverfügbarkeit

Die bestehenden Finalizer-Fehlergrenzen vereinheitlichen Datenbank-,
Struktur-, Generator-, Clock-, Provider- und Transaktionsfehler detailfrei.

Keine ID, Observation, Hash-, SQL-, Registry-, Provider- oder
Credentialinformation verlässt die Grenze.

## Nachweis

Tests belegen:

- Attempt-2-Published erzeugt Receipt und schließt Execution atomar;
- Published nach Revocation erzeugt `pending` Reassessment;
- Attempt-2-Abwesenheit endet `not_published` ohne Attempt 3;
- Attempt-2-Konflikt endet `publication_conflict` mit Reassessment;
- beide terminalen Recovery-Arten sind nicht retry-fähig;
- exakter Retry vermeidet Provider-Read und neue IDs;
- LQ-258/LQ-260-Verhalten für Attempt 1 bleibt unverändert;
- die additive Migration und das 24-Migrationen-Bundle-Gate;
- denselben Published-Abschluss auf echtem PostgreSQL 16.

Die vollständige Pflichtsuite mit PostgreSQL 16 besteht:

```text
3229 passed, 494 warnings
```

Der nächste Slice LQ-265 sollte den vollständigen zweistufigen Publication-
Lebenszyklus und seine terminalen Zustände end-to-end auditieren, ohne neue
Provider-, CLI-, Git- oder Deploymentwrites einzuführen.
