# LQ-586 — Owner-controlled Supervisor Control-directory Retirement Operator

## Ergebnis

LQ-586 implementiert den festen LQ-585-One-Shot-Entry-Point
`liquent-supervisor-control-directory-retire`.

## Eingabegrenze

Der Parser akzeptiert ausschließlich `--database-url-file`,
`--backend-instance-id-file`, `--request` und `--result-file`.

Private Lese- und atomare Schreibregeln werden aus dem bestehenden initialen
Bootstrapoperator wiederverwendet. Der Requestparser weist zusätzliche,
fehlende, doppelte, leere oder nicht-stringförmige Felder detailfrei ab.

## Composition

Nach erfolgreicher Readinessprüfung entstehen auf derselben Engine:

- `DatabaseManifestHandoffSupervisorControlDirectories`;
- `DatabaseManifestHandoffSupervisorJournal`, gebunden an die private
  Backendinstanz-ID;
- `PersistentManifestHandoffSupervisorControlDirectoryRetirement` aus LQ-490.

Der Factoryaufbau führt außer der ausdrücklichen Readinessprüfung keine
fachliche Wirkung aus.

## Ergebnishandoff

Erfolg validiert exakten Resultattyp und Directorybindung. Die persistente
Retirementzeit wird als UTC-ISO-Wert mit `Z` ausgegeben.

Die private Ergebnisdatei wird nur bei Erfolg mit exklusiver temporärer Datei,
`fsync` und atomarem Replace erzeugt. Stdout enthält ausschließlich
`{"outcome":"applied"}`.

Neutraler oder konfliktbehafteter Bestand erzeugt keine Ergebnisdatei und
liefert `{"outcome":"rejected"}`. Technische Fehler liefern nur
`{"error":"operator_unavailable"}` auf stderr.

Die Engine wird in jedem Pfad im `finally` freigegeben.

## SQLite-End-to-End-Nachweis

Ein migriertes SQLite-Szenario mit Active-Directory und vollständig terminalem
Writerjournal wird retired. Der Retry liefert dieselbe Directory-ID,
Handle-ID und persistente Retirementzeit.

Unbekannt, Reserved und Active ohne Terminalfact bleiben unverändert und
erzeugen kein Resultat. Der echte CLI-Pfad schreibt eine private atomare
Ergebnisdatei.

## Inventar

Der kontrollierte Bestand steigt auf 69 Console Entry Points und 70
Operator-Pythondateien einschließlich Paketinitialisierer. Migrationen bleiben
bei 42 und Head `20260826_0042`.

Operational-Bundle und aktive Inventargates werden fail-closed auf denselben
Bestand synchronisiert. LQ-585 wird required Contract des Bundles.

## Abgrenzung

LQ-586 ergänzt keine Migration, Tabelle, Domain-, Port- oder
Anwendungssignatur, Route, automatische Retention- oder Cleanupwirkung.

LQ-587 belegt denselben Übergang auf echtem PostgreSQL.
