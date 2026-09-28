# LQ-813 — Engine API Signal Status Evidence

## Erfolgsevidenz

Während Signal-Restore ist der Status noch `stopping`. Erst nach erfolgreicher
Rückgabe wird `stopped` sichtbar.

## Fehlerevidenz

Installfehler führt aus `initial` nach `failed`. Restorefehler führt aus
`stopping` nach `failed`. Ein innerlich bereits fehlgeschlagener Run bleibt nach
erfolgreichem Restore terminal `failed`.

Fremde boolesche Formen und doppelte Finalisierung scheitern fail-closed.
Nicht-deferred direkte Process Runs lehnen äußere Finalisierung ab.

## Kompatibilitätsevidenz

Die bestehende direkte Process-Run- und isolierte Signal-Run-Suite bleibt
unverändert grün. Es wird kein echtes Signal installiert.
