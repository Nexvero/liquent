# LQ-512 — Safe Local Read-Only Supervisor Control-Directory Cleanup Preflight

## Ergebnis

LQ-512 implementiert den sicheren lokalen read-only Preflight für den
physischen Supervisor-Control-Directory-Cleanup.

Der Adapter inventarisiert und verifiziert ausschließlich; er entfernt oder
verändert keine Datei.

## Kontrollierter Eingang

Der Adapter implementiert nur
`prepare_control_directory_cleanup` aus dem LQ-510-Preflight-Port.

Der Request trägt ausschließlich Attempt-ID und Directory-ID.

Root, Leaf, Handle, Actor, Pfad, Artefaktnamen, Rollenliste oder Allowboolean
können nicht vom Caller vorgegeben werden.

## Started-Attempt

Die Attempt-ID wird über einen injizierten persistenten Lookup aktuell
aufgelöst.

Nur der vollständige bestehende Started-Cleanuprequest mit exakt derselben
Attempt- und Directory-ID darf fortfahren.

Unbekannter Attempt bleibt neutral `None`; andere Zustände und Cross-Bindings
liefern den detailfreien Cleanupkonflikt.

## Aktuelle Clearance

Aus dem persistenten Attempt wird der Actor intern übernommen und die aktuelle
vollständige LQ-498-Clearance aufgelöst.

Sie muss exakt denselben Request und dasselbe Retired-Directory binden.

SessionPrincipal, frühere Allowentscheidung oder caller-gelieferte Clearance
werden nicht akzeptiert.

## Retired-Ziel

Handle und 64-stelliges Hex-Leaf stammen ausschließlich aus dem vollständigen
Retired-Wert der Clearance.

Der Adapter konstruiert kein Ziel aus Directory-ID, Handletext oder
Dateiinhalten.

Reserved, Active oder divergente Lifecyclefakten erreichen keinen
Dateisystemzugriff.

## Konstruktives Root

Das absolute private Root wird kontrolliert in den Adapter injiziert.

Der Konstruktor führt kein I/O aus und legt Root oder Leaf nicht an.

Relative und caller-gelieferte Roots werden abgelehnt.

## Rootprüfung

Bei jedem Preflight wird das Root zuerst mit `lstat` und danach mit
Directory-, No-follow- und Close-on-exec-Semantik geöffnet.

Es muss ein echtes Directory im Besitz der effektiven Prozess-UID mit exaktem
Modus `0700` sein.

Pfad- und Descriptorfakten müssen dasselbe Device und denselben Inode
bezeichnen.

## Leaföffnung

Nur das persistierte Leaf wird relativ zum geöffneten Rootdescriptor geöffnet.

Auch das Leaf muss ein echtes process-eigenes `0700`-Directory sein.

Eintrag und Descriptor werden über Device und Inode gebunden; Symlink,
Nichtdirectory, fremder Eigentümer, falscher Modus oder Austausch sind
detailfreier Konflikt.

## Sicher belegte Abwesenheit

Fehlt das exakte Leaf unter einem weiterhin sicher gebundenen Root, führt der
Adapter keine weitere physische Operation aus.

Nach erneuter Root- und Clearanceprüfung liefert er den geschlossenen
Absent-Preflight mit Attempt, Directory, Clearance und aware UTC Zeit.

Abwesenheit löscht keine Persistenz und erteilt keine Wiederverwendung.

## Persistentes Artefaktset

Der Adapter fragt jede der vier geschlossenen Rollen `wrapper_ready`,
`release_token`, `release_consumed` und `terminal_envelope` aktuell für den
intern gebundenen Handle ab.

Nur tatsächlich persistent vorhandene vollständige Records bilden das
erwartete Dateiset.

Fremder Handle, abweichende Rolle oder ein unvollständiger Lookupwert ist
technische Unverfügbarkeit.

## Kanonische Namen

Die Zuordnung von Rolle zu den vier kanonischen Dateinamen wird aus der
bestehenden Artifactgrenze über einen geschlossenen Helper wiederverwendet.

Preflight und Publisher besitzen dadurch keine divergierenden Namenslisten.

Freie Namen, Pfadseparatoren, Globs und temporäre `.pending-*`-Dateien sind
nicht zulässig.

## Exakte Inventur

Das Leaf wird vollständig über seinen Descriptor aufgelistet.

Die vorhandenen Namen müssen exakt der Menge persistenter Artefaktrollen
entsprechen.

Unbekannte Namen, fehlende belegte Dateien, Unterdirectories, Spezialdateien
oder zusätzlicher temporärer Bestand sperren den Preflight.

