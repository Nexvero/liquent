# LQ-259 — Persistent Release Publication Reconciliation Finalization

## Ergebnis

LQ-259 implementiert den atomaren persistenten Abschluss eines durch LQ-258
bytegleich bestätigten externen Publication-Erfolgs.

Der Slice erzeugt Receipt und Receipt-Reconciliation, schließt Execution und
Attempt und bewahrt bei inzwischen entzogener Authority gleichzeitig ein
`pending` Reassessment.

Bestätigte Abwesenheit oder Konflikt werden nicht als Erfolg persistiert.

## Öffentliche Grenze

`finalize_reconciliation` akzeptiert ausschließlich:

- bestehende Execution-ID;
- bestehende Attempt-ID.

Der Aufrufer liefert kein Receipt, keine Providerrevision, externe ID,
Observation, Authority-Boolean, Rolle oder Allow-Entscheidung.

## Read-only Reconciliation zuerst

Vor jeder neuen Persistenzmutation ruft LQ-259 die vollständige LQ-258-
Reconciliation auf.

Nur `PUBLISHED_CONFIRMED` darf den persistenten Abschluss erreichen.

`ABSENCE_CONFIRMED`, `CONFLICT`, neutrale Ablehnung oder technische
Nichtverfügbarkeit erzeugen kein Receipt.

## Exakter Retry vor Providerzugriff

Vor LQ-258 sucht der Finalizer nach einer bereits abgeschlossenen
Receipt-Reconciliation für genau Execution und Attempt.

Ein exakter Retry liefert den bestehenden Abschluss zurück, ohne:

- den Provider erneut zu inspizieren;
- neue IDs zu erzeugen;
- Receipt oder Reassessment zu duplizieren;
- Status erneut zu schreiben.

## Erneute atomare Bindungsprüfung

Das LQ-258-Ergebnis ist kein dauerhaftes Commit-Ticket.

Unter Datenbanksperre prüft LQ-259 erneut:

- Execution und Attempt weiterhin `outcome_unknown`;
- Attempt-Nummer 1 und leere Finish-Zeit;
- unveränderte Handoff-Bindung;
- historische Channel-ID und Revision;
- Providerart und kanonischen Zielnamen;
- Paketname und Paketversion;
- beobachteten Wheel-Hash;
- noch fehlendes Receipt.

Eine stale, substituierte oder bereits abgeschlossene Observation kann keinen
zweiten Abschluss erzeugen.

## Aktuelle Authority beim Commit

Innerhalb derselben Transaktion wird aktuell geprüft:

- aktueller Channel und exakte Revision;
- aktive Publisher-Zuordnung;
- aktive Registry-Policy;
- aktiver Signer;
- aktiver Signing-Key;
- fehlendes `pending` Reassessment.

Der von LQ-258 gelieferte `current_authority`-Boolean wird nicht als
Commit-Autorität übernommen.

Damit wirkt auch eine Revocation zwischen Provider-Read und Datenbankcommit.

## Receipt-ID

Eine neue `ReleasePublicationProviderReceiptId` wird erst nach sämtlichen
Bindungs- und Zustandsprüfungen erzeugt.

Die ID stammt aus der kontrolliert injizierten sicheren Materialgrenze. Sie
wird weder aus Providerrevision, externer ID, Hashwerten noch Zeit abgeleitet.

ID-Erzeugung allein gewährt keine Publication-Authority.

## Persistentes Receipt

`release_publication_receipts` bindet atomar:

- neue stabile Receipt-ID;
- unveränderten Handoff;
- unveränderliche Providerrevision als bestätigten Providerbeleg;
- beobachteten Bundle-Hash;
- Bestätigungszeit.

Credentials, Tokens und rohe Providerantworten werden nicht gespeichert.

## Receipt-Reconciliation

`release_publication_receipt_reconciliations` bindet dasselbe Receipt
zusätzlich an:

- genau eine Execution;
- genau einen Attempt;
- kanonische externe Artefaktidentität;
- unveränderliche Providerrevision;
- Bestätigungszeit;
- finalen Reconciliation-Status.

Execution und Attempt können weiterhin höchstens ein Receipt abschließen.

## Abschluss bei aktueller Authority

Ist sämtliche Authority beim Commit weiterhin aktuell, lautet der finale
Status:

```text
published
```

Atomar wechseln:

- Execution zu `published`;
- Attempt zu `reconciled`;
- Attempt erhält seine Finish-Zeit;
- Receipt und Reconciliation entstehen.

Es entsteht kein Reassessment.

## Abschluss nach Revocation

Ist externe bytegleiche Veröffentlichung bestätigt, aber aktuelle Authority
entzogen, darf die externe Realität nicht verschwiegen werden.

Der finale Status lautet dann:

```text
published_reassessment_required
```

