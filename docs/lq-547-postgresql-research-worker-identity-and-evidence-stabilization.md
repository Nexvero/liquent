# LQ-547 — PostgreSQL Research Worker Identity and Evidence Stabilization

## Ergebnis

LQ-547 schließt den in LQ-545 und LQ-546 getrennt ausgewiesenen
LQ-302-Mehrprozessbefund.

Der lokale allowlist-basierte Researchresolver bindet Runnerergebnisse nun an
die bereits akzeptierte persistente Experiment-ID. Die Erfolgsfinalisierung
verwendet dieselbe JSON-sichere Evidence-Projektion wie das unveränderliche
Ergebnisartefakt.

## Experiment-ID-Bindung

`ExperimentSnapshot.experiment_id` ist die vom Control Plane akzeptierte und
persistierte Identität des Researchlaufs.

Der darunterliegende historische `BacktestRunner` erzeugt zusätzlich eine
deterministische Parameterhash-ID. Diese interne Runner-ID war nicht identisch
mit der Snapshot-ID und führte deshalb beim Worker korrekt zu einer
detailfreien Execution-Failure.

Der `LocalCsvMidBreakoutV0Resolver` liefert nun einen kleinen geschlossenen
Executionwrapper. Er führt den bestehenden Runner genau einmal aus und ersetzt
im unveränderlichen `BacktestResult` ausschließlich `experiment_id` durch die
Snapshot-ID.

Strategie, Datasetfingerprint, Parameter, Trades, Metriken, Safetyflags und
alle Runnerentscheidungen bleiben unverändert.

Die nachgelagerte Prüfung in `ProcessOneResearchJob` und die erneute Prüfung in
`DatabaseResearchJobs.finalize_success` bleiben vollständig erhalten. Ein
anderer Resolver oder ein abweichendes Ergebnis wird weiterhin fail-closed
abgelehnt.

## JSON-sichere Evidence

Ein erfolgreicher Backtest ohne Verlusttrade kann `profit_factor = Infinity`
erzeugen. Das Artefakt projizierte nicht-endliche Metriken bereits kanonisch zu
JSON `null`, während die Datenbankfinalisierung noch das rohe Summary mit
`allow_nan=False` serialisierte.

Die persistente Erfolgsfinalisierung verwendet nun ebenfalls
`evidence_document(summary)`.

Damit speichern Artefakt und Datenbank dieselbe JSON-sichere fachliche
Projektion. `NaN`, positive und negative Unendlichkeit werden nicht als
nichtstandardkonforme JSON-Zahlen persistiert.

Die in-memory `BacktestExperimentSummary` bleibt unverändert und der Store
akzeptiert weiterhin nur den geschlossenen Summarytyp und das validierte
Artefaktbinding.

## Mehrprozesssemantik

Der PostgreSQL-Test startet weiterhin zwei unabhängige Prozesse mit getrennten
Engines gegen denselben queued Job.

`FOR UPDATE SKIP LOCKED` bindet genau einen Claim. Genau ein Prozess liefert
`succeeded`, der andere `idle`.

Es entsteht genau ein Claim, ein terminales Outcome und ein unveränderliches
Artefakt mit geprüftem SHA-256.

Es wurde kein Retry, Prozesslock oder testseitiger Allowpfad ergänzt.

## Verifikation

Die Resolver-, Worker- und lokale Application-Grenze bestehen mit elf
fokussierten normalen Tests.

Der echte LQ-302-Zwei-Prozess-Test bestand dreimal unabhängig.

Die vollständige PostgreSQL-Integrationssuite besteht mit 105 Tests.

Die vollständige normale Suite besteht mit 5023 Tests und einem erwarteten
Skip; 105 PostgreSQL-markierte Tests sind dort gezielt abgewählt.

## Abgrenzung

LQ-547 ergänzt keine Tabelle, Migration, Portsignatur, Route, CLI, Entry Point,
Workerloop-, Lease-, Claim- oder Authorityregel.

Es gibt keine Netzwerk-, Live-, Paper-Trading-, Commit-, Push-, Deployment-
oder automatische Ausführungswirkung.

## Nächster Slice

LQ-548 führt den abschließenden vollständig grünen Build-, Inventar-,
Migration- und Diffaudit über den stabilisierten Gesamtbestand aus.
