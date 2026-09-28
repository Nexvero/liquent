# LQ-260 — Persistent Release Publication Absence and Conflict Recovery

## Ergebnis

LQ-260 implementiert den atomaren persistenten Recovery-Abschluss für die
beiden nicht erfolgreichen LQ-258-Ergebnisse:

- bestätigte Abwesenheit;
- externer Konflikt.

Beide schließen den unklaren Attempt historisch ab. Keiner erzeugt sofort
Attempt 2 oder führt einen Upload aus.

## Warum ein eigener Recovery-Fakt nötig ist

Receipt und Receipt-Reconciliation modellieren ausschließlich bestätigte
externe Veröffentlichung.

Bestätigte Abwesenheit darf nicht als Receipt dargestellt werden. Ein Konflikt
darf weder als erwartete Veröffentlichung noch als gewöhnliche Abwesenheit
erscheinen.

LQ-260 ergänzt deshalb ein getrenntes historienerhaltendes
Recovery-Entscheidungsinventar.

## Stabile Recovery-ID

`ReleasePublicationRecoveryId` ist ein eigener repr-freier, immutable und
geslotteter Identitätstyp.

Er ist nicht mit Attempt-, Execution-, Receipt- oder Reassessment-ID
austauschbar.

`SecureIdentityAuthorityMaterialGenerator` erzeugt ihn aus einem unabhängigen
Zug von mindestens 32 Byte Betriebssystementropie.

ID-Erzeugung gewährt keine Retry- oder Publication-Authority.

## Öffentliche Grenze

`finalize_recovery` akzeptiert ausschließlich:

- bestehende Execution-ID;
- bestehende Attempt-ID.

Der Aufrufer liefert keine Recovery-Art, Observation, externe ID,
Providerrevision, Authority-Boolean, Rolle, Allow- oder Retry-Entscheidung.

## LQ-258 bleibt maßgeblich

Vor jeder neuen Recovery-Mutation führt LQ-260 die read-only LQ-258-
Reconciliation aus.

Nur `ABSENCE_CONFIRMED` und `CONFLICT` gelangen in diesen Finalizer.

`PUBLISHED_CONFIRMED` bleibt ausschließlich dem LQ-259-Receipt-Finalizer
vorbehalten.

Technisch weiterhin unbekannte Providerzustände bleiben unverändert
`outcome_unknown`.

## Additive Migration

Migration `20260818_0023` baut linear auf `20260817_0022` auf und ist der neue
einzige Head.

Sie erzeugt genau eine leere Tabelle:

`release_publication_recovery_decisions`.

Es gibt keinen Recovery-, Retry- oder Reassessment-Seed.

## Persistente Recovery-Bindung

Jede Recovery-Entscheidung bindet:

- stabile Recovery-ID;
- genau eine bekannte Execution;
- genau einen bekannten Attempt;
- geschlossene Recovery-Art;
- beim Commit beobachteten aktuellen Authority-Status;
- optionale externe Konfliktevidence;
- optionale Reassessment-ID;
- Entscheidungszeit.

Execution und Attempt können zusammen höchstens einen Recovery-Abschluss
besitzen.

## Geschlossene Recovery-Arten

Zulässig sind ausschließlich:

- `absence_confirmed`;
- `conflict`.

Die Tabellen-Check-Constraint erzwingt unterschiedliche Evidence-Regeln für
beide Arten.

## Evidence-Regeln für Abwesenheit

`absence_confirmed` darf keine externe Artefaktidentität, Providerrevision oder
Reassessment-ID speichern.

Abwesenheit bedeutet, dass der read-only Inspector das kontrollierte Ziel als
nicht vorhanden bestätigt hat.

Sie ist kein Provider-Receipt und kein Publication-Erfolg.

## Evidence-Regeln für Konflikt

`conflict` verlangt:

- kanonische externe Artefaktidentität;
- unveränderliche Providerrevision;
- bekannte `pending` Reassessment-ID.

Damit kann ein Konflikt nicht ohne konkrete externe Observation oder ohne
Security-Folgezustand persistiert werden.

## Erneute atomare Bindungsprüfung

Das LQ-258-Ergebnis ist kein dauerhaftes Commit-Ticket.

Unter Datenbanksperre prüft LQ-260 erneut:

- Execution und Attempt weiterhin `outcome_unknown`;
- Attempt-Nummer 1 und leere Finish-Zeit;
- unveränderten Handoff;
- historische Channel-ID und Revision;
- Providerart und kanonischen Zielnamen;
- Paketname und Paketversion;
- fehlendes Receipt;
- Observation passend zur Recovery-Art.

Eine nun bytegleiche sichtbare Observation kann nicht als Konflikt gespeichert
werden.

## Aktuelle Authority beim Commit

LQ-260 prüft innerhalb derselben Transaktion erneut:

- aktuellen Channel und Revision;
- aktive Publisher-Zuordnung;
- aktive Registry-Policy;
- aktiven Signer;
- aktiven Signing-Key;
- fehlendes `pending` Reassessment.

Der frühere LQ-258-Boolean wird nicht als Commit-Autorität übernommen.

## Abschluss bestätigter Abwesenheit

Bei `ABSENCE_CONFIRMED` wechseln atomar:

- Attempt 1 zu `reconciled`;
- Attempt 1 erhält seine Finish-Zeit;
- Execution von `outcome_unknown` zurück zu `prepared`;
- Recovery-Entscheidung wird gespeichert.

