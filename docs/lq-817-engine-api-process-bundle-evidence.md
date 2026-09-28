# LQ-817 — Engine API Process Bundle Evidence

## Identitätsevidenz

Tests belegen exakte Run-, Status- und Probetypen sowie identische Statusobjekte
im inneren Run, Bundle und Probe.

Gemischte Komponenten aus zwei gültigen Bundles und freie Fremdobjekte scheitern
fail-closed.

## Inertheit

Nach Composition bleibt der Status `initial` und die Probe nicht-ready. Host-,
Environment- und Runwirkungen werden im Test verboten.

## Kompatibilität

Der bisherige Composer ruft genau einmal den Bundlecomposer auf und gibt exakt
dessen Runinstanz zurück.

## Oberflächenevidenz

Das Bundle ist unveränderlich, detailfrei repräsentiert und akzeptiert nur den
exakten geschlossenen Settingswert.