Receipt und Reconciliation werden trotzdem gespeichert.

Gleichzeitig entsteht atomar ein `pending` Reassessment mit Intent `reassess`
und eine Execution-Reassessment-Zuordnung.

## Bereits vorhandenes Pending Reassessment

Existiert für den Handoff bereits ein `pending` Reassessment, wird dessen
stabile ID wiederverwendet und mit der Execution verknüpft.

Es wird kein zweites semantisch identisches Pending-Reassessment erzeugt.

Die bestehende Sperre wird nicht überschrieben oder abgeschlossen.

## Revocation-Race

Tests entziehen Publisher-Authority gezielt nach dem positiven LQ-258-Read,
aber vor dem Finalizer-Commit.

Die erneute transaktionale Prüfung erkennt diesen Zustand und schreibt
`published_reassessment_required` samt Reassessment.

Es gibt keinen positiven Authority-Cache oder Grace-Boolean.

## Abwesenheit bleibt Unknown

`ABSENCE_CONFIRMED` erzeugt weder Receipt noch Attempt-Finish.

Execution und Attempt bleiben `outcome_unknown`, bis ein eigener Recovery-
Slice sichere Regeln für Abschluss und gegebenenfalls Attempt 2 definiert.

LQ-259 startet keinen Retry und lädt nicht erneut hoch.

## Konflikt bleibt fail-closed

`CONFLICT` erzeugt ebenfalls kein Receipt und keinen Published-Status.

Das abweichende externe Ziel wird nicht überschrieben, gelöscht, ersetzt oder
als Erfolg anerkannt.

Die spätere Security-/Recovery-Behandlung bleibt separat.

## Geschlossenes Ergebnis

`FinalizedReleasePublication` bindet:

- Receipt-ID;
- Execution, Attempt und Handoff;
- finalen Status;
- bei Reassessment-Pflicht die stabile Reassessment-ID.

`ReleasePublicationFinalStatus` besitzt exakt:

- `PUBLISHED`;
- `PUBLISHED_REASSESSMENT_REQUIRED`.

Nur der zweite Status darf eine Reassessment-ID tragen.

## Konkurrenz

Auf PostgreSQL sperrt die Finalizer-Transaktion Registry-, Channel-, Handoff-,
Receipt-, Reassessment-, Execution- und Attempt-Inventare.

Ein konkurrierender Gewinner wird innerhalb der Sperre als exakter bestehender
Abschluss gelesen. Der zweite Prozess erzeugt keine weiteren Fakten.

## Fehlergrenze

`ReleasePublicationReconciliationFinalizeUnavailable` vereinheitlicht
detailfrei:

- Datenbank- und Strukturfehler;
- ungültige ID-Generatoren;
- unbenutzbare Clock;
- inkonsistente bestehende Abschlussfakten;
- technisch nicht sicher abschließbare Transaktionen.

Der Fehler enthält keine IDs, Hashwerte, SQL-, Provider-, Registry- oder
Credentialdetails.

## Persistenz und Migrationen

LQ-259 verwendet ausschließlich die LQ-249- und LQ-253-Inventare.

Es gibt keine Migration, Tabelle oder Schemaänderung. Head bleibt
`20260817_0022` mit 22 Migrationen.

## Nachweis

Tests belegen:

- atomaren Receipt-, Reconciliation-, Execution- und Attempt-Abschluss;
- Finish-Zeit nur für `reconciled`;
- exakten Retry ohne Provider-Read oder neue IDs;
- `published` bei aktueller Authority;
- `published_reassessment_required` bei Key-Revocation;
- atomare Reassessment-Erzeugung und Execution-Zuordnung;
- Erkennung einer Revocation zwischen LQ-258 und Commit;
- keine Mutation bei Abwesenheit oder Konflikt;
- denselben atomaren Abschluss auf echtem PostgreSQL 16.

Die vollständige Pflichtsuite mit PostgreSQL 16 besteht:

```text
3184 passed, 258 warnings
```

Der temporäre PostgreSQL-Cluster wurde kontrolliert gestoppt und entfernt.

## Bewusst nicht enthalten

LQ-259 implementiert keine Absence-Finalisierung, Attempt-2-Erzeugung,
Retry-Freigabe, Konflikt-Reassessment, Withdrawal, konkreten Provideradapter,
Create, Upload, CLI, Git- oder Deploymentaktion.

## Nächster Slice

LQ-260 sollte die kontrollierte Recovery für `ABSENCE_CONFIRMED` und
`CONFLICT` entscheiden. Sie muss festlegen, wie ein garantiert effektloser
Attempt historisch abgeschlossen wird, wann ein neuer Attempt zulässig ist und
wie Konflikte ein Reassessment auslösen, ohne jemals blind erneut hochzuladen.
