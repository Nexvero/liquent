# LQ-317 — Artifact Capability Inspection Executable

## Ergebnis

LQ-317 implementiert den installierbaren In-Image-Command
`liquent-artifact-capability-inspect` für die LQ-316-Phase
`artifact_capabilities`.

Das Executable prüft die benötigte immutable Artifact-Dateisystemsemantik unter
der effektiven Containeridentität. Es startet keinen Worker und greift weder
auf Datenbank, Netzwerk, Secrets noch Researchdaten zu.

## Geschlossener Aufruf

Der Command akzeptiert ausschließlich `--run-token` mit exakt 64
lowercase-Hexzeichen. Hilfe, zusätzliche Argumente, freie Pfade, Prefixe,
Dateinamen, Inhalte, Digests oder Allow-Booleans werden nicht akzeptiert.

Die spätere Docker-Composition muss den Token intern aus Run-ID und festem
Phasennamen ableiten. LQ-317 trifft diese Compositionentscheidung noch nicht.

Das Artifactroot ist im Image fest auf `/var/lib/liquent/artifacts` gebunden.
Der Probe-Prefix `.liquent-staging-probe-<token>` liegt außerhalb der regulären
LQ-296-Research-Schlüsselgrammatik.

Ein bereits vorhandener Prefix endet vor Mutation technisch unavailable und
wird weder gelesen, übernommen noch entfernt.

## Descriptor-relative Sequenz

Root und Probeverzeichnis werden no-follow als Directory-Descriptoren geöffnet.
Alle Kindoperationen sind relativ zu diesen Descriptoren und verwenden feste
Namen.

Die Probe:

- verlangt ein echtes, vom effektiven User besessenes Root ohne Group-/World-
  Write;
- erzeugt den reservierten Prefix exklusiv mit Modus 0700;
- erzeugt eine exklusive Temporärdatei mit Modus 0600;
- schreibt feste nicht geheime kanonische Bytes vollständig und fsynct sie;
- veröffentlicht ausschließlich per Hardlink und ersetzt kein Ziel;
- fsynct den Verzeichniszustand und entfernt den temporären Namen;
- öffnet das finale Objekt no-follow und prüft Typ, Owner, Modus und Linkcount;
- liest vollständig zurück und prüft Größe, exakte Bytes und SHA-256;
- beobachtet einen zweiten Publish auf denselben Namen als `FileExists`;
- entfernt ausschließlich das finale Probeobjekt und den eigenen leeren Prefix;
- fsynct und bestätigt abschließend die Abwesenheit des Prefix.

Es gibt kein Rename-overwrite, Truncate, Glob, rekursives Löschen oder Listing
regulärer Artifacts.

## Ergebnisgrenze

Vollständiger Erfolg erzeugt exakt das kanonische neutrale JSON-Faktum
`artifact_capabilities_valid=true` und Exitcode null.

Eine vor Mutation eindeutig unsichere Rootpolicy oder ein vollständig
beobachteter Capability-Mismatch ergibt dasselbe Faktum mit `false`.

Die Ausgabe enthält weder Token, Prefix, Pfad, Inhalt, Digest, UID/GID, Modus,
Filesystemtyp noch Systemfehler.

## Unknown Outcome

Ungültiger Token, bestehender Prefix, unerwarteter Typ, Race oder uneindeutiger
Create-, Write-, Fsync-, Link-, Read- oder Remove-Ausgang endet still mit
Exitcode zwei.

Nach einer technischen Exception führt das Executable kein erratenes Cleanup
aus. Ein möglicherweise verbliebener Prefix bleibt Recoverybestand des
gebundenen Runs und darf nicht durch automatischen Retry verändert werden.

Nur die vollständig erfolgreiche oder eindeutig als Mismatch beobachtete
Sequenz entfernt ihre eigenen Objekte und darf neutrales Evidence ausgeben.

## Tests

Lokale Tests verwenden ausschließlich private temporäre Verzeichnisse und
injizierte Rootpfade. Sie prüfen Erfolg mit vollständiger Entfernung,
geschlossene Tokengrammatik, bestehenden Prefix, unsichere Rootpolicy, exakten
Output und stilles CLI-Scheitern.

Ein simulierter verlorener Hardlink-Acknowledgement beweist, dass die bereits
entstandenen Probeobjekte nicht blind entfernt werden. Kein Dockercontainer und
kein externes Volume wird in Tests verwendet.

## Bundle und Nichtziele

Der neue Entry Point und das neue Operatormodul erhöhen die Bundle-Gates auf 25
Entry Points und 28 Operatormodule. Migrationen bleiben 27 mit Head
`20260819_0027`.

LQ-317 enthält keine Docker-Composition, Run-Token-Ableitung, Recovery-
Operation, Evidenceablage, Stagingfreigabe, Compose-, Schema-, SQL-, Migration-,
Port-, Domainmodell- oder Production-Wiring-Änderung.

## Nächster Slice

LQ-318 sollte die gehärtete Docker-Run-Composition für
`artifact_capabilities` implementieren. Sie muss den Token intern aus der
autorisierten Run-Bindung ableiten, ausschließlich das Artifactvolume
read-write mounten und Unknown Outcome ohne Retry oder Blind-Cleanup erhalten.
