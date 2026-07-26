# LQ-072 — Research Identity and Lifecycle

## Status

- Vier semantische ID-Typen für Workspace, Strategy Version, Experiment und
  Evidence ergänzt.
- Research-Job-Zustände und direkte Übergänge explizit implementiert.
- Terminale Zustände können nicht erneut geöffnet oder überschrieben werden.
- Keine ID-Generierung, Persistenz, Zeitlogik oder generische State Machine
  eingeführt.

## Minimaler Vertrag

Die ID-Typen bleiben zur Laufzeit einfache Strings. Sie verhindern auf
Typgrenzen, dass fachlich verschiedene Identitäten versehentlich gleich
behandelt werden, ohne ein eigenes ID-Framework einzuführen. Format und
Generierung bleiben Aufgabe der bereits vorhandenen `IdentifierFactory`-Grenze
und eines späteren konkreten Workflows.

Der Job-Lifecycle erlaubt nur:

```text
Draft → Ready → Queued → Running → Succeeded
  │       │        ├────────────→ Failed
  │       │        └────────────→ Cancelled
  │       ├─────────────────────→ Invalidated
  │       └─────────────────────→ Discarded
  └─────────────────────────────→ Discarded
```

Ein ungültiger Übergang wirft einen stabilen Fehler und verändert keinen
Zustand. Ein Retry wird später als neues Experiment modelliert; terminale
Zustände besitzen deshalb keine ausgehenden Übergänge.

## Bewusst nicht gebaut

- keine abstrakte Entity-Basisklasse,
- kein Repository oder Unit-of-Work,
- keine Events, Hooks oder Observer,
- keine UUID-/ULID-Bibliothek,
- keine Datenbanktabellen oder Migration,
- keine HTTP-Endpunkte oder Hintergrundjobs.

## Definition of Done

- benötigte Slice-1-Identitäten sind semantisch unterscheidbar,
- Happy Path, Fehler und Abbruch sind als direkte Übergänge testbar,
- ungültige Sprünge und Wiederöffnung terminaler Zustände scheitern fail-closed,
- die Implementierung bleibt klein und frei von neuen Abhängigkeiten,
- nächster Schritt ist LQ-073: minimale Anwendungsgrenze zum BacktestRunner.
