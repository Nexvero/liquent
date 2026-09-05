# LQ-540 — Controlled Persistent Supervisor Cleanup Retention Operation

## Ergebnis

LQ-540 komponiert aktuelle Directoryauflösung, autoritative Policyevaluation,
interne Decision-ID und atomaren persistenten Operationstore zu genau einer
Retentionoperation.

Die Operation erzeugt keine Clearance und keine physische Cleanupwirkung.

## Minimaler Request

Die Composition akzeptiert ausschließlich den bestehenden geschlossenen
Request aus Operation-ID und Directory-ID.

Sie akzeptiert keine Disposition, Policyrevision, Dauer, Retired-Fakten,
Decision-ID, Clock oder Authoritybehauptung.

## Retry vor jeder neuen Wirkung

Die Operation-ID wird zuerst über den neuen read-only Store-Lookup aufgelöst.

Ein vorhandener identisch an dieselbe Directory-ID gebundener Vorgang gibt das
historische vollständige Ergebnis zurück.

Dabei werden weder Directory noch aktuelle Policy, Clock oder Generator erneut
gelesen.

Dieselbe Operation-ID mit anderer Directorybindung liefert den bestehenden
detailfreien Operation-Conflict.

## Concurrent First Writer

Zwischen initialem Lookup und atomarem Bind kann ein paralleler identischer
Vorgang zuerst committen.

Der Store gibt dann den bereits persistierten First-Writer zurück, sofern die
Operation-ID an dieselbe Directory-ID gebunden ist.

Abweichende Evaluationszeit oder intern erzeugte Decision-ID des verlorenen
Racers erzeugen keine zweite Decision und keinen falschen Retry-Conflict.

Die persistierte Operation-/Directory-Bindung bleibt maßgeblich.

## Aktuelle Directoryauflösung

Nur bei bislang unbekannter Operation wird die Directory-ID aktuell aus dem
System of Record gelesen.

Nur ein vollständig rekonstruierter `Retired`-Wert wird evaluiert.

Unbekannte, Reserved- oder Active-Zustände liefern neutral `None`.

Der Caller kann Retired-, Handle-, Leaf- oder Zeitfakten nicht liefern.

## Autoritative Evaluation

Die LQ-539-Grenze löst die aktive Policy frisch auf und entscheidet `retain`
oder `eligible`.

Policyabwesenheit liefert neutral keine Operation.

Die Composition verändert die Evaluation nicht und ersetzt ihren Zeitpunkt
nicht durch eine zweite Clock.

## Interne Decision-ID

Erst nach erfolgreicher Evaluation wird genau eine Decision-ID intern erzeugt.

Der Generator muss den geschlossenen Decision-ID-Typ liefern.

Caller können keine Decision-ID wählen oder Kollisionen als Retry umdeuten.

## Atomare Bindung

Evaluation und interne Decision-ID werden in den bestehenden LQ-529-Command
gebunden.

Der Store prüft den aktuellen exakten Retired-Wert erneut und schreibt Decision
und Operation in einer Transaktion.

Eine neue Decision ist dadurch niemals ohne durable Operationbindung sichtbar.

## Read-only Operation-Lookup

Der bestehende Operationstore-Port erhält genau eine Lookupmethode nach
typisierter Operation-ID.

Der Lookup liefert das vollständig rekonstruierte Bound-Resultat oder neutral
`None`.

Er besitzt keine Liste, Suche, Mutation oder Discovery.

Beschädigte Operation-, Decision- oder Directorybindungen bleiben technische
Nichtverfügbarkeit.

## Geschlossene Ergebnisse

Erfolg liefert ausschließlich den bestehenden vollständigen Bound-Domainwert.

Neutrale Directory- oder Policyabwesenheit liefert `None`.

Divergente Operation-ID-Wiederverwendung liefert den feldlosen bestehenden
Operation-Conflict.

Technische Fehler bleiben detailfreie `ManifestHandoffRegistryUnavailable`.

## Keine Folgeaktion

`eligible` startet keine Clearance, keinen Attempt und keine Dateiwirkung.

`retain` bleibt ebenfalls eine erfolgreich persistierte Decision.

Die Composition ruft keinen Operator, Worker oder Scheduler auf.

## Bestand

Keine Migration und kein Entry Point werden ergänzt.

Der Bestand bleibt bei 67 Entry Points, 68 fachlichen Operatormodulen plus
Initialisierer und 42 Migrationen bis Head `20260826_0042`.

## Nächster Slice

LQ-541 bindet die aktuelle aktive Policyrevision zusätzlich an die persistente
Cleanup-Clearanceauflösung, damit ersetzte oder deaktivierte Policyrevisionen
eine spätere Clearance fail-closed sperren.
