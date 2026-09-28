# LQ-804 — Detail-limited Engine API Process Status

## Umsetzung

`ManifestHandoffSupervisorEngineApiProcessStatus` besitzt eine geschlossene
Enumphase und einen Lock. Explizite Methoden implementieren ausschließlich die
erlaubten monotonen Übergänge.

`snapshot` kopiert die Phase unter Lock und erzeugt daraus einen frozen,
slots-basierten Wert mit festen Gründen.

`ManifestHandoffSupervisorEngineApiReadinessProbe` akzeptiert ausschließlich die
exakte Statusklasse und projiziert nur ready und Grund auf den bestehenden
frameworkunabhängigen `Readiness`-Typ.

Ein interner Projektionsfehler wird zu nicht-ready mit dem festen
Unavailable-Grund und gibt keine Details weiter.

## Nicht umgesetzt

Der bestehende Prozesseinstieg verändert den Status noch nicht. Es gibt keinen
globalen Singleton, Poller, Cache, Healthserver oder Deploymentanschluss.
