# LQ-079 — Research-Job-Start

## Status

- Ein bereits validierter Job und ein bereits aufgelöster Runner können über
  genau eine Anwendungsfunktion gestartet werden.
- Der Job wird vor der synchronen Ausführung registriert.
- Erfolg und neutraler Fehlerzustand bleiben anschließend über LQ-078 lesbar.
- Keine Runner-Factory, HTTP-POST-Route, Queue oder Persistenz.

## Ablauf

```text
validierter Job + aufgelöster Runner
                 ↓
          Job registrieren
                 ↓
       synchron ausführen
          ↙             ↘
    Succeeded          Failed
       + Evidence      + execution_failed
```

Die Registrierung erfolgt zuerst. Dadurch bleibt ein akzeptierter Job auch dann
beobachtbar, wenn die Runner-Ausführung fachlich fehlschlägt. Eine doppelte
`job_id` wird vor dem Runner-Aufruf abgelehnt und überschreibt keinen Lauf.

## Bewusst nicht gebaut

- keine Auflösung von Dataset, Strategie, Risiko- oder Kostenadaptern,
- keine ID-Erzeugung und kein HTTP-Requestmodell,
- keine Queue, Nebenläufigkeit, Cancellation oder Retry,
- keine Datenbank, Authentifizierung, UI, Release oder Deployment.

## Definition of Done

- Registrierung geschieht vor der Ausführung,
- erfolgreiche und fehlgeschlagene Jobs bleiben eindeutig lesbar,
- Duplikate führen zu keiner Runner-Ausführung,
- vorhandener Lifecycle und vorhandene Evidence werden wiederverwendet,
- vollständige Testsuite bleibt grün,
- nächster Schritt kann genau einen Snapshot-zu-Runner-Resolver definieren.