## Private reguläre Dateien

Jede erwartete Datei wird relativ zum Leafdescriptor mit No-follow- und
Close-on-exec-Semantik read-only geöffnet.

Sie muss regulär, process-eigen, exakt `0600` und über genau einen Hardlink
gebunden sein.

Eintrag und geöffnete Datei müssen vor und nach dem Lesen in Device, Inode,
Modus, Owner, Linkzahl, Größe sowie Änderungszeiten übereinstimmen.

## Begrenztes Lesen

Der Adapter liest höchstens 65.536 Bytes plus ein Erkennungsbyte.

Leere oder größere Dateien sind keine sichere Inventur.

Es gibt kein Mapping, Streaming in ein fremdes Ziel oder unbeschränktes
Einlesen.

## Kanonisches Decoding

Jede Datei wird mit dem bestehenden versionierten strikten Codec decodiert und
erneut kanonisch encodiert.

Artifact-ID, Handle, Rolle, Korrelation, Digest, Bytezahl und vollständige
Bytes müssen dem persistenten Record entsprechen.

Unbekannte Keys, doppelte JSON-Keys, nichtkanonische Bytes oder Cross-Bindings
werden nicht adoptiert.

## Abschlussrevalidierung

Nach allen Reads wird die Namensmenge erneut vollständig geprüft.

Root- und Leafbindung werden erneut gegen ihre aktuellen Einträge verglichen.

Danach werden aktuelle Clearance und alle vier persistenten Artefaktrollen
erneut aufgelöst und müssen den zuerst gelesenen Werten exakt entsprechen.

## Prepared

Nur nach vollständigem Erfolg erzeugt der Adapter intern eine stabile
Preflight-ID und liefert den LQ-510-Prepared-Wert.

Prepared-Zeit ist aware UTC und liegt nicht vor Clearance oder dem neuesten
persistierten Artefaktrecord.

Der Wert enthält keine Pfade, Namen, Inodes, Bytes oder Descriptoren.

## Kein Descriptor-Grant

Alle geöffneten Descriptoren werden vor Rückkehr geschlossen.

Prepared ist keine Dateisystemauthority und kein sicherer physischer Snapshot
für eine spätere verzögerte Mutation.

Der physische Adapter muss nach dem LQ-511-Claim unmittelbar vor jedem Effekt
dieselben Root-, Leaf-, Inventar- und Dateifakten erneut prüfen.

## Keine Mutation

Der Adapter verwendet keine Writeflags, `mkdir`, `link`, `rename`, `replace`,
`chmod`, `chown`, `truncate`, `unlink`, `rmdir` oder `fsync`.

Er bereinigt auch keine Publisher-Temporärdatei und repariert keinen Modus.

Preflightfehler lassen den physischen Bestand unverändert.

## Konkurrenz

Drift während der Inventur führt zu Konflikt und nicht zu einem tolerierten
Snapshot.

Die doppelte Inventur und Descriptorbindung verkleinern das Racefenster,
ersetzen aber nicht die verpflichtende Post-Claim-Revalidierung.

Es gibt keinen Lock, der fremde Dateisystemwriter als vertrauenswürdig
annimmt.

## Fehlergrenze

Unbekannter Attempt bleibt neutral vor erwarteter Bindung.

Nicht Started, fehlende positive Clearance und unsichere oder divergente
physische Fakten liefern den bestehenden detailfreien Cleanupkonflikt.

Unlesbare Lookups, unsicheres Root, Clockfehler und unerwartete Plattformfehler
bleiben detailfreie technische Unverfügbarkeit.

LQ-512 benennt keinen neuen Exceptiontyp.

## Keine Persistenz oder Verdrahtung

LQ-512 ergänzt keine Tabelle, Migration, SQL, Attempttransition, Claim,
Outcome- oder Reconciliationmutation.

Es gibt keine Route, CLI, Worker-, Timer-, Startup-, Shutdown-, Service- oder
Productionverdrahtung.

Head bleibt `20260826_0040` mit 40 linearen Migrationen.

## Tests

Fokussierte Prüfungen belegen interne Attempt-/Clearance-/Zielauflösung,
No-follow-Descriptorbindung, exakte doppelte Inventur, private Single-Link-
Dateien, begrenztes kanonisches Lesen, Abschlussrevalidierung und vollständige
Mutationsfreiheit.

## Nächster Slice

LQ-513 sollte die einmalige lokale physische Entfernung aus einem LQ-511-Claim
mit vollständiger Post-Claim-Revalidierung implementieren.

Outcome-Persistenz, Reconciliation und Production-Wiring bleiben danach
getrennte Slices.
