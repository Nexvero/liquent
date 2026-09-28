# LQ-692 — Exclusive Supervisor Candidate Process Composition

## Umsetzung

`compose_manifest_handoff_supervisor_candidate_process` materialisiert den
vollständigen LQ-691-Graphen aus der atomaren Settingsgruppe.

## Parentpfad

Journal, Runtime und Gates teilen dieselbe extern besessene Datenbank-Engine und
dieselbe Clock.

Control-Directory-Registry, sicherer Resolver und atomare Artefakte teilen die
eine konfigurierte Hostwurzel.

Der Docker-Client erhält ausschließlich:

- den konfigurierten Socket
- den sicheren Resolver
- die zwei festen Wrappercommands
- die validierte numerische Identitypolicy

## Childgrenze

Die bereits festen Child-Primitiven werden ohne I/O an ihre unveränderlichen
Containerpfade und bounded Waitpolicy gebunden.

Nur das Childobjekt erhält den Capabilityexecutor; der Parentpfad erhält ihn
nicht.

## Fehlerbehandlung

Scheitert Composition nach Clienterzeugung, wird genau dieser Client geschlossen.

Close-Fehler verdecken keine ursprüngliche Compositionunverfügbarkeit und geben
keine privaten Details aus.

## Nicht aktiviert

Entrypoint, Appfactory, Health, Lifespan und Compose wählen das Prozessobjekt
noch nicht aus.
