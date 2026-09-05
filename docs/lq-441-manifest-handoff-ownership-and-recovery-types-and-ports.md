# LQ-441 — Manifest Handoff Ownership and Recovery Types and Ports

## Ergebnis

LQ-441 konkretisiert den LQ-440-Vertrag mit geschlossenen Domainwerten und
minimalen quellenspezifischen Ports.

Der Slice implementiert noch keine Persistenz oder Composition.

## Stabile Identitäten

Neu sind repr-freie unveränderliche IDs für:

- Execution-Claim;
- kontrollierten Execution-Owner;
- terminalen Execution-Endnachweis;
- Recovery-Claim;
- kontrollierten Recovery-Owner.

Alle IDs verlangen einen nicht leeren String und tragen keine Ableitung aus
Attempt, Actor, PID, Host, Zeit oder Pfad.

## Execution-Claim

`ClaimedManifestHandoffExecution` bindet Claim-ID, Attempt-ID und
Execution-Owner an serverseitige Claim- und Leasezeiten.

Beide Zeiten müssen aware UTC sein; Leaseende muss strikt nach Claimzeit
liegen.

`writer_authorized` ist nicht setzbar und fest `false`.

Der Claim allein öffnet den Writer daher ausdrücklich nicht.

## Lease-Erneuerung

`RenewedManifestHandoffExecutionLease` bindet dieselbe Claim-/Owneridentität
an serverseitige Renewal- und Ablaufzeit.

Auch hier muss die Dauer positiv sein.

`recovery_authorized` ist nicht setzbar und fest `false`.

Eine erneuerte oder abgelaufene Lease trifft keine Prozessendeentscheidung.

## Claimed Writer Start

`StartedManifestHandoffExecution` bindet genau:

- Execution-Claim;
- Attempt;
- `writer_started`-Observation-ID;
- kontrollierten Execution-Owner;
- serverseitige Startzeit.

Damit reicht der bestehende ungebundene Startappend für die spätere
Ownershipfoundation nicht aus.

Der neue Port öffnet keine generische Observationart.

## Terminale Endarten

`ManifestHandoffExecutionEndKind` ist geschlossen auf:

- `outcome_secured`;
- `outcome_unknown`;
- `start_not_confirmed`.

`RecordedManifestHandoffExecutionEnd` bindet End-ID, Claim, Attempt, Art und
serverseitige terminale Zeit.

Exitcode, Signal, PID, Host, Fehlermeldung und Caller-Boolean sind keine
Felder.

## Warum der Enum nicht caller-gesteuert ist

Der Enum ist ein gespeicherter Ergebniswert, aber kein Parameter eines
generischen öffentlichen Endports.

Die Prozessgrenze besitzt drei getrennte Methoden für die drei direkten
Ausgangsquellen.

Untrusted Code kann daher nicht `record_end(kind=...)` aufrufen.

## Recoveryrequest

`ManifestHandoffRecoveryRequest` enthält ausschließlich:

- intern kontrollierte Recovery-Claim-ID;
- Actor-UserId;
- Registry-Scope-ID;
- validierten Handoffnamen;
- kontrollierte Recovery-Owner-ID.

IDs, Actor und Scope bleiben repr-frei.

Der Request enthält keinen Pfad, Attemptoverride, Prozessende-Boolean,
Outcome, Digest, Rolle oder Allow-Wert.

## Recovery-Claim

`ClaimedManifestHandoffRecovery` bindet Recovery-Claim, aus Persistenz
aufgelöstes Attempt, beendeten Execution-Claim, Recovery-Owner und
serverseitige Claimzeit.

`writer_authorized` und `cleanup_authorized` sind nicht setzbar und fest
`false`.

Der Wert autorisiert ausschließlich den späteren read-only Recoveryablauf.

## Recoveryobservation

`AppendedManifestHandoffRecoveryObservation` bindet eine bestehende
Reconciliationobservation an den Recovery-Claim.

Zulässig sind ausschließlich die fünf LQ-427-Arten absent, temporary-only,
handed-off, handed-off-pending-cleanup und conflict.

Writer-, Cleanup- und reserved-Arten werden abgelehnt.

Die bestehende Faktenmatrix bleibt unverändert wirksam.

## Detailfreier Konflikt

`ManifestHandoffOwnershipConflict` ist ein leerer unveränderlicher Wert.

Er vereinheitlicht divergente Wiederverwendung von Claim-, Owner-, End- oder
Observationbindungen ohne gespeicherte Details auszugeben.

Technische Unverfügbarkeit bleibt davon getrennt und erhält in LQ-441 keinen
neuen Exceptionnamen.

## Autorisierter Execution-Claim-Port

`AuthorizedManifestHandoffExecutionClaim.claim_execution` erhält kontrollierte
Claim-ID, Attempt-ID, Actor und Execution-Owner.

Der spätere Adapter muss Attempt, Actor, Scope, aktuelle Aktivität und
Executionfähigkeit aus dem System of Record binden.

Ein Claimwert des Callers ist keine Allow-Entscheidung.

Die Rückgabe ist Claim, detailfreier Konflikt oder neutral `None`.

## Lease-Port

`ManifestHandoffExecutionLeaseRenewal.renew_execution_lease` erhält nur Claim
und Owner.

Zeit, Dauer und Ablaufentscheidung kommen nicht vom Caller.

Die Rückgabe kann Liveness aktualisieren, erteilt aber keine Recovery- oder
Takeoverfähigkeit.

## Claimed-Start-Port

`ControlledManifestHandoffClaimedWriterStart.start_claimed_execution` erhält
nur Observation-ID, Execution-Claim und Owner.

