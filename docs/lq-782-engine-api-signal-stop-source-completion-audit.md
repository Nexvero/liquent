# LQ-782 — Engine API Signal Stop Source Completion Audit

## Ergebnis

LQ-779 bis LQ-782 schließen die explizit besessene SIGTERM-/SIGINT-Stopquelle
ohne globale Import- oder Konstruktionswirkung.

## Geschlossene Eigenschaften

- Installation nur im Main Thread
- vollständige Bindung vorheriger Handler
- minimale lokale boolesche Signalwirkung
- keine Handler-I/O- oder Closewirkung
- Rollback partieller Installation
- umgekehrte vollständige Wiederherstellung
- erneute Installation setzt Stopzustand zurück
- detailfreie Install-/Restorefehler
- kein Signalversand oder Thread

## Offene Blocker

Stopquelle und Owned Process Run müssen noch in eine Install-Run-Finally-Restore-
Operation gebunden werden.

Ein Signal unterbricht ein bereits blockierendes Accept noch nicht. Dafür bleibt
ein eigener kontrollierter Wakeup-/Listener-Shutdown-Vertrag erforderlich.

## Productionstatus

Die Stopquelle ist noch nicht verdrahtet; `production_ready=false` bleibt korrekt.

## Verifikation

- 292 fokussierte Signal-, Process-Run-, Loop-, Accept-, Listener-, Exchange-, Peer-, Gate-, Host- und Migrationsprüfungen bestehen.
- 5.647 vollständige Nicht-PostgreSQL-Tests bestehen; 108 werden erwartungsgemäß übersprungen.
- Deprecation-Warnungen werden in der vollständigen Suite als Fehler behandelt.
- Die abschließende Diffprüfung bleibt die Whitespace- und Scopegrenze.

## Nächster Strang

Als Nächstes ist Install-Run-Finally-Restore für den endlichen Proxyprozess
umzusetzen.
