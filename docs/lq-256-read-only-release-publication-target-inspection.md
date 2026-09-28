# LQ-256 — Read-only Release Publication Target Inspection

## Ergebnis

LQ-256 implementiert die kontrollierte Read-before-write-Entscheidung für ein
externes Publication-Ziel.

Nach erfolgreichem LQ-255-Integritätsnachweis löst der Slice den aktuellen
Channelkontext aus dem System of Record auf und inspiziert das Ziel genau
einmal read-only.

Es gibt keinen Create-, Upload- oder sonstigen Provider-Write.

## Öffentliche Grenze

`inspect_publication_target` akzeptiert ausschließlich:

- bestehende Execution-ID;
- bestehende Attempt-ID.

Der Aufrufer liefert keine URL, Providerart, Zielbezeichnung, Paketversion,
Hashwerte, Rollen oder Allow-Entscheidung.

## Integrität zuerst

Vor jeder Providerinspektion muss der vollständige LQ-255-Nachweis positiv
sein.

Damit sind Bundle, Wheel, SHA256SUMS, SSHSIG, historische Evidence und aktuelle
Signer-/Key-Authority bereits bytegenau geprüft.

Lehnt LQ-255 neutral ab, wird der Provider nicht aufgerufen. Technische
Integritätsnichtverfügbarkeit bleibt auch in LQ-256 technische
Nichtverfügbarkeit.

## Aktuelle Zielauflösung

Nach dem Integritätscheck liest LQ-256 erneut aktuell:

- vorbereitete Execution und Attempt 1;
- unveränderten Handoff;
- aktuellen Channel und exakte Revision;
- aktive Channeldefinition;
- aktive Publisher-Zuordnung;
- vorhandene Receipts;
- offene Reassessments.

Die Datenbanktransaktion ist beendet, bevor der Provideradapter aufgerufen
wird.

## Kontrollierter Zielkontext

`ReleasePublicationTarget` enthält ausschließlich:

- Channel-ID und Revision;
- kontrollierte Providerart;
- kanonischen Zielnamen;
- Paketname;
- Paketversion.

Der Zielname ist repr-frei. Credentials, Basis-URL, Tokens und freie
Providerparameter sind nicht Bestandteil des Domainobjekts.

Paketname muss weiterhin `liquent` sein. Paketversion muss exakt dem
verifizierten LQ-255-Payload entsprechen.

## Getrennter Inspector-Port

`ReleasePublicationTargetInspector` besitzt nur eine read-only Methode:

`inspect_target(target)`.

Der Port erhält weder Datenbankengine noch Artifact Source, Authority-Snapshot,
SessionPrincipal oder Uploadmethode.

LQ-256 implementiert bewusst keinen konkreten Netzwerkprovider.

## Abwesendes Ziel

`None` vom Providerinspector bedeutet ausschließlich: Die kontrollierte
Paketversion ist am Ziel bestätigt nicht vorhanden.

LQ-256 erzeugt dann die Entscheidung `CREATE_ALLOWED`.

Diese Entscheidung führt selbst keinen Create aus und ist kein dauerhaftes
Publication-Ticket. Ein späterer Write-Slice muss Authority und Zustand erneut
angemessen binden.

## Bytegleich vorhandenes Ziel

Ein vorhandenes Ziel wird als bytegleich behandelt, wenn:

- es tatsächlich sichtbar ist;
- Paketname exakt übereinstimmt;
- Paketversion exakt übereinstimmt;
- beobachteter Wheel-SHA-256 exakt dem LQ-255-Payload entspricht.

Das Ergebnis ist `RECONCILIATION_REQUIRED`.

Ein zweiter Upload ist in diesem Fall ausdrücklich unzulässig. Die externe
Realität muss in einem späteren Slice read-only bestätigt und als Receipt
reconciled werden.

## Konflikt

Ein vorhandenes Ziel mit abweichendem Paketnamen, abweichender Version,
abweichendem Wheel-Hash oder fehlender Sichtbarkeit ergibt `CONFLICT`.

Der Konflikt enthält keine Detailausgabe über beobachtete Unterschiede und
autorisiert keinen Write.

Bestehende externe Artefakte werden niemals überschrieben, ersetzt oder
gelöscht.

## Provider-Observation

`ReleasePublicationTargetObservation` bindet:

