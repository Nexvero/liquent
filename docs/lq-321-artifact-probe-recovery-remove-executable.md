# LQ-321 — Artifact Probe Recovery Remove Executable

## Ergebnis

LQ-321 implementiert den installierbaren bewusst schreibenden In-Image-Command
`liquent-artifact-probe-recovery-remove`.

Er revalidiert genau einen rungebundenen LQ-317-Probe-Prefix und entfernt nur
einen vollständig als recoverable bestätigten Bestand. Abwesenheit bleibt
idempotent, Conflict bleibt unverändert und technische Mehrdeutigkeit endet
ohne Blind-Cleanup.

Der Slice komponiert oder startet noch keinen Dockercontainer und stellt keine
Recovery-Autorisierungsgrenze bereit.

## Geschlossener Aufruf

Der Command akzeptiert ausschließlich `--run-token` mit exakt 64 lowercase-
Hexzeichen. Root, Volume, Prefix, Namen, Inhalte, erwarteter Zustand oder
Allow-Boolean sind nicht aufrufbar.

Das Root ist fest `/var/lib/liquent/artifacts`; darunter wird nur
`.liquent-staging-probe-<token>` descriptor-relativ und no-follow adressiert.

Ungültiger Token endet vor Dateisystemzugriff still unavailable.

## Abwesenheit

Ein nachweislich fehlender exakter Prefix liefert `already_absent` ohne Write,
Erzeugung oder Suche nach ähnlichen Objekten.

Dieser Ausgang ist technisch idempotent. Er beweist keinen früheren
Capability-Erfolg und ändert die ursprüngliche unavailable Stagingphase nicht.

## Vollständige Revalidierung

Vor dem ersten Unlink muss das Root ein echtes Verzeichnis des effektiven Users
ohne Group-/World-Write sein.

Der Prefix muss ein echtes Verzeichnis desselben Users mit Modus 0700 sein.
Zulässig sind nur:

- leerer Prefix;
- ausschließlich `.capability.tmp`;
- ausschließlich `capability.json`;
- beide Namen als zwei Hardlinks auf denselben Inode desselben Devices.

Jede Datei wird no-follow vollständig gelesen und muss regulär, Owner des
effektiven Users, Modus 0600, exakt groß und bytegleich mit den festen
LQ-317-Probebytes sein. SHA-256 und Linkcount müssen passen.

Beide Namen verlangen gemeinsame Device-/Inodebindung und Linkcount zwei;
ein einzelner Name verlangt Linkcount eins.

Unbekannte Namen, zusätzliche Objekte, Symlinks, abweichende Metadaten oder
Inhalte, unabhängige Dateien und externe Hardlinks ergeben `conflict` ohne
Mutation.

## Compare-before-unlink

Nach dem vollständigen Snapshot wird jeder bekannte vorhandene Name direkt vor
seinem Unlink erneut no-follow geöffnet und vollständig validiert.

Inhalt, Typ, Owner, Modus, Größe und Digest müssen weiterhin stimmen; Device
und Inode müssen exakt zum unmittelbar zuvor aufgenommenen Snapshot gehören.

Eine Abweichung oder technisch uneindeutige erneute Beobachtung stoppt vor dem
betroffenen Unlink unavailable. Ein caller-gelieferter früherer
LQ-320-Ausgang wird nicht akzeptiert.

Die feste Remove-Reihenfolge ist temporärer Name, danach finaler Name. Es gibt
kein Glob, rekursives Löschen, Rename, Truncate oder Entfernen unbekannter
Objekte.

## Dauerhafte Entfernung

Nach den bekannten Dateien fsynct der Command das Probeverzeichnis und prüft
erneut, dass es leer ist.

Danach entfernt er ausschließlich den exakten Prefix, fsynct das Volumeroot
und bestätigt descriptor-relativ dessen Abwesenheit.

Nur die vollständig bestätigte Sequenz liefert `removed`.

## Unknown Outcome

Create findet nicht statt. Uneindeutiger Open-, Read-, Stat-, List-, Unlink-,
Rmdir-, Fsync- oder Abwesenheitsausgang endet detailfrei mit Exitcode zwei.

Nach dem ersten möglichen Remove-Effekt folgt kein Retry und kein Versuch,
verbliebene bekannte Namen oder das Prefix noch zu entfernen. Ein simulierter
verlorener Unlink-Acknowledgement beweist diese Stopgrenze.

Ein späterer Recoveryversuch muss wieder mit LQ-320 read-only beginnen und die
dann sichtbare Realität neu klassifizieren.

Es gibt keinen dritten Pfad, Volume-Remove, Compose-Down, Prune oder Zugriff auf
reguläre Artifacts.

## Neutrale Ausgabe

Exitcode null schreibt ausschließlich kanonisches JSON mit Schema-Version,
Operation `artifact_probe_recovery_remove` und einem Ausgang:

- `already_absent`;
- `removed`;
- `conflict`.

Token, Volume, Prefix, Namen, Inhalt, Digest, Device, Inode, Owner, Modus und
Fehlerdetails werden nicht ausgegeben.

Kein Ausgang gewährt Readiness, Artifactfähigkeit oder Deploymentfreigabe.

## Tests

Lokale Tests decken alle vier recoverable Zustände, idempotente Abwesenheit und
unveränderte Konflikte ab.

Ein injizierter Fehler nach tatsächlich erfolgtem ersten Unlink lässt den
verbliebenen finalen Namen unangetastet und endet unavailable. Es wird kein
Dockercontainer oder externes Volume verwendet.

## Bundle und Nichtziele

Der Entry Point und das Operatormodul erhöhen die Bundle-Gates auf 27 Entry
Points und 30 Operatormodule. Migrationen bleiben 27 mit Head
`20260819_0027`.

LQ-321 enthält keine owner-only Recovery-Dateigrenze, Docker-Composition,
Autorisierungsprüfung, Evidenceablage, Stagingentscheidung, Compose-, Schema-,
SQL-, Migration-, Port-, Domainmodell- oder Production-Wiring-Änderung.

## Nächster Slice

LQ-322 sollte die owner-kontrollierte Recovery-Composition implementieren:
zuerst LQ-320 mit read-only Volume, danach nur bei recoverable LQ-321 mit
read-write Volume, jeweils aus derselben erneut validierten Run- und
Recoverybindung.
