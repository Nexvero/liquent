# LQ-314 — Runtime Inspection Executable

## Ergebnis

LQ-314 implementiert den installierbaren Command `liquent-runtime-inspect` für
die drei LQ-313-Phasen `entrypoint`, `input_ownership` und `data_read_only`.

Das Executable arbeitet ausschließlich mit festen Containerpfaden und lokalen
read-only Beobachtungen. Es startet keinen Worker, öffnet kein Netzwerk, liest
keine Inputinhalte und führt keine Schreibprobe aus.

## CLI

Der Command akzeptiert genau `--phase` mit einem der drei Namen. Es gibt keine
Pfad-, User-, Mount-, Package-, Output- oder Policyargumente und keinen
Environment-/PATH-Fallback.

Erfolg oder eindeutiger Mismatch schreibt genau ein kanonisches neutrales JSON
und liefert Exitcode null. Technische Nichtverfügbarkeit oder CLI-Fehler liefert
Exitcode zwei ohne stdout oder stderr.

## Entry-Point-Prüfung

Die installierte `liquent`-Distribution muss genau einen Console Script Entry
`liquent-research-worker` mit Ziel
`liquent_platform.operators.research_worker:main` enthalten.

Das feste Script unter `/opt/liquent/venv/bin` wird mit No-follow geöffnet und
muss regulär, Linkcount eins, nicht group/world-writable und für den
Runtimeuser ausführbar sein.

Das Zielmodul wird nicht importiert und der Worker nicht gestartet.

## Inputownership

Config und Worker-ID werden an den festen Zielen mit `O_NOFOLLOW` geöffnet.
Geprüft werden ausschließlich Descriptor-Metadaten: regulär, aktueller Owner,
Linkcount eins und 0400 oder 0600.

Die Bytes werden nie gelesen oder dekodiert. Deshalb können Tests bewusst
ungültige private Inhalte verwenden und trotzdem die reine Metadatengrenze
beweisen.

## Daten-read-only

Der feste Research-Datenroot wird als echtes No-follow-Verzeichnis geöffnet.
`/proc/self/mountinfo` ist auf ein MiB begrenzt und muss genau einen passenden
Mountpoint mit `ro` ohne `rw` enthalten.

Der Root muss für den Runtimeuser nicht schreibbar sein und mindestens einen
vorhandenen Eintrag enthalten. Reguläre vorhandene Dateien dürfen ebenfalls
nicht schreibbar sein.

Es gibt keinen Create-, Open-for-write-, Rename-, Link-, Unlink-, Chmod- oder
Probe-Write-Aufruf. Tests beweisen, dass Inhalt und Verzeichnisbestand
unverändert bleiben.

Escaped Mountpoint-Leerzeichen werden ausschließlich über die standardisierte
octale Mountinfo-Darstellung dekodiert. Fehlende oder doppelte Mountpoints sind
technisch unavailable.

## Detailgrenze

Output enthält ausschließlich Schema-Version, Phase und ein Boolean-Faktum.
Paket-, Script-, UID-, Mode-, Inode-, Mount-, Pfad- und Fehlerdetails werden
nicht ausgegeben.

Alle technischen Fehler werden als `runtime_inspect_unavailable`
vereinheitlicht und von der CLI still in Exitcode zwei übersetzt.

## Bundle

Der neue Entry Point und das Modul erhöhen die Gates auf 24 Entry Points und 27
Operatormodule. Migration-Head und Migrationszahl bleiben `20260819_0027` und
27.

## Nichtziele

Keine Docker-Run-Composition, Secretinspection, Artifactfähigkeit,
Datenbank-/Job-/Revocation-/Log-/SIGTERM-Phase oder reale Stagingausführung wird
implementiert.

Es gibt keine Schema-, SQL-, Migration-, Port-, Domainmodell- oder
Composeänderung.

## Nächster Slice

LQ-315 sollte die gehärtete rungebundene Docker-Run-Composition ergänzen, die
dieses feste Executable ohne Secrets, Netzwerk, Shell oder beschreibbares
Artifactvolume für genau eine der drei Phasen startet.
