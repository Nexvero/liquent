# LQ-1171 — Joint Engine API Single-open Registry Contract

## Ergebnis

Verlangt genau einen Arbeitsdescriptor der Acceptance-Wurzel je
Inventarentscheidung. Eine getrennte finale No-follow-Öffnung revalidiert nur
die sichtbare Rootidentität und wird nicht für Markerreads verwendet.

## Grenze

Markerreads über den final erneut aufgelösten Rootpfad sind ausgeschlossen.