- kanonische externe Artefaktidentität;
- unveränderliche Providerrevision;
- beobachteten Paketnamen;
- beobachtete Paketversion;
- beobachteten Wheel-Hash;
- Sichtbarkeitsstatus.

Externe Identität und Providerrevision sind repr-frei und werden in LQ-256
nicht persistiert.

## Geschlossene Entscheidung

`ReleasePublicationTargetDecisionKind` besitzt exakt drei Werte:

- `CREATE_ALLOWED`;
- `RECONCILIATION_REQUIRED`;
- `CONFLICT`.

`InspectedReleasePublicationTarget` bindet die Entscheidung an denselben
kontrollierten Zielkontext und dasselbe verifizierte LQ-255-Payload.

Nur `CREATE_ALLOWED` besitzt keine Observation. Die beiden vorhandenen
Zielzustände verlangen eine konkrete Observation.

## Fail-closed Authority

Ein inzwischen inaktiver Channel, stale Revision oder inaktiver Publisher
beendet die Entscheidung neutral vor Providerzugriff.

Ein vorhandenes Receipt oder `pending` Reassessment sperrt die Inspektion
ebenfalls.

Damit kann ein historischer positiver Attempt nicht als aktueller
Providerzugriff verwendet werden.

## Keine positive Cachewirkung

Weder der LQ-255-Nachweis noch eine LQ-256-Entscheidung werden als positiver
Authority-Cache gespeichert.

Die Rückgabe ist ein kurzlebiges read-only Ergebnis für die kontrollierte
Orchestrierung. Ein späterer Write muss weiterhin gegen Revocation und
Konkurrenz abgesichert werden.

## Technische Nichtverfügbarkeit

`ReleasePublicationTargetInspectionUnavailable` vereinheitlicht detailfrei:

- Datenbank- und Strukturfehler;
- technische LQ-255-Fehler;
- ungültige Providerantwortstypen;
- Provider-Timeout oder unklaren Read-Zustand;
- beschädigte Ziel- oder Paketbindung.

Der Fehler trägt keine URL, Providerantwort, IDs, Hashwerte, SQL-, Credential-
oder Netzdetails.

Technisch unklar ist niemals gleichbedeutend mit „Ziel fehlt“ und erlaubt
deshalb keinen Create.

## Keine Persistenzmutation

LQ-256 ändert weder Execution noch Attempt.

Insbesondere entstehen kein `write_started`, `outcome_unknown`, Receipt oder
Reassessment. Selbst `RECONCILIATION_REQUIRED` wird noch nicht persistiert.

Es gibt keine Migration oder Tabelle. Head bleibt `20260817_0022` mit 22
Migrationen.

## Nachweis

Tests belegen:

- bestätigte Abwesenheit ergibt ausschließlich `CREATE_ALLOWED`;
- bytegleich sichtbares Ziel ergibt `RECONCILIATION_REQUIRED`;
- abweichender Hash, Name, Version oder Sichtbarkeit ergibt `CONFLICT`;
- inaktiver Publisher verhindert Providerzugriff;
- unbekannter Attempt verhindert Integritäts- und Providerzugriff;
- Providerfehler bleiben detailfreie technische Nichtverfügbarkeit;
- Execution und Attempt bleiben unverändert `prepared`;
- dieselbe kontrollierte Zielauflösung auf echtem PostgreSQL 16.

Die vollständige Pflichtsuite mit PostgreSQL 16 besteht:

```text
3158 passed, 152 warnings
```

Der temporäre PostgreSQL-Cluster wurde kontrolliert gestoppt und entfernt.

## Bewusst nicht enthalten

LQ-256 implementiert keinen konkreten Provideradapter, HTTP-Client,
Credential-Lookup, Upload, immutable Create, Idempotency-Key, Write-Started-
Transition, Unknown Outcome, Reconciliation, Receipt, Reassessment, CLI, Git-
oder Deploymentaktion.

## Nächster Slice

LQ-257 sollte den atomaren Write-Start und die kontrollierte immutable
Create-Grenze implementieren. Vor dem Provider-Write muss es die
`CREATE_ALLOWED`-Bindung, aktuelle Authority und Konkurrenz erneut absichern;
ein möglicher externer Effekt muss danach zwingend als Erfolg oder
`outcome_unknown` festgehalten werden.
