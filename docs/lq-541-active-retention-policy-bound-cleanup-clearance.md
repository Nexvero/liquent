# LQ-541 — Active Retention Policy-bound Cleanup Clearance

## Ergebnis

LQ-541 bindet Cleanup-Clearance-Erzeugung, Clearance-Auflösung und spätere
Write-Claim-Revalidierung an die weiterhin exakt aktive Retentionpolicy.

Eine historische `eligible`-Decision allein kann keine neue oder fortgeltende
Cleanupauthority mehr tragen.

## Aktuelle Policyrevision

Die persistente Clearancegrenze liest den Singleton der geschlossenen
Datenklasse direkt aus dem System of Record.

Die Revision der aktuellen `eligible`-Decision muss exakt mit der aktiven
Policyrevision übereinstimmen.

Fehlende, deaktivierte oder ersetzte Policy liefert keine positive Clearance.

Es gibt keinen Fallback auf eine historische Revision oder Defaultpolicy.

## Clearance-Erzeugung

Die aktive Policyprüfung erfolgt innerhalb derselben serialisierten
Transaktion wie Directory-, Journal-, Decision-, Management-, Hold-, Recovery-
und Referenceprüfung.

Nur nach positiver exakter Revisionsbindung dürfen Attempt und Clearance
atomar entstehen.

Ein Policywechsel vor Commit kann nicht unbemerkt mit einer alten Decision
freigegeben werden.

## Retry

Auch ein Retry einer bereits angelegten Clearance revalidiert alle aktuellen
Fakten einschließlich der aktiven Policyrevision.

Ein zwischenzeitlicher Policywechsel führt detailfrei zum bestehenden
Conflict und erneuert keine Wirkung.

Die historische Clearancezeile wird nicht gelöscht oder umgeschrieben.

## Write-Claim-Revalidierung

Der bestehende Claimadapter verwendet dieselbe `_facts`-Rekonstruktion der
Clearance-Erzeugung innerhalb seiner Write-Transaktion.

Damit wird die aktive Policyrevision unmittelbar vor einem neuen physischen
Write-Claim erneut geprüft.

Eine nach Clearance-Erzeugung deaktivierte oder ersetzte Policy sperrt den
Claim fail-closed.

## Read-only Clearance-Auflösung

Auch die aktuelle persistente Clearance-Auflösung liest die aktive Policy
frisch und vergleicht sie mit der aktuellen gebundenen Decision.

Abweichung oder Abwesenheit liefert den bestehenden detailfreien
Cleanup-Conflict.

Dadurch können Preflight und spätere kontrollierte Ausführung keine stale
Clearance als aktuell gültig rekonstruieren.

## Verlängerung und Ersetzung

Jede neue Policyrevision besitzt eine neue stabile Revision-ID, auch bei
gleicher Dauer.

Deshalb sperrt jede Ersetzung alte `eligible`-Decisions, bis LQ-540 unter der
neuen Policy eine neue Evaluation und Decision bindet.

Eine längere Policy kann somit sofort frühere Eligibility entwerten.

## Deaktivierung

Deaktivierung entfernt den Active-Pointer.

Clearance-Erzeugung, Retry, Auflösung und Claim behandeln diese Abwesenheit
fail-closed.

Keine frühere Policy wird still reaktiviert.

## Historische Fakten

Decision, Operation, Clearance und Attempt bleiben unveränderte Auditfacts.

Der Policywechsel überschreibt keine gebundene historische Revision.

Die Prüfung entscheidet ausschließlich über neue oder fortgesetzte physische
Wirkung.

## Fehlergrenzen

Autoritative Policyabwesenheit oder Revisionabweichung ist eine detailfreie
fachliche Sperre.

Mehrdeutige oder beschädigte Policyprojektion und Infrastrukturfehler bleiben
detailfreie `ManifestHandoffRegistryUnavailable`.

Kein neuer Exceptiontyp entsteht.

## Keine weitere Wirkung

LQ-541 erzeugt keine Policy, Evaluation oder Decision.

Es startet keinen Cleanup und verändert keine Dateien.

Keine Migration, CLI, Route, Entry Point oder Productionverdrahtung wird
ergänzt.

## Bestand

Der Bestand bleibt bei 67 Entry Points, 68 fachlichen Operatormodulen plus
Initialisierer und 42 Migrationen bis Head `20260826_0042`.

## Nächster Slice

LQ-542 ergänzt die explizite persistente Retentionoperation in die bestehende
opt-in Cleanup-Composition, ohne automatische Ausführung oder neue Route.