Attempt, Scope, Actor und Name müssen aus dem Claimbestand aufgelöst werden.

Nur ein aktueller passender Claim darf genau einen gebundenen Start erzeugen.

Der Port akzeptiert keinen Pfad, Namen, Outcome oder Allow-Wert.

## Quellenspezifischer Endport

`ControlledManifestHandoffExecutionEnd` bietet ausschließlich:

- `record_outcome_secured`;
- `record_outcome_unknown`;
- `record_start_not_confirmed`.

Jede Methode bindet intern kontrollierte End-ID, Claim und Owner.

Es gibt keine generische Endart, Prozessdetailmap oder freie Terminalzeit.

## Autorisierter Recovery-Claim-Port

`AuthorizedManifestHandoffRecoveryClaim.claim_recovery(request)` erhält nur
den geschlossenen Recoveryrequest.

Der spätere Adapter muss das Attempt, den terminal belegten Execution-Claim,
aktuelle Actor-/Scopeaktivität und explizite Recoveryfähigkeit aus Persistenz
auflösen.

Leaseablauf allein darf niemals einen Claim liefern.

Bereits abgeschlossener oder anderweitig besessener Recoverybedarf endet
neutral.

## Recovery-Append-Port

`ControlledManifestHandoffRecoveryObservationAppend` besitzt fünf getrennte
Methoden entsprechend den direkten LQ-427-Ergebnissen.

Jede Methode erhält intern erzeugte Observation-ID, Recovery-Claim und
Recovery-Owner; nur faktentragende Arten erhalten `ManifestHandoffFacts`.

Attempt, Scope und Name sind keine Parameter und werden aus dem Claimbestand
gebunden.

Es gibt keine Writer- oder Cleanupmethode an diesem Port.

## Authority und Revocation

SessionPrincipal identifiziert den Actor, erteilt aber keine Claim- oder
Recoveryauthority.

Execution- und Recoveryentscheidungen müssen aktuelle aktive Fakten aus dem
System of Record lesen.

Ordinary Membership und Researchpermissions sind keine Ersatzfähigkeit.

Revocation muss jede spätere Claimentscheidung sperren.

Mechanische End- und Outcomesicherung eines bereits kontrolliert begonnenen
Ablaufs bleibt davon getrennt.

## Neutralität und technische Unverfügbarkeit

Fehlende Authority, nicht recoverbarer Zustand, fremder Owner oder bereits
abgeschlossener Ausgang liefert neutral `None`.

Divergente stabile Identitätswiederverwendung liefert den leeren Konflikt.

Beschädigte Historie, mehrdeutige Bindung und Infrastrukturfehler bleiben
detailfreie technische Unverfügbarkeit.

Keiner dieser Ausgänge gibt IDs, Actor, Scope, Pfade oder Prozessdetails aus.

## Keine Fencingfiktion

Kein Typ trägt eine Generation, ein Takeoverflag oder einen
`process_ended`-Boolean.

Leasewerte autorisieren keine Recovery.

Nur ein später direkt gesicherter terminaler Endfakt kann die persistente
Recoveryprüfung öffnen.

Der bestehende Writer wird nicht verändert und erhält keinen Fencingtoken.

## Retention und Nichtwiederverwendung

Die stabilen IDs und ihre Bindungen sind nicht reassigbar oder
wiederverwendbar.

LQ-441 definiert keine Delete-, Release-, Reset-, Rebind- oder
Upsertoberfläche.

Die Retentionuntergrenzen aus LQ-440 bleiben unverändert, ohne konkrete Frist
oder physische Ablageentscheidung.

## Migration und Implementierung

Revision und Head bleiben `20260819_0028`.

Der Slice ergänzt keine Tabelle, Spalte, SQL-Abfrage, Migration, Seed- oder
Bootstrapdaten.

Keiner der neuen Ports besitzt bereits einen Adapter.

LQ-439 wird noch nicht auf claimed start umgestellt.

## Kein Wiring

Es gibt keinen Supervisor, Prozessstart, Reconcilerwrapper, Composer,
Operator, CLI, Route, Scheduler, Compose-, CI- oder Production-Wiringpfad.

Kein Dateisystem-, Environment-, Datenbank-, Clock- oder Netzwerkzugriff wird
ausgeführt.

## Tests

Fokussierte Tests belegen:

- repr-freie stabile IDs;
- positive aware-UTC-Leases ohne Autorisierungsflags;
- claimed Startbindung und geschlossene Endarten;
- pfad- und booleanfreien Recoveryrequest;
- nicht überschreibbare Writer-/Cleanup-Nichtautorisierung;
- ausschließlich fünf Reconciliationarten im Recoverywert;
- getrennte quellenspezifische Portsignaturen;
- fehlende generische End-, Writer- und Cleanupmethode;
- Roadmap- und Folgeslicebindung.

## Nichtziele

LQ-441 implementiert keine Claim-, Lease-, End-, Recovery- oder
Observationpersistenz.

Bestandsverankerung, Scope-/Authority-Bootstrap, Cleanup und finale
Evidence-Retention bleiben separat.

Staging, Commit, Push, Build, Signatur, Promotion, Publication und Deployment
werden weder ausgeführt noch autorisiert.

## Nächster Slice

LQ-442 sollte die additive persistente Execution-Ownership- und
Recoveryfoundation für diese geschlossenen Fakten implementieren.

Supervisoradapter, claimed Composerintegration, Recoverycomposition,
Bestandsverankerung, Cleanup und finale Evidence-Retention bleiben danach
separate Slices.
