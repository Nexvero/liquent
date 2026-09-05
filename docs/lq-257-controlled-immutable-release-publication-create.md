# LQ-257 — Controlled Immutable Release Publication Create

## Ergebnis

LQ-257 implementiert den atomaren Write-Start und genau einen kontrollierten
immutable Create für einen vorbereiteten Publication-Attempt.

Der Slice persistiert jeden möglichen externen Effekt konservativ als
`outcome_unknown`. Er behauptet weder aufgrund einer positiven Providerantwort
noch aufgrund eines Timeouts einen Publication-Erfolg.

## Öffentliche Grenze

`create_publication` akzeptiert ausschließlich:

- bestehende Execution-ID;
- bestehende Attempt-ID.

Der Aufrufer liefert keine Providerart, URL, Zielbezeichnung, Credentials,
Artefaktbytes, Hashwerte, Rolle, Allow-Entscheidung oder Idempotency-ID.

## Read-before-write bleibt verpflichtend

Vor jedem möglichen Create ruft LQ-257 die vollständige LQ-256-
Zielinspektion auf.

Nur die geschlossene Entscheidung `CREATE_ALLOWED` darf den Write-Start
erreichen.

`RECONCILIATION_REQUIRED`, `CONFLICT`, neutrale Ablehnung oder technische
Nichtverfügbarkeit führen zu keinem Provider-Write.

## Erneute aktuelle Prüfung

Eine LQ-256-Entscheidung ist kein dauerhaftes Write-Ticket.

Unmittelbar vor dem Write-Start löst eine neue Datenbanktransaktion erneut
aktuell auf:

- vorbereitete Execution und Attempt 1;
- unveränderten Handoff;
- aktuellen aktiven Channel und exakte Revision;
- aktive Publisher-Zuordnung;
- aktuelle aktive Registry-Policy;
- aktuellen aktiven Signer;
- aktuellen aktiven Signing-Key;
- fehlendes Receipt;
- fehlendes `pending` Reassessment.

## Exakte Payload-Bindung

Der Write-Start vergleicht die LQ-256/LQ-255-Bindung erneut mit der Persistenz:

- Handoff-ID;
- Providerart und kanonischer Zielname;
- Paketname und Paketversion;
- Bundle-Hash;
- Wheel-Hash;
- SHA256SUMS-Hash;
- Signaturhash;
- Promotion-Evidence-Hash.

Eine stale oder substituierte Entscheidung kann dadurch keinen Write starten.

## Atomarer Write-Start

Bei vollständig aktueller Authority wechselt Attempt 1 innerhalb einer kurzen
Control-Plane-Transaktion atomar:

```text
prepared -> write_started
```

Der Commit ist abgeschlossen, bevor der Provideradapter aufgerufen wird.

Die Datenbanktransaktion bleibt niemals über einen externen Provideraufruf
offen.

## PostgreSQL-Konkurrenz

Auf PostgreSQL sperrt die Write-Start-Transaktion die beteiligten Registry-,
Channel-, Publisher-, Handoff-, Receipt-, Reassessment-, Execution- und
Attempt-Inventare.

Nur ein Prozess kann den vorbereiteten Attempt erfolgreich auf
`write_started` setzen.

Ein konkurrierender Prozess erkennt danach den möglichen externen Effekt und
führt keinen zweiten Create aus.

## Immutable Creator

`ReleasePublicationImmutableCreator` besitzt genau eine Write-Methode:

`create_immutable(target, artifacts, idempotency_key)`.

Der Adapter erhält:

- den kontrollierten LQ-256-Zielkontext;
- das vollständig geprüfte LQ-255-Payload;
- ausschließlich die stabile Execution-ID als Idempotency-Key.

Er erhält keine Datenbankengine, Authority-Snapshots, Rollen, private
Signing-Keys oder Deploymentdaten.

## Create-only Vertrag

Der Creator darf ausschließlich die bestätigte fehlende immutable
Paketversion erzeugen.

Überschreiben, Ersetzen, Upsert, mutable Tags, Aliase oder `latest` sind nicht
Teil des Ports.

LQ-257 implementiert keinen konkreten Netzwerkprovider. Die create-only
Semantik ist eine Pflicht für den später kontrolliert injizierten Adapter.

## Provider-Acknowledgement

Eine syntaktisch gültige Providerantwort wird als
`ReleasePublicationCreateAcknowledgement` mit repr-freier Request-ID
repräsentiert.

Die Acknowledgement ist kein Receipt und kein Nachweis externer Sichtbarkeit.
Sie wird in diesem Slice nicht persistiert.

## Positiver Provider-Return

Auch nach positiver Acknowledgement wechselt der persistente Zustand zwingend
zu:

