# LQ-320 — Artifact Probe Recovery Inspection Executable

## Ergebnis

LQ-320 implementiert den installierbaren read-only In-Image-Command
`liquent-artifact-probe-recovery-inspect`.

Er klassifiziert ausschließlich den exakten rungebundenen LQ-317-Probe-Prefix
als `absent`, `recoverable` oder `conflict`. Technische Mehrdeutigkeit endet
still unavailable.

Der Command entfernt, erstellt oder verändert kein Dateisystemobjekt und trifft
keine Cleanup-, Readiness- oder Deploymententscheidung.

## Geschlossener Aufruf

Akzeptiert wird ausschließlich `--run-token` mit exakt 64 lowercase-
Hexzeichen. Zusätzliche Argumente, freie Rootpfade, Prefixe, Volume-Namen,
Dateinamen, erwartete Zustände oder Allow-Booleans sind ausgeschlossen.

Das Root ist fest auf `/var/lib/liquent/artifacts` gebunden. Der Inspector
öffnet es no-follow als Directory-Descriptor und adressiert darunter nur
`.liquent-staging-probe-<token>`.

Er listet keine regulären Artifactbereiche und sucht nicht nach ähnlichen
Prefixen.

## Abwesenheit

Ist der exakte Prefix descriptor-relativ nachweislich nicht vorhanden, lautet
das Ergebnis `absent`.

Abwesenheit erstellt keinen Prefix und bedeutet weder früheren Probe-Erfolg
noch gültige Artifact-Capabilities. Sie ist ausschließlich eine neutrale
Recoverybeobachtung.

## Recoverable-Zustände

Ein vorhandener Prefix muss ein echtes no-follow geöffnetes Verzeichnis des
effektiven Users mit Modus 0700 sein.

Genau vier erreichbare Zustände werden akzeptiert:

- leeres Probeverzeichnis;
- ausschließlich `.capability.tmp`;
- ausschließlich `capability.json`;
- beide Namen als Hardlinks auf exakt denselben Inode desselben Devices.

Jede vorhandene Datei muss regulär, Owner des effektiven Users, Modus 0600 und
vollständig lesbar sein. Größe, exakte feste Probebytes und SHA-256 müssen dem
LQ-317-Inhalt entsprechen.

Ein einzelner Name verlangt Linkcount eins. Beide Namen verlangen jeweils
Linkcount zwei sowie identische Inode- und Devicewerte.

Nur dann lautet die Klassifikation `recoverable`.

## Conflict

`conflict` vereinheitlicht eindeutig beobachtete, nicht ausschließlich der
LQ-317-Sequenz zuordenbare Zustände:

- unsichere Root- oder Prefix-Owner-/Moduspolicy;
- Prefix-Symlink oder anderes Nichtverzeichnis;
- unbekannte oder zusätzliche Namen;
- Symlink, Unterverzeichnis oder nicht reguläres Kindobjekt;
- abweichender Owner, Modus, Inhalt, Größe oder Digest;
- externer Hardlink oder unerwarteter Linkcount;
- zwei unabhängige Dateien unter den beiden bekannten Namen.

Der Inspector liest bei Prefix- oder Kind-Symlinks kein Ziel. Conflict gewährt
keine spätere Remove-Autorisierung; diese Entscheidung bleibt bei der noch
nicht implementierten Recovery-Composition.

## Technische Nichtverfügbarkeit

Ungültiger Token sowie uneindeutige Open-, Stat-, List-, Read- oder
Descriptorfehler enden detailfrei mit Exitcode zwei und ohne stdout/stderr.

Es gibt keinen Retry, Fallback, Pfadscan, Cleanup oder Versuch, aus
unvollständiger Beobachtung einen Conflict abzuleiten.

Exceptions enthalten weder Root, Token, Prefix, Namen, Inhalt, Digest,
Metadaten noch Betriebssystemdetail.

## Neutrale Ausgabe

Exitcode null schreibt genau ein kanonisches JSON-Dokument mit:

- `schema_version: 1`;
- `inspection: artifact_probe_recovery`;
- `outcome: absent | recoverable | conflict`.

Die Ausgabe enthält keine Run-, Token-, Volume-, Pfad-, Datei-, Inode-, Owner-,
Modus-, Inhalts- oder Digestwerte.

## Tests

Tests verwenden ausschließlich private temporäre Roots. Sie beweisen alle vier
recoverable Zwischenzustände und vergleichen den vollständigen sichtbaren
Bestand vor und nach der Inspektion.

Unbekannte Namen, abweichende Bytes, breite Modi, unabhängige Dateien,
Symlinks und externe Hardlinks werden als Conflict klassifiziert. Ein
Prefix-Symlink wird nicht verfolgt.

Es wird kein Dockercontainer oder externes Volume verwendet.

## Bundle und Nichtziele

Der neue Entry Point und das Operatormodul erhöhen die Gates auf 26 Entry
Points und 29 Operatormodule. Migrationen bleiben 27 mit Head
`20260819_0027`.

LQ-320 enthält keine Recovery-Autorisierungsdatei, Docker-Composition,
write-time Revalidierung, Remove-Fähigkeit, Evidenceablage, Compose-, Schema-,
SQL-, Migration-, Port-, Domainmodell- oder Production-Wiring-Änderung.

## Nächster Slice

LQ-321 sollte das bewusst schreibende In-Image-Remove-Executable definieren und
implementieren. Es muss denselben vollständigen Zustand unmittelbar vor dem
ersten Unlink erneut prüfen und ausschließlich exakt bekannte Probeobjekte
entfernen. Die autorisierte Docker-Composition bleibt danach separat.
