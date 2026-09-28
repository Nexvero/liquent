# LQ-675 — Direct Child Control Artifact Adapter Contract

## Ergebnis

Der Supervisor-Kindprozess benötigt einen atomaren Adapter für genau die bereits
gemountete Directory `/run/liquent/control`.

Er verwendet dieselbe kanonische Artefakt- und No-replace-Semantik wie der
hostseitige Adapter, aber keine Hostroot- oder Jobresolvergrenze.

## Feste Bindung

Der Adapter wird bei Processcomposition an genau eine absolute Directory und
genau eine `ManifestHandoffSupervisorControlDirectoryId` gebunden.

Publish und Read akzeptieren ausschließlich diese ID.

Ein Request kann keinen Pfad, Dateinamen oder andere Directory wählen.

## Direkte Öffnung

Die gebundene Directory wird direkt mit `O_DIRECTORY` und `O_NOFOLLOW`
geöffnet.

Sie muss ein echtes Verzeichnis sein, dem effektiven Wrapperuser gehören und
exakt Modus 0700 besitzen.

Abweichung wird nicht repariert oder normalisiert.

## Kein Parentbesitz

Der übergeordnete Containerpfad wird nicht als private Jobdirectory behandelt.

Er darf beispielsweise root-owned und 0755 sein; seine Policy erteilt keine
Artefaktfähigkeit.

Nur der erfolgreich validierte Descriptor der gebundenen Direct-Directory wird
für Dateioperationen verwendet.

## Wiederverwendete Semantik

Codec, feste Rollennamen, bounded Reads, Dateiowner/-modus, Single-Link-Prüfung,
temporäres O_EXCL, vollständiger Write, File-fsync, atomarer Hardlink,
Directory-fsync und byteidentischer Retry bleiben unverändert.

Der Direktadapter implementiert keine zweite Publikationslogik.

## Abwesenheit und Fehler

Nur die Abwesenheit des festen Rollenfiles liefert neutral `None`.

Falsche Directory-ID, Symlink, Modus-/Ownerabweichung, beschädigte Bytes oder
I/O-Fehler bleiben detailfreie technische Unverfügbarkeit.

## Keine zusätzliche Macht

Der Adapter besitzt keine Delete-, Cleanup-, Overwrite-, Prozess-, Engine- oder
Authorityoberfläche.
