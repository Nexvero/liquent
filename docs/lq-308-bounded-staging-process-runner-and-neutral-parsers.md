# LQ-308 — Bounded Staging Process Runner and Neutral Parsers

## Ergebnis

LQ-308 implementiert die lokale Prozessgrundlage des LQ-307-Adapters.

`LocalBoundedProcessRunner` führt genau eine explizite argv-Liste ohne Shell
aus, übergibt eine vollständig vom Aufrufer gebaute Umgebung und erfasst stdout
und stderr getrennt sowie begrenzt.

`reduce_phase_output` reduziert erfolgreichen Prozessoutput über eine totale
geschlossene Abbildung aller 29 Phasen auf genau ein neutrales Boolean-Faktum.

Der Slice enthält noch keine Docker-/Compose-Kommandotabelle und löst deshalb
keine Stagingoperation aus.

## Prozessgrenze

Das Executable muss ein absoluter existierender Dateipfad sein. argv ist ein
nicht leeres Tupel gültiger Strings ohne NUL.

Das Arbeitsverzeichnis ist explizit, absolut und vorhanden. Die Umgebung wird
als neues Dictionary an `Popen` übergeben; es gibt kein `shell=True`, stdin
zeigt auf DEVNULL und die Prozessgruppe ist neu.

Damit erbt der Kindprozess ausschließlich Werte, die der spätere Adapter
explizit allowlistet.

## Begrenztes Capture

stdout und stderr werden über nicht blockierende Pipes und einen Selector
gelesen. Jeder Kanal besitzt die explizite Bytegrenze des Aufrufs.

Die Grenze ist positiv und maximal 1 MiB. Timeout ist positiv und höchstens
eine Stunde; die Terminate-Grace ist positiv und höchstens 30 Sekunden.

Ein überschrittener Kanal wird exakt an der Grenze abgeschnitten und als
`truncated` markiert. Der Prozess erhält dann SIGTERM.

Bei Timeout erhält die neue Prozessgruppe ebenfalls genau ein SIGTERM. Endet
sie nicht innerhalb der Grace, folgt SIGKILL und `hard_killed` wird wahr.

Timeout, Truncation und Hard Kill sind ausschließlich technische
Nichtverfügbarkeit und können nie durch den Parser zu `passed` werden.

## Beobachtung

`ProcessObservation` enthält nur Returncode, begrenzte stdout-/stderr-Bytes
sowie die drei neutralen Kontrollflags.

Sein `repr` enthält weder argv, Umgebung, Arbeitsverzeichnis noch Output.

Ein interner Start-, Pipe-, Selector-, Signal- oder Waitfehler wird detailfrei
als `staging_process_unavailable` vereinheitlicht.

## Phasenparser

Für jede der 29 LQ-306-Phasen existiert genau ein fest benanntes Boolean-
Faktum. Beispiele sind Digestgleichheit, UID/GID-Gleichheit, isolierte Netze,
exakter Migration-Head, Artifacthash, Revocation und kontrollierter Stop.

Akzeptiert wird ausschließlich ein JSON-Objekt mit Schema-Version eins,
exaktem Phasennamen und exakt dem zugehörigen `facts`-Schlüssel.

Doppelte oder unbekannte Schlüssel, falsche Typen, falsche Phase, zusätzliche
Zeilen, stderr, Nonzero-Exit, leerer Output oder nicht kanonisch reduzierbare
Antworten sind `staging_process_unavailable`.

Das Boolean `true` wird neutral zu `passed`, `false` zu `failed`. Technische
Fehler werden niemals als fachlicher Fail umgedeutet.

## Redaction

Vor JSON-Auswertung sperrt der Parser DSN-Schemata, HTTP(S)-URLs, bekannte
private Pfadpräfixe, Secretpfade, Credential-/Password-/Authorizationbegriffe
und Private-Key-Marker.

Der reduzierte Output wird neu als kanonisches sortiertes JSON erzeugt. Raw
stdout oder stderr wird nicht weitergereicht.

## Ressourcenbesitz

Der Runner besitzt nur den von ihm gestarteten kurzlebigen Prozess, dessen
Prozessgruppe, Pipes und Selector.

Im `finally` bleibt kein laufender Kindprozess zurück. Externe Docker-,
Compose-, Datenbank-, Image-, Volume- und Netzwerkressourcen werden weder
erkannt noch besessen.

## Bundlekorrektur

LQ-306 und LQ-308 ergänzen jeweils ein Operatormodul ohne Console Entry Point.
Das Operational-Bundle-Gate erwartet deshalb jetzt weiterhin 22 Entry Points,
aber 23 Operatormodule.

Migration-Head und Migrationszahl bleiben unverändert `20260819_0027` und 27.

## Nichtziele

Keine feste Docker-Kommandotabelle, Phase-zu-Command-Composition,
Evidenceobjekt-Persistenz, CLI oder reale Stagingausführung wird implementiert.

Es gibt keine Schema-, SQL-, Migration-, Port-, Domainmodell- oder
Composeänderung.

## Nächster Slice

LQ-309 sollte die feste Phase-zu-Command-Composition und den privaten atomaren
EvidenceObjectSink implementieren. Erst diese Composition darf reduzierte
Parsergebnisse in `StagingPhaseEvidence` für LQ-306 überführen.
