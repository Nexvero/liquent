# LQ-513 — One-Shot Local Supervisor Control-Directory Physical Cleanup

## Ergebnis

LQ-513 implementiert die einmalige lokale physische Entfernung eines
vollständig gebundenen Supervisor-Control-Directory-Cleanup-Claims.

Der Adapter persistiert selbst kein Outcome und führt keine Reconciliation
aus.

## Einziger Eingang

`remove_control_directory` akzeptiert ausschließlich den vollständigen
LQ-510-Claimed-Wert.

Attempt-ID, Directory-ID, Claim-ID, Clearance und Preflight stammen aus diesem
geschlossenen Wert.

Caller können weder Root, Leaf, Handle, Pfad, Dateiname, Rollenliste,
Allowboolean noch erwarteten Ausgang ergänzen.

## Persistenter Claim

Vor jedem Dateisystemzugriff wird der Claim über seine Attempt-ID aus dem
persistenten System of Record aufgelöst.

Nur ein vollständiger `write_claimed`-Wert, der dem übergebenen Claimed-Wert
exakt entspricht, darf fortfahren.

Unbekannter, bereits weitergeschalteter oder abweichender Claim ist vor Wirkung
ein detailfreier Konflikt.

## Keine erneute Authorityentscheidung

Der committierte LQ-511-Claim bleibt die letzte Authorityentscheidung.

LQ-513 akzeptiert keinen Principal und liest kein caller-geliefertes
Authoritysnapshot.

Der Adapter revalidiert den persistenten Claim, er erzeugt aber keine neue
Management-, Membership- oder Researchauthority.

## Aktuelles Retired-Ziel

Die Directory-ID wird aktuell über den persistenten Lifecyclelookup
aufgelöst.

Nur der vollständige Retired-Wert mit exakt derselben Directory-ID liefert
Handle und Leaf.

Reserved, Active, unbekanntes oder divergentes Ziel sperrt jede Wirkung.

## Aktuelle Artefaktrecords

Für den intern gebundenen Handle werden alle vier geschlossenen Artefaktrollen
aktuell aufgelöst.

Nur vollständige Records mit exakt passendem Handle und passender Rolle werden
akzeptiert.

Die erste vollständige Recordmenge bleibt die Vergleichsbasis für jede
nachfolgende Revalidierung dieses Aufrufs.

## Kontrolliertes Root und Leaf

Das absolute Root wird ausschließlich konstruktiv injiziert und bei jedem
Aufruf erneut über `lstat`, No-follow-Directorydescriptor, Owner, Modus `0700`,
Device und Inode gebunden.

Nur das persistierte Leaf wird relativ zu diesem Root geöffnet.

Leaf-Eintrag und Descriptor müssen ebenfalls ein process-eigenes echtes
`0700`-Directory mit identischem Device und Inode bezeichnen.

## Kein Already-absent nach Claim

Ein fehlendes Leaf ist nach einem gültigen Write-Claim kein normaler
`already_absent`-Ausgang.

Vor einem Effekt wird es als Konflikt behandelt, weil LQ-512 ein vorhandenes
sicheres Leaf für Prepared belegt hatte.

Nach möglicher Wirkung wird Abwesenheit ausschließlich als Teil des bestimmten
Removed- oder unklaren Unknown-Ausgangs bewertet.

## Exakte Ausgangsinventur

Vor der ersten Mutation muss die Namensmenge exakt den aktuell persistent
vorhandenen kanonischen Artefaktrollen entsprechen.

Jede erwartete Datei wird erneut vollständig wie in LQ-512 geprüft: regulär,
process-eigen, `0600`, Single-Link, begrenzt, kanonisch und vollständig an den
persistenten Record gebunden.

Unbekannte Namen, Publisher-Temporärdateien, Unterdirectories, Spezialdateien,
fehlende Records oder Drift sperren ohne Wirkung.

## Gemeinsame kanonische Namen

LQ-513 verwendet denselben geschlossenen Rollen-zu-Dateiname-Helper wie
Publisher und LQ-512.

Es gibt keine zweite freie Namenskonfiguration, Globs oder Pfadverkettung.

Die Entfernung iteriert ausschließlich in der festen Reihenfolge der vier
geschlossenen Rollen.

## Revalidierung vor jedem Artefakt

Unmittelbar vor jedem einzelnen `unlink` werden persistenter Claim,
Retired-Ziel und vollständige Artefaktrecordmenge erneut aufgelöst.

Root, Leaf, verbleibende Namensmenge und alle verbleibenden Artefaktbytes
werden erneut vollständig geprüft.

Die konkret zu entfernende Datei wird direkt danach nochmals gegen ihren
Record gebunden.

## Relative Einzelwirkung

`unlink` erhält ausschließlich den intern kanonischen Namen und den geöffneten
Leafdescriptor.

Es gibt kein absolutes Delete, `chdir`, Shellkommando, Glob oder rekursives
Entfernen.

Nach jedem erfolgreichen Artefakt-Unlink wird der Leafdescriptor synchronisiert.

