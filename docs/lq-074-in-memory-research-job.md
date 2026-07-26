# LQ-074 — In-Memory Research Job

## Status

- Ein bereits validierter Research-Job ist synchron im Speicher ausführbar.
- Der Job nutzt die vorhandene LQ-073-Anwendungsgrenze und das vorhandene
  Evidence-Reporting.
- Erfolg speichert die Evidence am Job; Fehler enden neutral mit
  `execution_failed`.
- Terminale Jobs können nicht erneut ausgeführt werden.
- Keine Datenbank, Queue, Worker, API oder neue Abhängigkeit eingeführt.

## Ablauf

```text
Ready → Queued → Running → Succeeded + Evidence
                     └───→ Failed + execution_failed
```

Der Job beginnt bewusst in `Ready`: Dataset-, Strategie- und Parameterprüfung
gehören vor diese Grenze und werden nicht als halbfertige Validierungsengine in
den Ausführungsjob eingebaut. Die synchrone Ausführung beweist zuerst den
Produktfluss, bevor ein asynchroner Betriebsbedarf angenommen wird.

Interne Exceptions werden nicht als öffentlicher Fehlertext gespeichert. Der
erste Slice besitzt genau einen neutralen Fehlercode. Eine spätere, konkrete
UX-Anforderung kann die Fehlercodes gezielt erweitern.

## Bewusst nicht gebaut

- keine Jobliste oder In-Memory-Repository-Abstraktion,
- keine Queue, Parallelität, Progress-Anzeige oder Cancellation,
- kein Retry desselben Jobs,
- keine Datenbanktransaktion oder Migration,
- kein HTTP-Endpunkt,
- keine Broker-, Paper- oder Live-Ausführung.

## Definition of Done

- ein validierter Job durchläuft die erlaubten Statusübergänge,
- ein erfolgreicher No-Signal-Lauf liefert gültige Evidence,
- ein Runnerfehler endet terminal und ohne interne Detailweitergabe,
- derselbe Job kann nicht erneut ausgeführt werden,
- vollständige Testsuite bleibt grün,
- nächster Schritt ist LQ-075: minimaler HTTP-Vertrag für diesen bewiesenen Flow.
