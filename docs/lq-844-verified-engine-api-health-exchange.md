# LQ-844 — Verified Engine API Health Exchange

## Umsetzung

`VerifiedManifestHandoffSupervisorEngineApiHealthExchange` akzeptiert exakt die
konkrete Linux-Peerpolicy, das geschlossene Healthprotokoll und optional exakt das
bounded Health-Stream-I/O.

`exchange` autorisiert den Stream, prüft Nachweistyp, Objektidentität und
Deskriptor, liest einen Request, erzeugt eine Response und prüft den Deskriptor
vor dem vollständigen Write erneut.

Eine leere oder fremd typisierte Protocolresponse scheitert vor dem Write.

Alle unerwarteten technischen Fehler werden an der bestehenden detailfreien
Grenze vereinheitlicht.

## Nicht umgesetzt

Keine Socketkonfiguration, Closeownership, Listener-, Accept-, Serve-Loop- oder
Healthdeployment-Composition.