## Keine unbekannten Einträge

Der Adapter entfernt niemals einen Namen, der nicht zu einem persistent
gebundenen kanonischen Artefakt gehört.

Er toleriert auch keine nachträglich erschienene Datei.

Unbekannter Bestand wird nicht verschoben, adoptiert oder best-effort
bereinigt.

## Finales leeres Leaf

Nach allen bekannten Artefakten müssen die erwartete Restmenge und die aktuelle
Directoryinventur beide leer sein.

Claim, Retired-Ziel, Artefaktrecords, Root und Leaf werden davor erneut
gebunden.

Erst dann darf exakt das persistierte Leaf relativ zum Rootdescriptor mit
`rmdir` entfernt werden.

## Dauerhaftigkeit

Nach `rmdir` wird der Rootdescriptor synchronisiert.

Anschließend muss ein No-follow-Stat des exakten Leafs autoritativ
`FileNotFound` liefern und das Root weiterhin denselben sicheren Bestand
bezeichnen.

Ein bloß erfolgreicher Systemcall genügt nicht für Removed.

## Removed

Nur nach vollständiger Artefaktentfernung, Leafabwesenheit, Root-fsync und
Rootrevalidierung liefert der Adapter
`RemovedManifestHandoffSupervisorControlDirectory`.

Der Wert bindet dieselbe Claim-, Attempt- und Directory-ID sowie eine aware UTC
Zeit nicht vor `claimed_at`.

Removed persistiert noch keinen Completed-Zustand.

## Wirkungsschwelle

Unmittelbar vor dem ersten `unlink` oder dem abschließenden `rmdir` wird intern
festgehalten, dass ein physischer Effekt begonnen haben kann.

Vor dieser Schwelle bleiben unsichere oder divergente Fakten detailfreier
Konflikt beziehungsweise technische Unverfügbarkeit.

Ab dieser Schwelle darf kein Fehler als sichere Nichtwirkung ausgegeben werden.

## Unknown nach möglicher Wirkung

Jeder System-, Lookup-, Clock-, Revalidierungs- oder Dauerhaftigkeitsfehler
nach Beginn eines Effekts liefert den geschlossenen
`UnknownManifestHandoffSupervisorControlDirectoryCleanupEffect`.

Auch Drift nach bereits entfernten Artefakten, partieller Bestand oder
fehlende Abschlussbestätigung endet Unknown.

Unknown bindet dieselbe Claim-, Attempt- und Directory-ID und autorisiert
keinen Retry.

## Keine blinde Wiederholung

Der Adapter besitzt keine Retry-, Resume- oder Continue-Methode.

Ein später erneut aufgelöster Attempt befindet sich nach persistiertem Unknown
nicht mehr in `write_claimed` und wird vor Wirkung abgelehnt.

Nur die separate read-only Reconciliation darf den physischen Bestand danach
klassifizieren.

## Keine Reparatur

LQ-513 verwendet kein `mkdir`, `link`, `rename`, `replace`, `chmod`, `chown`
oder `truncate`.

Es stellt keine Datei wieder her, vervollständigt keinen partiellen Cleanup und
adoptiert keinen ausgetauschten Inode.

Root, Nachbarleafs und persistente Fakten werden nicht entfernt.

## Fehlergrenze

Vor Wirkung bleiben Persistenz- und Rootinfrastrukturfehler detailfreie
technische Unverfügbarkeit.

Unsicheres Ziel oder Inventar ist detailfreier Cleanupkonflikt.

Nach möglicher Wirkung werden beide Kategorien bewusst zu Unknown vereinheitlicht,
damit kein unsicherer Wiederholungsweg entsteht.

LQ-513 benennt keinen neuen Exceptiontyp.

## Keine Outcome-Persistenz

Der lokale Adapter schreibt keine Attempt-, Claim-, Completed- oder
Outcome-unknown-Zeile.

Eine spätere kontrollierte Composition muss Removed beziehungsweise Unknown
unmittelbar persistent abschließen.

Sie darf bei fehlgeschlagener Persistenz nach physischer Wirkung keinen
zweiten Remove-Aufruf starten.

## Kein Schema oder Wiring

LQ-513 ergänzt keine Tabelle, Migration, SQL, Portsignatur, Route, CLI,
Worker-, Timer-, Startup-, Shutdown- oder Productionverdrahtung.

Head bleibt `20260826_0040` mit 40 linearen Migrationen.

## Tests

Fokussierte Prüfungen belegen persistenten Claim und Retired-Lookup,
vollständige Post-Claim-Inventur, Revalidierung vor jedem Namen,
descriptorrelative Einzel-Unlinks, fsync-Reihenfolge, leeres finales Rmdir,
bestätigte Abwesenheit und Unknown ab der Wirkungsschwelle.

## Nächster Slice

LQ-514 sollte physisches Removed beziehungsweise Unknown unmittelbar und
claimgebunden in den bestehenden Attemptzustandsautomaten persistieren.

Read-only Reconciliation und Production-Wiring bleiben danach getrennte
Slices.
