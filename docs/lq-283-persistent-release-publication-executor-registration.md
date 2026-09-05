# LQ-283 — Persistent Release Publication Executor Registration

## Ergebnis

LQ-283 implementiert die in LQ-282 entschiedene persistente Registrierung
technischer Publication-Executor-Identitäten.

Der Slice ergänzt einen stabilen Registration-ID-Typ, einen geschlossenen Port,
eine atomare PostgreSQL-/SQLite-Persistenzgrenze und Migration
`20260819_0025`.

Es entsteht noch kein Operator, Entry Point, Handoff, Execution oder Attempt.

## Stabile getrennte Identitäten

`ReleasePublicationExecutorRegistrationId` identifiziert eine unveränderliche
Registrierungsentscheidung.

`ReleasePublicationExecutorId` identifiziert den daraus entstandenen
technischen Executor.

Beide Werte sind stabile, nicht neu zuordenbare interne Fakten. Sie werden
weder als Rolle noch als Capability oder Publication-Authority interpretiert.

Die repr-freien Value Objects verhindern eine versehentliche Ausgabe ihrer
Werte über Standardrepräsentationen.

## Geschlossener Port

`ReleasePublicationExecutorRegistration.register` akzeptiert ausschließlich
eine `ReleasePublicationExecutorRegistrationId`.

Der Aufrufer liefert keine Executor-ID, Authority, Rolle, Allow-Entscheidung,
Workspace-, Publisher-, Channel-, Host- oder Credentialbehauptung.

Die Executor-ID wird erst innerhalb der atomaren Persistenzgrenze durch den
injizierten sicheren Generator erzeugt.

## Atomare Entscheidung

Ein erfolgreicher Erstaufruf persistiert in genau einer Transaktion:

- einen neuen Fakt im bestehenden Executor-Inventar;
- eine unveränderliche Registration-ID-/Executor-ID-Bindung.

Erst nach erfolgreicher Persistenz wird
`RegisteredReleasePublicationExecutor` ausgegeben.

Ein Generatorfehler, ein ungültiger Generatorwert oder ein Datenbankfehler
rollt beide Schreibvorgänge zurück.

## Exakter Retry

Ein späterer Aufruf mit derselben Registration-ID liest die committete Bindung
und liefert dieselbe Executor-ID.

Der Generator wird beim exakten Retry nicht erneut aufgerufen.

Parallel konkurrierende Erstaufrufe werden unter PostgreSQL durch eine
serverseitige Tabellensperre linearisiert. Beide Beobachter erhalten dieselbe
committete Entscheidung; es entstehen genau ein Executor und eine Bindung.

SQLite unterstützt denselben funktionalen Vertrag für lokale und
Einzelprozessnutzung. Der verpflichtende Mehrverbindungsnachweis läuft gegen
PostgreSQL 16.

## Verschiedene Registration-IDs

Verschiedene Registration-IDs erzeugen getrennte Executor-Identitäten.

Die eindeutige Executor-Bindung verhindert, dass derselbe Executor später
einer anderen Registrierungsentscheidung zugeordnet wird.

Registration- und Executor-ID werden nicht gelöscht, recycelt oder unter
anderer Bedeutung wiederverwendet. Historische Bindungen müssen mindestens so
lange erhalten bleiben wie jede referenzierende Execution, jeder Attempt und
jeder Auditnachweis.

## Keine Authority

Die Existenz eines Executors erlaubt keinen Handoff und keine Veröffentlichung.

Insbesondere gewährt sie keine:

- Publisher- oder Channel-Authority;
- Registry-, Signer- oder Key-Authority;
- Promotion-, Reviewer- oder Providerberechtigung;
- Workspace-Mitgliedschaft oder Research-Permission.

Alle fachlichen Authority-Entscheidungen bleiben aktuell an das System of
Record gebunden.

## Fehlergrenze

Ungültige Aufrufe, beschädigte Persistenz, Generatorfehler, fehlende Migration
und technische Datenbankfehler werden als vorhandenes detailfreies technisches
Unavailability-Muster nach außen vereinheitlicht.

Die Grenze gibt keine SQL-, DSN-, Tabellen-, Generator- oder
Verbindungsdetails aus und bewahrt keine Exception-Chain.

Eine neutrale Ablehnung ist für diesen geschlossenen additiven Port nicht
erforderlich: Jede valide neue Registration-ID darf genau einen technischen
Executor erzeugen, und ein exakter Retry löst die bestehende Entscheidung auf.

## Migration

Revision `20260819_0025` folgt linear auf `20260819_0024`.

Sie ergänzt ausschließlich die Entscheidungstabelle mit:

- stabiler Registration-ID als Primärschlüssel;
- eindeutiger Executor-ID;
- referenzieller Bindung an das bestehende Executor-Inventar;
- Mindestprüfung auf eine nichtleere Registration-ID.

Die Migration seedet keinen Executor und keine Registrierung.

Der Operational-Bundle-Gate erwartet jetzt exakt 25 lineare Migrationen und
Head `20260819_0025`.

## Bewusst nicht enthalten

LQ-283 implementiert keine:

- CLI, Requestdatei oder geschützte Ausgabe;
- Operator-Composition oder Entry-Point-Verdrahtung;
- Executor-Aktivierung, Deaktivierung, Rotation oder Attestation;
- Handoff-, Execution-, Attempt- oder Provider-Mutation;
- Registry-, Publisher-, Channel- oder Signing-Änderung;
- automatische Registrierung beim Worker-Start;
- Lösch-, Recovery- oder Reassignment-Funktion.

## Nachweis

Die Tests belegen Portgeschlossenheit, atomare Erstregistrierung, identischen
Retry ohne erneute Generierung, getrennte Ergebnisse für getrennte Requests,
Rollback bei ungültigen Generatorwerten, detailfreie Unavailability und
repr-freies Verhalten.

Ein PostgreSQL-Integrationstest belegt den konkurrierenden exakten Retry gegen
getrennte Verbindungen.

Migration-Gate und Operational-Bundle-Prüfung sind auf den neuen linearen Head
angehoben.

## Nächster Slice

LQ-284 implementiert den owner-only Executor-Registrierungsoperator und den in
LQ-282 festgelegten autorisierten Handoff-Operator als getrennte Prozessgrenzen.
