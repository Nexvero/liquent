# LQ-544 — PostgreSQL Supervisor Cleanup Retention Chain Evidence

## Ergebnis

LQ-544 weist die vollständige Retentionkette auf echtem PostgreSQL nach.

Der Nachweis umfasst Migration, Policyadministration, Authority-Lifecycle,
Recovery, Evaluation, Operationsbindung, Clearance und Revocation.

## Migrierte Grundlage

Ein leerer Datenbankaufbau migriert bis Head `20260826_0042`.

Die geschlossenen Retentiontabellen bleiben danach leer; Migrationen erzeugen
weder Policyseed noch Authorityseed oder implizite Freigabe.

Zwei kumulativ sichtbare PostgreSQL-Hindernisse wurden minimal korrigiert:
Constraintnamen der Directory-Lifecycle-Migration bleiben innerhalb des
PostgreSQL-Limits, und Migration 0040 verändert Claims ohne erzwungenen
Tabellenneubau unter abhängigen Fremdschlüsseln.

## Policy- und Authority-Nachweis

Bootstrap ist persistent und idempotent.

Eine Verkürzung der Mindestaufbewahrung wird abgelehnt; eine Verlängerung
erzeugt eine neue aktive Revision und liefert bei Retry dasselbe Ergebnis.

Authority-Grant und Deaktivierung wirken auf spätere Entscheidungen.

Ein inaktiver verbleibender Authority-User gewährt keine Mutation. Die
principalfreie Offline-Recovery stellt aus effektivem Lockout eine aktive
Authority wieder her und bleibt bei Retry idempotent.

## Evaluation und Operation

Ein vollständig rekonstruiertes retired Directory wird gegen die aktuelle
persistente Policy evaluiert.

Nach Ablauf der Mindestaufbewahrung bindet die kontrollierte Operation genau
eine `eligible`-Decision atomar an Operation, Directory und Policyrevision.

Ein Retry derselben Operation liefert denselben First-Writer. PostgreSQL hält
weiterhin genau eine Decision; Clock und Decisiongenerator erzeugen keine
zweite Wirkung.

## Clearance und Revocation

Aktive User-, Scope-, Management-, Hold-, Recovery-, Reference- und
Terminal-Journal-Fakten erlauben eine Clearance nur dann, wenn die aktuelle
Eligibility-Decision exakt auf die aktive Policyrevision verweist.

Die erzeugte Clearance bindet dieselbe Decision wie die Retentionoperation.

Eine anschließende Policyersetzung bewahrt historische Operation-, Decision-,
Attempt- und Clearance-Fakten, entwertet aber deren Autorität für spätere
Wirkung sofort.

Sowohl read-only Clearance-Auflösung als auch Retry der Clearance-Erzeugung
enden danach detailfrei als Cleanup-Conflict.

Eine neue Cleanupwirkung erfordert zuerst eine neue ausdrückliche
Retentionoperation unter der neuen aktiven Revision.

## Behobene Schnittstellenabweichung

Der End-to-End-Nachweis hat zwei fehlende Typimporte im Retention-Portbestand
und einen falschen Journal-Lookup-Aufruf im Clearance-Resolver sichtbar
gemacht.

Die Korrekturen ändern keine Ports oder Signaturen: vorhandene Callable-
Lookups werden nun entsprechend ihrer bereits verdrahteten Form aufgerufen.

## Abgrenzung

LQ-544 ergänzt keine Migration, Tabelle, Route, Entry Point, Policyregel,
Scheduler-, Queue-, Worker- oder automatische Cleanupwirkung.

Die PostgreSQL-Instanz und Python-Umgebung des Nachweises sind ausschließlich
temporäre lokale Prüfmittel und kein Projekt- oder Deploymentbestand.

## Nächster Slice

LQ-545 führt den abschließenden Retention-Strang-Audit mit vollständiger
Regression, PostgreSQL-Suite, Inventar- und Diffprüfung durch.
