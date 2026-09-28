# LQ-296 — Immutable Local Research Artifact Store

## Ergebnis

LQ-296 implementiert `LocalImmutableResearchArtifactStore` als owner-
kontrollierten lokalen Adapter des bestehenden `ArtifactStore`-Ports.

Der Store erstellt und liest ausschließlich kanonische JSON-Ergebnisse unter
einer engen Research-Schlüsselstruktur. Er führt keine Job-, Claim- oder
Authorityentscheidung aus.

## Vertrauensanker

Der konfigurierte Root muss absolut, bereits vorhanden, ein echtes Verzeichnis,
vom aktuellen Prozess-User besessen und weder gruppen- noch world-writable sein.

Der Adapter erstellt den Root nicht und folgt keinem Root-Symlink. Sein `repr`
enthält keinen Pfad.

## Geschlossene Schlüsselgrammatik

Akzeptiert wird ausschließlich:

`research/<64 lowercase hex>/result.json`

Absolute Pfade, `..`, leere Segmente, freie Dateinamen, andere Präfixe,
Großbuchstaben und nicht exakt 64-stellige Hashsegmente werden abgewiesen.

Der Hashpfad entspricht der in LQ-295 erzeugten Ableitung der internen Job-ID;
die Job-ID selbst erscheint weder im Schlüssel noch im Dateinamen.

## Symlink-sichere Verzeichnisgrenze

Root, Research-Verzeichnis, Hashverzeichnis und Ergebnisdatei werden relativ
zu geöffneten Directory-Deskriptoren und mit `O_NOFOLLOW` aufgelöst.

Zwischenliegende Symlinks, fremde Eigentümer und gruppen- oder world-writable
Verzeichnisse sind technische Nichtverfügbarkeit. Es wird nicht außerhalb des
Roots gelesen oder geschrieben.

Neu erzeugte Verzeichnisse erhalten Modus `0700`.

## Atomares immutable Create

Content muss aus nicht leeren Bytes bestehen und den Medientyp
`application/json` tragen.

Der Store schreibt zunächst eine owner-only Temporärdatei mit `O_EXCL`, Modus
`0600`, vollständigem Write und `fsync`. Anschließend veröffentlicht ein
atomarer Hardlink den endgültigen Namen nur dann, wenn dieser noch fehlt.

Der endgültige Name wird niemals überschrieben, ersetzt oder gekürzt.
Temporärdateien werden auch bei Fehlern entfernt.

Ein exakter Retry mit identischen Bytes liefert dieselbe Referenz. Ein Retry
mit abweichenden Bytes scheitert detailfrei und lässt den vorhandenen Inhalt
unverändert.

## Referenz und Read-Verifikation

`put` berechnet SHA-256 und liefert Schlüssel, Digest, Medientyp und Bytegröße
als bestehende `ArtifactReference`.

`get` akzeptiert nur eine strukturell gültige JSON-Referenz und öffnet nur eine
owner-only reguläre Datei mit Modus `0600` und Linkcount eins.

Jeder Read vergleicht tatsächliche Größe und SHA-256 erneut. Fehlende,
veränderte, hart verlinkte oder anders berechtigte Dateien werden niemals als
gültiges Artifact ausgegeben.

## Fehlergrenze

Pfad-, Berechtigungs-, Symlink-, Race-, I/O-, Hash- und Integritätsfehler werden
als detailfreie `research_artifact_store_unavailable` vereinheitlicht.

Die Exception enthält weder Root, Schlüssel, Pfad, Digest, Content noch
Betriebssystemdetail.

## Nicht enthalten

LQ-296 implementiert keine Verschlüsselung, Remote- oder Object-Storage-
Anbindung, Garbage Collection, Retentionlöschung, Recoveryentscheidung,
Artifactlisting, CLI, Workerloop, Route, Compose- oder Production-Wiring.

Schema und Migration-Head bleiben `20260819_0027`; Bundle und Entry Points
bleiben unverändert.

Die vollständige lokale Suite besteht mit 3350 Tests, 98 erwarteten
PostgreSQL-Skips und 615 bestehenden Warnungen.

## Implementierungsfolge

LQ-297 kann nun die vollständige side-effect-freie Workercomposition aus
persistenter Job-Control, geschlossenem Resolver, lokalem ArtifactStore und
`ProcessOneResearchJob` bereitstellen.

Der langlebige Loop und Runtime-Entry-Point bleiben danach getrennt.
