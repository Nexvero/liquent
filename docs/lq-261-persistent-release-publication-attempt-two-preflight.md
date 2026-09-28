# LQ-261 — Persistent Release Publication Attempt-Two Preflight

## Ergebnis

LQ-261 implementiert den persistenten Preflight für genau einen zweiten
Publication-Attempt nach einem bestätigten LQ-260-Abwesenheitsabschluss.

Der Slice prüft Artefakte, aktuelle Authority und das externe Ziel erneut und
legt Attempt 2 atomar als `prepared` an. Er schreibt kein Artefakt zum Provider.

## Eng begrenzter Einstieg

`prepare_retry_attempt` akzeptiert ausschließlich:

- die bestehende Execution-ID;
- die ID des abgeschlossenen ersten Attempts.

Der Aufrufer liefert keine Retry-Eignung, Rolle, Authority-Entscheidung,
Zielbeschreibung, Hashwerte oder Provider-Observation.

## Persistenter Recovery-Nachweis

Attempt 2 ist nur möglich, wenn das System of Record weiterhin genau diesen
Zustand enthält:

- Attempt 1 gehört zur Execution;
- Attempt 1 hat Nummer 1;
- Attempt 1 ist `reconciled` und besitzt eine Finish-Zeit;
- die Execution ist wieder `prepared`;
- der zugehörige LQ-260-Abschluss lautet `absence_confirmed`;
- dessen beim Abschluss persistierter Authority-Status war wahr.

Ein Conflict-Abschluss, ein Receipt oder ein `pending` Reassessment sperrt den
Preflight neutral.

## Gespeicherte Eignung ist keine aktuelle Authority

Der LQ-260-Wert `current_authority` ist nur eine notwendige historische
Vorbedingung. Er ist kein übertragbares Autorisierungsticket.

LQ-261 löst die aktuelle Authority bei jedem neuen Preflight erneut aus dem
System of Record auf.

## Aktuelle Channel- und Publisher-Bindung

Der Handoff muss weiterhin an den aktuellen Channel und exakt dessen aktuelle
Revision gebunden sein.

Die Channel-Revision muss aktiv sein und die erwartete Artifact-Class tragen.
Die persistente Publisher-Zuordnung für den Handoff muss weiterhin aktiv sein.

Eine inzwischen umgeschaltete Revision oder deaktivierte Publisher-Authority
sperrt Attempt 2.

## Aktuelle Registry-Bindung

Der aktuelle Registry-Set wird neu gelesen. Seine Policy, der gebundene Signer
und der gebundene Signing-Key müssen aktiv sein.

Eine nach dem Recovery-Commit erfolgte Revocation wirkt deshalb auf den
nächsten Preflight. Frühere positive Entscheidungen werden nicht gecacht.

## Frische Artefaktintegrität

Vor jeder neuen Zielinspektion führt LQ-261 die kontrollierte LQ-255-
Integritätsprüfung erneut aus.

Sie bindet weiterhin:

- Execution, Attempt 1 und Handoff;
- Paketversion;
- Bundle-, Wheel-, Checksums-, Signatur- und Promotion-Evidence-Hash;
- aktuelle Registry-Policy, Signer und Key;
- die lokal gebundenen Releaseartefakte.

Fehlende oder veränderte Artefakte erlauben keinen Attempt 2.

## Frisches Read-before-write

Auch eine frühere bestätigte Abwesenheit ist kein Write-Ticket.

Nach Integritäts- und Authority-Prüfung konstruiert LQ-261 das Ziel allein aus
persistiertem Channel- und Handoff-Kontext und liest es über den bestehenden
read-only Inspector erneut.

Nur eine erneut bestätigte Abwesenheit erlaubt die Vorbereitung von Attempt 2.

## Sichtbarer Zielzustand

Liefert der Inspector inzwischen eine Observation, entsteht kein Attempt 2.

Das gilt unabhängig davon, ob das sichtbare Artefakt inhaltlich passen könnte
oder einen Konflikt darstellt. LQ-261 klassifiziert und überschreibt keinen
inzwischen sichtbaren Providerzustand.

## Atomare Persistenz

Nach erfolgreichem Preflight prüft LQ-261 die persistenten Voraussetzungen
innerhalb der Schreibtransaktion erneut.

Auf PostgreSQL serialisiert eine kurze Control-Plane-Sperre konkurrierende
Attempt-2-Erzeugung gegen die beteiligten Publication- und Registry-Fakten.

