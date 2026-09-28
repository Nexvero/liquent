# LQ-685 — Exclusive Supervisor Production Selection Decision

## Entscheidung

Die nächste Implementierung darf Production nur in einer atomaren Folge öffnen.

Die Aktivierung wird nicht über mehrere unabhängig deploybare Teilschalter
verteilt.

## Erforderliche Implementierungsfolge

1. Ein geschlossener Settingsvertrag bindet Auswahl, absoluten Socketpfad,
   absolute Control-Wurzel und feste nichtprivilegierte Wrapperidentität.
2. Eine process-eigene Composition erzeugt persistente Adapter, Resolver,
   Docker-Client und ausschließlich den Kandidatengraphen.
3. Die Appfactory übernimmt Graph, Healthbeitrag und Close-Callback gemeinsam;
   partielle Übergabe scheitert beim Aufbau.
4. Der Lifecycle markiert stopping vor genau einem Client-Close.
5. Compose liefert Socket und Hostwurzel nur an den ausgewählten Prozess und
   bindet sie mit minimal erforderlichen Rechten.
6. End-to-End-Evidenz belegt Start, Ready, Writer, Recovery, Terminal,
   not-ready und Shutdown ohne Parent-Capability-Fallback.

## Aktivierungsregel

`production_ready=true` darf erst nach vollständiger Umsetzung und Evidenz
aller sechs Punkte eingeführt werden.

Bis dahin bleibt der bestehende konstante Wert `false` korrekt.

## Verbotene Zwischenzustände

- Settings ohne Composition
- Socketmount ohne exklusive Graphauswahl
- Kandidat neben Parent-Executorgraph
- Health ohne Supervisorbeitrag
- Client ohne eindeutigen Lifecyclebesitzer
- Readiness trotz fehlender Hostfähigkeit
- Shutdown, der neue fachliche Wirkung ausführt

## Unveränderte Grenzen

Dieser Slice setzt keinen der sechs Schritte um und trifft keine konkrete
Socket-, UID-, GID-, Pfad-, Compose- oder Settingswertentscheidung.
