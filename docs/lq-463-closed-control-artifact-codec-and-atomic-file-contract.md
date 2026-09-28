# LQ-463 — Closed Control Artifact Codec and Atomic File Contract

## Ergebnis

LQ-463 definiert geschlossene Dokumente, Codec sowie atomare Publisher- und
Readerports für private Supervisor-Control-Artefakte.

Der Slice implementiert noch keinen JSON-Codec oder Dateisystemadapter.

## Vier Dokumenttypen

Ready, Release-Token, Release-Consumed und Terminal-Envelope besitzen vier
getrennte unveränderliche Dokumentklassen.

Es gibt kein freies Rollen-/Payloaddokument.

Die Rolle wird durch die Dokumentklasse gesetzt und ist kein Callerparameter.

## Gemeinsame Bindung

Jedes Dokument bindet Artefakt-ID, Supervisorhandle und exakt typisierte
Korrelations-ID.

Ready verlangt eine Gated-Observation-ID.

Token und Consumed verlangen eine Release-ID.

Terminal verlangt eine Terminal-Observation-ID.

## Ready

Ready enthält ausschließlich die gemeinsame Bindung.

Es trägt weder Prozessstatus noch Capabilityentscheidung.

Seine Existenz ersetzt keine direkte Engine-Running-Beobachtung.

## Release-Token

Das Token trägt genau dieselbe Release-ID wie der persistente Release-Commit.

Es enthält keinen freien Tokenstring und kein Allowboolean.

Seine Veröffentlichung autorisiert nicht rückwirkend einen anderen Release.

## Release-Consumed

Consumed ist ein eigener Dokumenttyp und keine Statusänderung am Token.

Es bindet dieselbe Release-ID wie das zuvor gelesene Token.

Ein Ack ohne passenden Commit und Token bleibt in der Composition fail-closed.

## Terminal-Envelope

Das Envelope enthält genau einen bestehenden geschlossenen Writer- oder
Recoveryabschluss.

Der Outcome-Handle muss dem Dokumenthandle entsprechen.

Freie Ergebnisobjekte, Logs, Tracebacks und Engineausgaben sind ausgeschlossen.

Das Envelope allein beweist noch kein Runtime-Ende.

## Artefaktbytes

Kodierte Bytes sind nicht leer und auf 65.536 Bytes begrenzt.

Der Wert ist repr-frei.

Text, Mapping oder Stream sind keine alternativen Eingaben.

Die Grenze verhindert unbegrenzte Resultat- und Diagnosekanäle.

## Kodierter Record

Der kodierte Record bindet Artefakt-ID, Handle, Rolle, Bytes und Artefaktfakten.

Bytezahl muss exakt der Bytelänge entsprechen.

SHA-256 muss exakt aus denselben Bytes berechnet sein.

Divergente Fakten können nicht als gültiger Record konstruiert werden.

## Codec

`encode` akzeptiert ausschließlich die geschlossene Dokumentunion.

`decode` akzeptiert ausschließlich einen bereits faktisch gebundenen kodierten
Record.

Die spätere Implementation muss eine einzige kanonische versionierte
Serialisierung verwenden.

Unbekannte Versionen, Felder, Rollen oder Outcomeformen scheitern fail-closed.

## Kanonische Bytes

Semantisch identische Dokumente müssen byteidentisch kodiert werden.

Schlüsselordnung, UTF-8, Zahlen-, Null- und Whitespaceform werden durch den
späteren Codec festgelegt, nicht durch Caller.

Decode und erneutes Encode müssen dieselben Bytes ergeben.

Es gibt keine tolerante Normalisierung beschädigter Dokumente.

## Publisherrequest

Publish bindet genau eine Control-Directory-ID und einen kodierten Record.

Der Request enthält keinen Pfad, Dateinamen, Modus, temporären Namen oder
Overwrite-Schalter.

Die Zielrolle stammt aus dem kodierten Record.

Control-Directory-ID ist keine Hostpfadangabe.

## Atomare Veröffentlichung

Die spätere Implementation muss private temporäre Anlage, vollständigen Write,
File-fsync, atomare No-replace-Veröffentlichung und Directory-fsync ausführen.

Temporäre Dateien sind keine publizierten Fakten.

Eine vorhandene Rolle wird niemals überschrieben oder umbenannt.

Publisher-Erfolg darf erst nach Directory-fsync zurückkehren.

## Exakter Retry

Ist dieselbe Rolle bereits vorhanden, werden vollständige Bytes verglichen.

Byteidentischer Inhalt liefert denselben faktischen Erfolg.

Jede Abweichung liefert den feldlosen detailfreien Artefaktkonflikt.

Last-write-wins und partielle Reparatur sind ausgeschlossen.

## Published-Record

Der Erfolg enthält nur Control-Directory-ID, Artefakt-ID, Rolle und Fakten.

Er enthält keinen Hostpfad oder Dateideskriptor.

Publikation persistiert noch keine LQ-460-Korrelation.

Die Composition muss die Fakten anschließend über den passenden Rollenstore
binden.

## Reader

Read adressiert nur Control-Directory-ID und geschlossene Rolle.

Neutrale Rollenabwesenheit liefert `None`.

Temporärer, mehrdeutiger, unsicherer oder beschädigter Bestand ist nicht
neutral.

Erfolg liefert denselben kodierten Record samt erneut verifizierten Fakten.

## Sichere Verzeichnisgrenze

Die spätere Implementation löst IDs ausschließlich über eine konstruktiv
injizierte private Registry auf.

Sie muss Eigentümer, Typ, Modus, Nicht-Symlink und feste Rollennamen prüfen.

Callerwerte werden nie zu Pfaden oder Dateinamen zusammengesetzt.

Traversal, Symlink-Following und fremder Bestand bleiben fail-closed.

## Fehlergrenzen

`ManifestHandoffSupervisorControlArtifactConflict` ist feldlos und detailfrei.

Codec-, Decode-, I/O-, fsync-, Eigentümer- und Strukturfehler bleiben an der
bestehenden detailfreien technischen Grenze.

LQ-463 benennt keinen neuen Exceptiontyp.

`None` darf technische Unverfügbarkeit oder unklaren Write-Ausgang nicht
verdecken.

## Keine Authority

Dokumente und Ports akzeptieren keine Session, User-ID, Rolle im
Autorisierungssinn, Permission oder Allowentscheidung.

Control-Artefakte erteilen selbst keine Writer- oder Recoveryfähigkeit.

Journal- und Authorityvoraussetzungen bleiben außerhalb des Fileadapters.

## Keine Prozess- oder Enginewirkung

Die Ports starten, stoppen oder inspizieren keinen Container.

Sie akzeptieren kein Command, PID, Signal, Socket oder Enginehandle.

Publisher und Reader interpretieren kein fachliches Outcome.

## Kein Schema oder Wiring

LQ-463 ändert keine Migration, Tabelle, Spalte, Signatur bestehender Ports oder
Productioncomposition.

Head bleibt `20260824_0032` mit 32 linearen Migrationen.

Es gibt keinen Seed, Backfill, CLI-, Route-, Compose- oder Wrapper-Wiring.

## Tests

Fokussierte Tests belegen vier Dokumente, feste Rollen, typisierte
Korrelationen, Handlebindung des Envelopes, Bytegrenze, Digest-/Längenprüfung,
minimale Codec-/Publisher-/Readerports und fehlende Pfadparameter.

## Nächster Slice

LQ-464 sollte den kanonischen Codec und atomaren lokalen Fileadapter gegen
diese Grenze implementieren.

Wrapper und Supervisorservice folgen separat.