Die Transaktion fügt genau einen neuen Attempt ein mit:

- neuer stabiler Attempt-ID;
- derselben Execution;
- Attempt-Nummer 2;
- Status `prepared`;
- persistenter Startzeit;
- leerer Finish-Zeit.

Execution und Handoff werden nicht neu erzeugt oder umgeschrieben.

## Kein Providerwrite

LQ-261 besitzt keinen Creator- oder Upload-Port.

Die erneute Zielabwesenheit und der persistente Attempt 2 bilden nur die
Voraussetzung für einen späteren kontrollierten Create-Slice. Es werden weder
Wheel noch Bundle, Signatur, Checksums oder Promotion Evidence übertragen.

## Exakter Retry

Existiert Attempt 2 bereits konsistent als `prepared`, liefert ein exakter
Retry denselben persistenten Attempt zurück.

Dieser Pfad führt keine erneute Artefaktprüfung, Providerinspektion oder
ID-Erzeugung aus. Er legt keinen dritten Attempt an.

Ein vorhandener, aber nicht konsistenter Attempt 2 wird nicht als neue
Publication-Chance interpretiert.

## Parallelität

Konkurrierende erfolgreiche Preflights können wegen der eindeutigen
Execution-/Attempt-Nummer-Bindung nur einen Attempt 2 persistieren.

Nach der Serialisierung liest der Verlierer den bereits angelegten Attempt und
liefert denselben stabilen Fakt zurück.

## Neutrale Ablehnung

`None` bedeutet ohne Detailoffenlegung, dass aktuell kein sicherer zweiter
Attempt vorbereitet werden darf. Dazu zählen insbesondere:

- fehlender oder nicht passender Absence-Recovery-Abschluss;
- nicht mehr `prepared` befindliche Execution;
- Receipt oder `pending` Reassessment;
- aktuelle Channel-, Publisher- oder Registry-Revocation;
- fehlende oder nicht mehr passende Artefakte;
- ein inzwischen sichtbares externes Ziel.

Diese neutrale Ablehnung ist kein technischer Fehler und erzeugt keine
Mutation.

## Detailfreie technische Nichtverfügbarkeit

`ReleasePublicationRetryAttemptUnavailable` vereinheitlicht bestehende
technische Fehler detailfrei, darunter:

- Datenbank- und Strukturfehler;
- nicht sicher dekodierbare persistente Fakten;
- technische Integritäts- oder Providerfehler;
- ungültige ID-Generator- oder Clock-Ergebnisse;
- nicht sicher abschließbare Transaktionen.

Die Grenze gibt keine IDs, Hashwerte, SQL-, Registry-, Provider-, Pfad- oder
Credentialdetails preis.

## Keine Migration

LQ-261 nutzt die bestehende Attempt- und Recovery-Persistenz.

Es gibt keine neue Tabelle, Spalte, Constraint, Migration oder Bootstrap-
Mutation. Der lineare Head bleibt `20260818_0023` mit 23 Migrationen.

## Nicht Bestandteil dieses Slices

LQ-261 implementiert insbesondere nicht:

- den Provider-Create für Attempt 2;
- einen automatischen Upload;
- Attempt 3 oder eine allgemeine Retry-Schleife;
- neue Receipt-, Recovery- oder Reassessment-Regeln;
- neue CLI-, Runtime-, Deployment- oder Wiring-Entscheidungen.

## Nachweis

Gezielte Tests belegen:

- frische Integritäts-, Authority- und Abwesenheitsprüfung;
- atomare Persistenz genau eines vorbereiteten Attempt 2;
- Revocation nach LQ-260 sperrt vor dem Provider-Read;
- ein inzwischen sichtbares Ziel sperrt Attempt 2;
- Conflict-Recovery ist nicht retry-fähig;
- technische Providerfehler bleiben detailfrei und mutationslos;
- exakter Retry vermeidet Integritäts-, Provider- und Generatoraufrufe;
- denselben erfolgreichen Ablauf auf echtem PostgreSQL 16.

Die vollständige Pflichtsuite mit PostgreSQL 16 besteht:

```text
3207 passed, 333 warnings
```

Der nächste Slice führt den kontrollierten immutable Create für den
vorbereiteten Attempt 2 aus. Er muss unmittelbar vor dem Write erneut lesen und
dieselben Unknown-Outcome-Sicherungen wie Attempt 1 erhalten.
