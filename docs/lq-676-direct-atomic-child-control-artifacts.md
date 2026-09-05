# LQ-676 — Direct Atomic Child Control Artifacts

## Ergebnis

`DirectAtomicLocalManifestHandoffSupervisorControlArtifacts` erweitert den
bestehenden atomaren Adapter ausschließlich um direkte Child-Directory-Auflösung.

## Konstruktion

Konstruktion verlangt absoluten Direct-Pfad, exakten bestehenden
Control-Directory-ID-Typ und den kanonischen Codec.

Pfad und ID bleiben aus Repräsentationen ausgeschlossen.

## Wiederverwendung

Publish, Read, kanonisches Decode, Konfliktklassifikation, temporäre
Dateibereinigung, fsync und Published-Fakten werden unverändert vom bestehenden
Adapter geerbt.

Dadurch gibt es weiterhin nur eine Implementierung der kritischen atomaren
Dateisequenz.

## Child-spezifische Auflösung

`_directory` akzeptiert nur die konstruktiv gebundene ID und gibt nur die
gebundene Direct-Directory zurück.

`_open_directory` öffnet genau diesen absoluten Pfad mit no-follow und wendet
die bestehende private Directoryprüfung direkt auf seinen Descriptor an.

Der Parentdescriptor wird weder geöffnet noch validiert.

## Unveränderte Grenzen

Der Slice komponiert noch keinen Gatewrapper oder Kindprozess und registriert
keinen Command.

Settings, Appfactory, Compose und Production bleiben unverändert.
