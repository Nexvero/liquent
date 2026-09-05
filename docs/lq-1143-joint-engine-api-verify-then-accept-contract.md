# LQ-1143 — Joint Engine API Verify-then-Accept Contract

## Ergebnis

Verlangt vollständige Run-Root-Prüfung vor dem atomaren Acceptance-Write.

## Grenze

Fehlgeschlagene Prüfung darf keinen Run verbrauchen; erfolgreicher Write ist terminal.
