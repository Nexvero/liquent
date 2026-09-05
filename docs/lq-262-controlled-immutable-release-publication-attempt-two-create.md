# LQ-262 — Controlled Immutable Release Publication Attempt-Two Create

## Ergebnis

LQ-262 implementiert genau einen kontrollierten immutable Provider-Create für
den durch LQ-261 persistent vorbereiteten Attempt 2.

Jeder mögliche externe Effekt wird erneut konservativ als `outcome_unknown`
persistiert. Der Slice behauptet keinen Publication-Erfolg und erzeugt kein
Receipt.

## Öffentliche Grenze

`create_retry_publication` akzeptiert ausschließlich:

- die bestehende Execution-ID;
- die persistente Attempt-2-ID.

Provider, Ziel, Paket, Artefakte, Hashwerte, Authority und Idempotenz werden
nicht vom Aufrufer geliefert.

## Ausschließlich Attempt 2

Der Create-Pfad verlangt:

- Attempt-Nummer 2;
- Attempt-Status `prepared`;
- leere Finish-Zeit;
- Execution-Status `prepared`;
- abgeschlossenen reconciled Attempt 1;
- bestätigten LQ-260-Abwesenheitsabschluss für Attempt 1.

Attempt 1 bleibt beim LQ-257-Pfad. Ein dritter Attempt oder eine allgemeine
Retry-Schleife ist nicht enthalten.

## Frische Artefaktintegrität

Vor jeder neuen externen Inspektion führt LQ-262 die vollständige LQ-255-
Prüfung für Attempt 2 aus.

Die Prüfung bindet den unveränderten Handoff und alle Paket-, Bundle-, Wheel-,
Checksums-, Signatur- und Promotion-Evidence-Hashes an die kontrollierten
lokalen Artefakte und die aktuelle Registry-Authority.

Die Artifact-Integrity-Grenze akzeptiert Attempt 2 nur bei passendem
historischem Absence-Recovery für den abgeschlossenen Attempt 1.

## Erneutes Read-before-write

Ein vorbereiteter Attempt 2 ist kein dauerhaftes Write-Ticket.

LQ-262 löst das Ziel erneut aus dem persistenten Channel- und Handoff-Kontext
auf und liest es über den bestehenden read-only Inspector.

Nur erneut bestätigte Abwesenheit darf den atomaren Write-Start erreichen.
Jede sichtbare Observation sperrt den Create neutral und wird nicht
überschrieben oder neu klassifiziert.

## Aktuelle Authority

Vor der Zielinspektion und erneut innerhalb der Write-Start-Transaktion müssen
aktuell bestehen:

- derselbe aktuelle aktive Channel und dieselbe Revision;
- aktive Publisher-Zuordnung des Handoffs;
- aktuelle aktive Registry-Policy;
- aktiver Signer;
- aktiver Signing-Key;
- kein Receipt;
- kein `pending` Reassessment.

Der beim Recovery persistierte positive Authority-Fakt ist nur eine
historische Voraussetzung und ersetzt diese aktuellen Prüfungen nicht.

## Exakte Payload-Bindung

Unmittelbar vor dem Statuswechsel vergleicht LQ-262 erneut:

- Execution, Attempt 2 und Handoff;
- Providerart, Zielname, Paketname und Paketversion;
- Bundle-, Wheel-, Checksums-, Signatur- und Promotion-Evidence-Hash.

Eine stale, substituierte oder inzwischen widerrufene Vorprüfung kann keinen
Write starten.

## Atomarer Write-Start

Bei vollständig aktuellem Zustand wechselt Attempt 2 in einer kurzen
Control-Plane-Transaktion:

```text
prepared -> write_started
```

Der Commit ist abgeschlossen, bevor der Creator aufgerufen wird. Die
Datenbanktransaktion bleibt niemals während eines externen Provideraufrufs
offen.

## PostgreSQL-Konkurrenz

Auf PostgreSQL sperrt der Write-Start die beteiligten Registry-, Channel-,
Publisher-, Handoff-, Receipt-, Reassessment-, Execution-, Attempt- und
Recovery-Inventare.

Nur ein Prozess kann Attempt 2 erfolgreich auf `write_started` setzen. Ein
konkurrierender Aufruf erkennt danach den möglichen Effekt und führt keinen
zweiten Create aus.

## Eigene Idempotenzidentität

Der Retry-Creator erhält die stabile Attempt-2-ID als Idempotency-Key.

