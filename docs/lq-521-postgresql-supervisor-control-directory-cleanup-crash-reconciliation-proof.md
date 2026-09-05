# LQ-521 — PostgreSQL Supervisor Control-Directory Cleanup Crash Reconciliation Proof

## Ergebnis

LQ-521 ergänzt den positiven PostgreSQL-End-to-End-Nachweis für die echte
read-only Reconciliation eines nach Crash verbliebenen Cleanup-Write-Claims.

Absent, unverändert present und conflict werden getrennt belegt.

## Wegwerfbares PostgreSQL

Jeder parametrisierte Fall erhält über die bestehende Integrationfixture eine
eigene bis Head migrierte Wegwerfdatenbank.

Es gibt keinen SQLite-, In-Memory-, Adapter- oder Compositionfallback.

Die bestehende verpflichtende PostgreSQL-Gatepolicy bleibt unverändert.

## Wiederverwendete Ausgangskette

Jeder Fall verwendet die vollständige LQ-520-User-, Scope-, Handoff-, Backend-,
Journal-, Terminal-, Directory- und Cleanup-Authority-Ausgangskette.

Das Control Directory ist retired und bindet ein gültiges privates Leaf.

Decision, Management, Hold, Recovery und Reference bleiben vollständig
persistiert und positiv.

## Persistenter Crashzustand

Der Test ergänzt für jedes Directory einen eigenen Cleanup-Attempt im Zustand
`write_claimed`.

Attempt, Actor, Directory, Decision, Clearance, Scope, Terminalobservation und
alle gebundenen Revisionen sind vollständig konsistent.

Eine eigene Claimzeile bindet Claim-, Attempt-, Directory-, Clearance- und
Preflight-ID sowie monotone Prepared- und Claimed-Zeiten.

## Warum write_claimed

`write_claimed` repräsentiert den maximal unsicheren Neustartpunkt: Die
physische Wirkung kann bereits begonnen oder abgeschlossen sein, während der
Outcome-Commit fehlt.

Der Zustand beweist weder Abwesenheit noch unveränderte Anwesenheit.

Ein zweiter Remove wäre deshalb unzulässig.

## Drei getrennte physische Fälle

Der Test ist über `absent`, `present` und `conflict` parametrisiert.

Jeder Fall läuft mit eigener Datenbank, eigenem privaten Root und eigenem
Claim, sodass Ergebnisse keine Fakten teilen.

## Absent

Für absent wird das exakt persistierte leere Leaf vor dem Operatoraufruf
entfernt.

Der Root selbst bleibt sicher und unverändert gebunden.

Der echte Inspector muss die bestätigte Leafabwesenheit als `absent`
klassifizieren.

## Present

Für present bleibt das private leere `0700`-Leaf unverändert bestehen.

Da keine persistenten Artefaktrecords existieren, ist das exakte erwartete
Inventar ebenfalls leer.

Der echte Inspector muss diesen vollständigen Gleichstand als `present`
klassifizieren.

## Conflict

Für conflict erhält das Leaf eine zusätzliche private reguläre Datei mit
festen Bytes.

Diese Datei gehört nicht zum leeren persistenten Artefaktset.

Der Inspector muss das abweichende Inventar als `conflict` klassifizieren und
darf die Datei nicht entfernen oder verändern.

## Physischer Vorher-Nachher-Beweis

Vor jedem Reconcile-Aufruf erfasst der Test einen Snapshot aus Leafanwesenheit,
Leafmodus, Namen, Bytes und Dateimodi.

Nach dem echten Operatorlauf muss der Snapshot bytegenau identisch sein.

Damit sind auch im conflict-Fall Reparatur und Cleanup ausgeschlossen.

## Echter Operatorpfad

Jeder Fall ruft den echten LQ-519-`reconcile`-Befehl über private URL-, Backend-,
Root- und Requestdateien auf.

Attempt- und Directory-ID sind die einzigen fachlichen Requestwerte.

Es gibt keinen Monkeypatch, Fake-Inspector oder direkten Aufruf des
Reconciliationadapters.

## Unknown-Sicherung vor Inspection

Die LQ-516-Composition muss den gefundenen `write_claimed`-Attempt zuerst über
LQ-514 als Unknown persistieren.

Erst der dadurch dauerhaft gesperrte physische Retrypfad darf die read-only
Inspection erreichen.

Der Test belegt diese Zwischensicherung durch das gesetzte persistente
`unknown_at` im terminalen Datensatz.

## Genau eine read-only Inspection

Der Operator ruft ausschließlich die LQ-516-Reconciliation auf.

Die Composition besitzt keine Schleife und der lokale Inspector keine
Remove-Methode.

Der unveränderte physische Snapshot belegt zusätzlich die Wirkungslosigkeit
des konkreten Laufs.

## Geschlossene sichtbare Ergebnisse

stdout enthält exakt Attempt-ID, Directory-ID und den jeweiligen Outcome
`absent`, `present` oder `conflict`.

Claim-, Clearance-, Revision-, Root-, Datei- und Datenbankdetails verlassen die
Grenze nicht.

## Terminale Persistenz

Nach jedem Lauf ist der Attempt `reconciled`.

`reconciliation_outcome` entspricht exakt dem physischen Fall und
`reconciled_at` ist gesetzt.

Fachliches Cleanup-Outcome und `completed_at` bleiben leer.

## Monotone Zeiten

Persistiert gilt
`reconciled_at >= unknown_at >= write_claimed_at`.

Damit wird weder die Crashsicherung noch die Inspection zeitlich vor den
historischen Claim gesetzt.

## Keine Claimwiederholung

Für den Attempt existiert nach Reconciliation weiterhin genau eine
Write-Claim-Zeile.

Es wird kein neuer Attempt, Preflight, Clearance- oder Claimwert erzeugt.

Keiner der drei terminalen Reconciliationausgänge autorisiert einen Retry.

## Keine Productionänderung

LQ-521 verändert keinen Operator, Adapter, Domainwert, Port oder Entry Point.

Es ergänzt keine Migration, Tabelle, Spalte, Produktions-SQL-, Discovery-,
Batch-, Scheduler- oder automatische Aktivierungswirkung.

Head bleibt `20260826_0040` mit 40 linearen Migrationen.

## Tests

Eine statische Begleitprüfung sichert echte PostgreSQL-Fixture, vollständigen
Claimzustand, alle drei physischen Fälle, echten Operatoraufruf, unveränderte
Snapshots und terminale monotone Persistenz ab.

## Nächster Slice

LQ-522 sollte die gesamte Control-Directory-Cleanup-Kette von Retentionvertrag
bis Operator und PostgreSQL-Beweisen abschließend auf offene Production-,
Recovery- und Betriebsblocker auditieren.

Automatische Planung, Directorydiscovery und Batchcleanup bleiben geschlossen.
