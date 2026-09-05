# LQ-679 — Fixed Child Process Composition Contract

## Ergebnis

Writer und Recovery erhalten je einen festen installierbaren Command über eine
gemeinsame profilgeschlossene Processcomposition.

## Eingabegrenze

Der Command akzeptiert ausschließlich die exakte kanonische
Vierzehn-Element-Ankerfolge aus LQ-660.

Es gibt keine freien Argumente, Subcommands, Environmentpfade, Importnamen oder
Authoritywerte.

Profil des Commands und Profil des Ankers müssen identisch sein.

## Feste Pfade

Launchroot ist `/run/liquent/launch`, Control-Directory
`/run/liquent/control`, Source `/run/liquent/source` und Target
`/run/liquent/target`.

Nur Writer verwendet Source. Recovery ruft ausschließlich die Reconciliation
mit Target auf.

## Identität

Der Wrapper leitet Hostowner und Readergruppe aus den Metadaten der festen
Launchdatei ab und bindet sie an aktuellen Wrapper-UID/GID.

Der bestehende numerische Identity-Policy-Typ verlangt getrennten Hostowner und
Wrapperuser sowie identische Reader-/Wrappergruppe.

Der Loader prüft diese Fakten anschließend erneut über no-follow-Deskriptoren.

## Composition

Process-eigen konstruiert werden Ankercodec, Launchloader, direkter
Control-Adapter, Gatewrapper, lokaler Capabilityexecutor und One-shot-
Kindprozess.

UTC-Clock, Monotonic-Clock, Sleep sowie maximale Wait- und Pollgrenze sind fest.

## Capabilityausführung

Writer verwendet ausschließlich die package-lokale atomare Handoffprimitive mit
den festen Containerpfaden.

Recovery verwendet ausschließlich die package-lokale read-only
Reconciliationprimitive und erhält keine Writer- oder Cleanupfähigkeit.

Der Renderer darf intern ausschließlich seinen bereits gehärteten festen
Git-Doppelsnapshot ausführen; der Wrapper selbst besitzt keinen freien
subprocess- oder Commandkanal.

## Exitgrenze

Vollständiges Terminal liefert Exit 0, neutraler Gatekonflikt Exit 3 und jede
technische Unverfügbarkeit Exit 1.

Der Command schreibt keine IDs, Pfade, Digests, Outcomes oder Fehlerdetails auf
stdout oder stderr.
