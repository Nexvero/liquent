# LQ-080 — Research-Runner-Resolver

## Status

- Eine kleine Ein-Methoden-Schnittstelle löst einen validierten
  `ExperimentSnapshot` in den bestehenden `BacktestExecution`-Port auf.
- Nach erfolgreicher Auflösung wird ausschließlich der vorhandene
  LQ-079-Startpfad verwendet.
- Eine fehlgeschlagene Auflösung registriert keinen halbfertigen Job.
- Keine konkrete DataSource-, Strategy-, Risk- oder Cost-Factory gebaut.

## Ablauf

```text
ExperimentSnapshot
        ↓ resolve
BacktestExecution
        ↓ LQ-079
registrierter Research-Job
        ↓
Succeeded oder Failed
```

Der Resolver konstruiert nur den ausführbaren Runner und startet ihn nicht.
Seine konkrete Implementierung wird erst zusammen mit einer bewusst
unterstützten Dataset- und Strategiekombination ergänzt. Damit bleibt die
Anwendungsgrenze testbar, ohne ein generisches Plugin- oder Factory-System
vorwegzunehmen.

## Fehlergrenze

Kann der Snapshot nicht aufgelöst werden, schlägt der Aufruf vor der
Jobregistrierung fehl. Ein HTTP-Adapter kann diesen Fall später neutral als
fachlich nicht auflösbaren Input darstellen. Interne Pfade oder Exceptions
gehören nicht in die öffentliche Antwort.

## Bewusst nicht gebaut

- kein Resolver-Register und keine dynamische Plugin-Suche,
- keine konkrete CSV-, synthetische oder externe Datenauflösung,
- keine automatische Strategieauswahl oder Parameterkonvertierung,
- kein HTTP-POST, keine Authentifizierung, Datenbank oder Queue,
- kein Release oder Deployment.

## Definition of Done

- der Resolver erhält exakt den gebundenen Snapshot,
- erfolgreiche Auflösung verwendet den vorhandenen Startpfad,
- fehlgeschlagene Auflösung hinterlässt keinen Job,
- keine zweite Runner- oder Evidence-Abstraktion entsteht,
- vollständige Testsuite bleibt grün,
- nächster Schritt ist ein einzelner explizit unterstützter lokaler Resolver.
