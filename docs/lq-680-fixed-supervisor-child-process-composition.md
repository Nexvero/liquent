# LQ-680 — Fixed Supervisor Child Process Composition

## Ergebnis

Die feste Processcomposition und der konkrete lokale Child-Capabilityexecutor
sind implementiert.

## Capabilityexecutor

`LocalManifestHandoffSupervisorChildCapabilityExecutor` akzeptiert
ausschließlich typisierte, bereits freigegebene Writer- oder Recoveryexecution.

Writerergebnisse werden in die bestehenden fünf Writerkinds übersetzt.
Pre-bind-Unverfügbarkeit wird terminal als `unavailable`, möglicher
Post-bind-Unknown als `outcome_unknown` bewahrt.

Recoveryergebnisse werden in die bestehenden sechs Recoverykinds übersetzt;
technisch unklare Beobachtung bleibt `outcome_unknown`.

Fakten, Dateiname, Handle, Claim, Owner und UTC-Endzeit werden durch die
bestehenden Domainkonstruktoren erneut geprüft.

## Processcomposition

Der Ankercodec läuft vor jeder Dateiwirkung und sperrt Cross-Profile-Aufrufe.

Danach werden der exakt gebundene Loader, Direct-Control-Adapter, Gatewrapper,
Capabilityexecutor und One-shot-Prozess konstruiert.

Writer und Recovery teilen keine dynamische Profilauswahl nach dem Decode.

## Commands

`liquent-supervisor-writer-wrapper` ruft ausschließlich `writer_main` auf.

`liquent-supervisor-recovery-wrapper` ruft ausschließlich `recovery_main` auf.

Beide sind reguläre Wheel-Entrypoints ohne Shellwrapper.

## Unveränderte Grenzen

Keine Settings-, Appfactory-, Compose-, Engine-Client- oder Productionauswahl
wurde ergänzt.