Damit besitzt der zweite kontrollierte Create eine andere Identität als der
erste Versuch und kann nicht mit dessen Provider-Idempotenz kollidieren.
Wiederholungen desselben Attempt 2 verwenden dagegen exakt dieselbe Identität.

Der Creator erhält keine Datenbankengine, Rollen, Authority-Boolean, private
Signing-Keys oder Deploymentdaten.

## Immutable Create-only

Der Provideradapter darf ausschließlich die bestätigte fehlende immutable
Paketversion erzeugen.

Overwrite, Replace, Upsert, mutable Tags, Alias- oder `latest`-Mutation gehören
nicht zum Port. LQ-262 fügt weiterhin keinen konkreten Netzwerkprovider oder
Credential-Lookup hinzu.

## Positiver Provider-Return

Auch eine gültige `ReleasePublicationCreateAcknowledgement` ist kein Receipt
und kein Sichtbarkeitsnachweis.

Nach dem Provideraufruf wechseln atomar:

```text
execution: outcome_unknown
attempt 2: outcome_unknown
```

Das Ergebnis verlangt einen späteren read-only Read-back und persistenten
Reconciliation-Abschluss.

## Providerfehler

Sobald der Creator aufgerufen wurde, kann ein externer Effekt nicht sicher
ausgeschlossen werden.

Timeout, Verbindungsabbruch, ungültiger Return oder anderer technischer Fehler
führen deshalb ebenfalls zuerst zu `outcome_unknown` und anschließend zu einer
detailfreien technischen Nichtverfügbarkeit.

Es gibt keinen unmittelbaren dritten Versuch und keinen blinden zweiten
Provideraufruf.

## Crash-Wiederaufnahme

Ein persistiertes `write_started` bedeutet bereits „möglicher externer
Effekt“.

Ein späterer exakter Retry führt weder Integritätsprüfung noch Provider-Read
oder Create aus. Er hebt den Zustand konservativ auf `outcome_unknown` und
liefert pending Reconciliation zurück.

Ein bereits `outcome_unknown` befindlicher Attempt 2 wird ebenfalls ohne
externen Aufruf wiedergegeben.

## Neutrale Ablehnung

`None` bedeutet ohne Detailoffenlegung, dass aktuell kein sicherer Create
gestartet werden darf. Dazu zählen insbesondere:

- fehlender oder falscher Attempt 2;
- fehlendes bestätigtes Absence-Recovery;
- veränderte oder fehlende Artefakte;
- aktuelle Authority-Revocation;
- Receipt oder `pending` Reassessment;
- ein inzwischen sichtbares Providerziel.

Vor dem Write-Start erzeugt diese Ablehnung keine Mutation.

## Detailfreie technische Nichtverfügbarkeit

`ReleasePublicationRetryCreateUnavailable` vereinheitlicht technische Fehler
ohne Provider-, SQL-, Registry-, Hash-, Pfad-, ID- oder Credentialdetails.

Nach möglichem Provider-Effekt wird der sichere Unknown-Zustand persistiert,
bevor der Fehler die Grenze verlässt.

## Keine Migration

LQ-262 verwendet die bestehenden Execution-, Attempt- und Recovery-Fakten.

Es gibt keine neue Tabelle, Spalte, Constraint, Migration oder Bootstrap-
Mutation. Head bleibt `20260818_0023` mit 23 linearen Migrationen.

## Nachweis

Tests belegen:

- frische Attempt-2-Artefaktprüfung;
- erneutes Read-before-write;
- atomaren Commit von `write_started` vor dem Creatoraufruf;
- Attempt-2-ID als Provider-Idempotency-Key;
- positiven Return mit anschließendem Unknown-Zustand;
- Providerfehler als detailfreie Nichtverfügbarkeit nach sicherem Unknown;
- Crash-Wiederaufnahme ohne zweiten Create;
- sichtbares Ziel und Revocation sperren vor dem Write;
- kein Receipt und kein Publication-Erfolg;
- denselben Ablauf auf echtem PostgreSQL 16.

Die vollständige Pflichtsuite mit PostgreSQL 16 besteht:

```text
3214 passed, 375 warnings
```

Der nächste Slice erweitert die read-only Unknown-Outcome-Reconciliation auf
Attempt 2. Er darf keinen Create ausführen und muss Erfolg, bestätigte
Abwesenheit, Konflikt und technische Unklarheit erneut geschlossen trennen.
