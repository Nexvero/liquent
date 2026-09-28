# LQ-1156 — Joint Engine API One-shot Acceptance Precheck

## Ergebnis

Erweitert Verify-then-Accept um read-only Vorprüfung und behält O_EXCL als finales Race-Gate.

## Grenze

Der Precheck ist keine Ersatzentscheidung und kann Parallelität nicht allein serialisieren.
