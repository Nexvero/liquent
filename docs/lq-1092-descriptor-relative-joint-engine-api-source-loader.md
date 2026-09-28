# LQ-1092 — Descriptor-relative Joint Engine API Source Loader

## Ergebnis

Öffnet die Wurzel einmal und liest jedes Kind mit O_NOFOLLOW relativ zu demselben Deskriptor.

## Grenze

Wurzelidentität und vollständiger Namenssatz werden vor und nach den Reads geprüft.