```text
execution: outcome_unknown
attempt:   outcome_unknown
```

Ein späterer Read-back muss erst bestätigen, ob und mit welchen Bytes das
Artefakt extern sichtbar ist.

Das Rückgabeobjekt `ReleasePublicationWritePendingReconciliation` benennt
genau diesen offenen Zustand.

## Timeout und technische Providerfehler

Sobald der Creator aufgerufen wurde, kann ein externer Effekt nicht mehr sicher
ausgeschlossen werden.

Timeout, Verbindungsabbruch, Prozessfehler oder ungültiger Provider-Return
führen deshalb ebenfalls zu `outcome_unknown`.

Der technische Fehler wird anschließend detailfrei als
`ReleasePublicationCreateUnavailable` gemeldet. Er darf keinen unmittelbaren
zweiten Upload auslösen.

## Crash zwischen Commit und Provideraufruf

Ein persistiertes `write_started` bedeutet bereits „möglicher externer
Effekt“.

Ein späterer Retry führt keine Zielinspektion und keinen Create aus. Er hebt
den Zustand konservativ auf `outcome_unknown` und verlangt Reconciliation.

Damit bleibt auch ein Prozessverlust direkt vor oder während des
Provideraufrufs fail-closed.

## Exakter Retry

Ein Retry bei `outcome_unknown` liefert dasselbe Execution-/Attempt-/Handoff-
Tripel als pending Reconciliation zurück.

Die ursprüngliche flüchtige Acknowledgement wird nicht erfunden oder
rekonstruiert. Der Retry ruft weder LQ-256 noch den Creator erneut auf.

## Revocation zwischen Inspection und Start

Wird Channel-, Publisher-, Registry-, Signer- oder Key-Authority nach der
LQ-256-Inspektion entzogen, scheitert die erneute Write-Start-Prüfung neutral.

Der Attempt bleibt `prepared`, und der Creator wird nicht aufgerufen.

Es gibt keinen Grace-Boolean oder positiven Authority-Cache.

## Zustandskonsistenz

Zulässige aktive Kombinationen an dieser Grenze sind:

- Execution `prepared`, Attempt `prepared`;
- Execution `prepared`, Attempt `write_started` während des externen Calls;
- Execution `outcome_unknown`, Attempt `outcome_unknown` danach.

Andere unerwartete aktive Kombinationen werden nicht als Retry-Freigabe
interpretiert, sondern technisch fail-closed behandelt.

## Keine Erfolgsbehauptung

LQ-257 erzeugt kein Receipt und setzt keinen Status `published`.

Es speichert keine externe Artefaktidentität, Providerrevision,
Publikationszeit oder Sichtbarkeitsbehauptung.

Eine positive API-Antwort reicht ausdrücklich nicht als Publication-Fakt.

## Persistenz und Migrationen

LQ-257 verwendet die bestehenden LQ-253-Statusfelder.

Es gibt keine Migration, Tabelle oder Schemaänderung. Head bleibt
`20260817_0022` mit 22 Migrationen.

## Nachweis

Tests belegen:

- `write_started` ist vor dem Creator-Call committet;
- genau ein Creator-Call verwendet die Execution-ID als Idempotency-Key;
- positiver Return endet dennoch in `outcome_unknown`;
- Timeout und ungültige Acknowledgement bewahren `outcome_unknown`;
- Retry nach möglichem Effekt inspiziert und schreibt nie erneut;
- persistiertes `write_started` wird ohne Create konservativ wiederaufgenommen;
- Konflikt aus LQ-256 verhindert den Write-Start;
- Revocation nach Inspection verhindert den Write-Start;
- es entsteht kein Receipt;
- dieselbe Reihenfolge auf echtem PostgreSQL 16.

Die vollständige Pflichtsuite mit PostgreSQL 16 besteht:

```text
3166 passed, 180 warnings
```

Der temporäre PostgreSQL-Cluster wurde kontrolliert gestoppt und entfernt.

## Bewusst nicht enthalten

LQ-257 implementiert keinen konkreten Provideradapter, Credential-Lookup,
Read-after-write, externe Sichtbarkeitsprüfung, Reconciliation, Receipt,
Reassessment, Retry-Attempt 2, Withdrawal, CLI, Git- oder Deploymentaktion.

## Nächster Slice

LQ-258 sollte die verpflichtende read-only Unknown-Outcome-Reconciliation
implementieren. Sie muss das externe Ziel erneut inspizieren, bytegleichen
Erfolg, bestätigte Abwesenheit, Konflikt und weiterhin technischen Unknown-
Zustand unterscheiden und darf niemals blind erneut hochladen.
