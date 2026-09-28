# LQ-539 — Authoritative Persistent Supervisor Cleanup Retention Evaluation

## Ergebnis

LQ-539 implementiert die autoritative read-only Retention-Evaluation aus der
jeweils aktuell persistent aufgelösten Policy.

Die Evaluation besitzt keine Persistenz- oder Cleanupwirkung.

## Exakte Eingaben

Die Grenze akzeptiert ausschließlich den geschlossenen Evaluationsrequest und
einen vollständig rekonstruierten `Retired`-Wert.

Request- und Retired-Directory-ID müssen exakt übereinstimmen.

Abweichung liefert neutral `None` und keine Policyentscheidung.

## Aktuelle Policy

Jeder Aufruf löst die aktive Policy genau einmal über den LQ-533-Lookup auf.

Fehlt eine aktive Policy, liefert die Evaluation neutral `None`.

Es gibt keinen Cache, Fallback und keine Defaultdauer.

Policydeaktivierung oder -ersetzung wirkt auf jede spätere Evaluation.

## Vertrauenswürdige Clock

Die Clock wird erst nach erfolgreicher aktueller Policyauflösung gelesen.

Sie muss aware UTC sein und darf weder vor Retirement noch vor
Policyaktivierung liegen.

Caller können keinen Evaluationszeitpunkt übergeben.

## Geschlossene Schwelle

Vor `retired_at + minimum_retention` lautet die Disposition `retain`.

Exakt ab der Schwelle lautet sie `eligible`.

Die Addition verwendet ausschließlich die positive persistierte Policydauer.

Dateizeit, mtime, Größe, freier Speicher und lokale Defaults spielen keine
Rolle.

## Vollständige Bindung

Das Ergebnis bindet Request, exakten Retired-Wert, geschlossene Datenklasse,
tatsächlich gelesene Policyrevision, Disposition und Evaluationszeit.

`eligible` ist keine Clearance oder Dateisystemauthority.

`retain` ist ein erfolgreicher autoritativer Entscheid und kein Fehler.

## Fehlergrenze

Policyabwesenheit und Zielabweichung bleiben neutral.

Beschädigte Werte, regressierende oder nicht-UTC Clock und technische
Lookupfehler bleiben detailfreie `ManifestHandoffRegistryUnavailable`.

Kein neuer Exceptiontyp entsteht.

## Bewusst nicht enthalten

Keine Directoryauflösung, Decision-ID, Operationbindung oder
Decisionpersistenz.

Keine Clearance, Cleanup-, Datei-, Operator-, Route- oder Productionwirkung.

Keine Migration, Port- oder Domainsignaturänderung.

## Bestand

Der Bestand bleibt bei 67 Entry Points, 68 fachlichen Operatormodulen plus
Initialisierer und 42 Migrationen bis Head `20260826_0042`.

## Nächster Slice

LQ-540 komponiert Directoryauflösung, aktuelle Policyevaluation, interne
Decision-ID und atomaren persistenten Operationstore zu genau einer
Retentionoperation.