Es entstehen kein Receipt, Reassessment und kein Attempt 2.

## Retry-Eignung ist noch kein Retry

`retry_eligible=True` wird nur zurückgegeben, wenn beim Recovery-Commit die
vollständige aktuelle Authority weiterhin besteht.

Dieser Wert beschreibt ausschließlich, dass ein späterer Slice einen neuen
Attempt prüfen darf.

Er erzeugt keinen Attempt, startet keine Zielinspektion und autorisiert keinen
Upload. Vor Attempt 2 sind ein neuer Authority-, Integritäts- und
Read-before-write-Preflight verpflichtend.

## Abwesenheit nach Revocation

Ist das Ziel bestätigt abwesend, aber Authority inzwischen entzogen, wird
Attempt 1 trotzdem historisch abgeschlossen.

`retry_eligible` lautet dann `False`.

Es entsteht kein Reassessment, weil kein externer Konflikt und kein bestätigter
Publication-Effekt vorliegt. Die Revocation selbst sperrt jeden späteren Retry.

## Abschluss eines Konflikts

Bei `CONFLICT` wechseln atomar:

- Attempt 1 zu `reconciled`;
- Attempt 1 erhält seine Finish-Zeit;
- Recovery-Entscheidung speichert externe Evidence;
- ein `pending` Reassessment mit Intent `reassess` entsteht;
- Execution und Reassessment werden verknüpft.

Execution bleibt fail-closed `outcome_unknown`. Es entsteht kein Attempt 2.

## Bestehendes Pending Reassessment

Existiert bereits ein `pending` Reassessment für den Handoff, wird dessen
stabile ID wiederverwendet.

Die Execution-Zuordnung wird idempotent ergänzt. Es wird kein semantisch
doppeltes Pending-Reassessment erzeugt.

## Exakter und konkurrierender Retry

Vor LQ-258 sucht der Finalizer nach einer bestehenden Recovery-Entscheidung für
Execution und Attempt.

Ein exakter Retry liefert denselben Recovery-Fakt ohne Provider-Read oder neue
IDs zurück.

Auf PostgreSQL serialisiert die kurze Control-Plane-Sperre konkurrierende
Finalizer. Der Verlierer liest den bereits committeten Abschluss.

## Kein blindes Hochladen

LQ-260 besitzt keinen Creator- oder Upload-Port.

Auch bestätigte Abwesenheit löst nicht unmittelbar LQ-257 aus. Ein späterer
Attempt 2 benötigt eine eigene persistente Identität und einen neuen
Read-before-write-Zyklus.

Ein Konflikt kann niemals Retry-Eignung erhalten.

## Finales Recovery-Ergebnis

`FinalizedReleasePublicationRecovery` bindet:

- Recovery-ID;
- Execution, Attempt und Handoff;
- Absence- oder Conflict-Art;
- Retry-Eignung;
- bei Konflikt die Reassessment-ID.

Die Domaininvarianten verbieten Retry-Eignung für Konflikte und eine
Reassessment-ID für Abwesenheit.

## Fehlergrenze

`ReleasePublicationRecoveryFinalizeUnavailable` vereinheitlicht detailfrei:

- Datenbank- und Strukturfehler;
- ungültige Generatoren oder Clock;
- inkonsistente bestehende Recovery-Fakten;
- nicht passende Observation-/Recovery-Bindungen;
- technisch nicht sicher abschließbare Transaktionen.

Der Fehler enthält keine IDs, Hashwerte, SQL-, Provider-, Registry- oder
Credentialdetails.

## Bundle-Gate

Das LQ-236-Wheelgate erwartet nun 23 lineare Migrationen bis Head
`20260818_0023`.

Bundleformat, Console Entry Points und Operatormodule bleiben unverändert.

## Nachweis

Tests belegen:

- leere additive Recovery-Foundation;
- Foreign-Key- und Evidence-Invarianten;
- unabhängige sichere Recovery-ID-Erzeugung;
- Abwesenheitsabschluss ohne Receipt, Reassessment oder Attempt 2;
- Retry-Eignung nur bei aktueller Authority;
- keine Retry-Eignung nach Revocation;
- Konfliktabschluss mit externer Evidence und `pending` Reassessment;
- exakten Retry ohne Provider-Read oder neue IDs;
- Published-Erfolg bleibt dem Receipt-Finalizer vorbehalten;
- denselben Foundation- und Recovery-Stand auf echtem PostgreSQL 16.

Die vollständige Pflichtsuite mit PostgreSQL 16 besteht:

```text
3200 passed, 294 warnings
```

Der temporäre PostgreSQL-Cluster wurde kontrolliert gestoppt und entfernt.

## Bewusst nicht enthalten

LQ-260 implementiert keine Attempt-2-Erzeugung, Retry-Ausführung, neue
Zielinspektion nach Recovery, Create, Upload, Receipt für Abwesenheit oder
Konflikt, Reassessment-Abschluss, Withdrawal, CLI, Git- oder Deploymentaktion.

## Nächster Slice

LQ-261 sollte den persistenten Attempt-2-Preflight für einen exakt
`retry_eligible` Abwesenheitsabschluss implementieren. Er muss Authority,
Artefaktintegrität und Zielabwesenheit vollständig neu prüfen, eine neue
Attempt-ID mit Nummer 2 atomar erzeugen und weiterhin vor jedem Provider-Write
enden.
