# LQ-509 — Physical Supervisor Control-Directory Cleanup Execution Contract

## Ergebnis

LQ-509 definiert die Sicherheitsgrenze für die erste physische Wirkung eines
Supervisor-Control-Directory-Cleanups.

Der Slice implementiert keine Dateioperation, Domainwerte, Ports oder
Persistenzänderung.

## Einziger zulässiger Eingang

Physische Ausführung darf nur aus einem durch LQ-508 atomar erzeugten Paar aus
Started-Attempt und immutable Clearance vorbereitet werden.

Ein alleinstehender LQ-494-Attempt, ein Cleanuprequest, eine Directory-ID oder
eine separat gelesene Clearance öffnet keine Dateiwirkung.

## Exakte Bindung

Attempt, Clearance, Actor, Directory, Retentiondecision und alle gebundenen
Quellrevisionen müssen unverändert zusammengehören.

Cross-Attempt-, Cross-Actor-, Cross-Directory- und Cross-Revision-Adoption ist
ausgeschlossen.

## Keine Authority aus dem Principal

Der authentifizierte SessionPrincipal identifiziert nur den Actor.

Er trägt keine Cleanup-, Membership-, Research- oder Dateisystemauthority.

Caller-gelieferte Allowbooleans, Rollen, Capabilities, Pfade oder
Inventurergebnisse werden nicht akzeptiert.

## Aktuelle Freigabe

Unmittelbar vor einer Write-Claim-Entscheidung muss die vollständige aktuelle
Clearance erneut aus dem persistenten System of Record aufgelöst werden.

Management-, Retention-, Hold-, Recovery-, Referenz-, Registry- und
Terminaljournalfakten werden dabei erneut gegen Actor und Ziel gebunden.

Ein committierter Widerruf oder neuer Blocker sperrt jede später begonnene
Write-Claim-Entscheidung.

## Aktueller Attempt

Nur der exakt gebundene Attempt im Zustand `started` darf die physische
Vorbereitung erreichen.

Completed, reconciled, unbekannte und bereits write-geclaimte Attempts dürfen
nicht erneut physisch ausgeführt werden.

## Serverseitige Zielauflösung

Die Directory-ID führt über die aktuelle Registry ausschließlich zu einem
vollständigen Retired-Wert und dessen unverändertem stabilen Leaf.

Root und Leaf werden niemals aus Callerpfaden, Handletext, Dateiinhalten oder
einer früher publizierten absoluten Adresse rekonstruiert.

Reserved, Active oder divergente Registryfakten sperren die Ausführung.

## Kontrolliertes Root

Das private absolute Root stammt ausschließlich aus kontrollierter
Adapterkonfiguration.

Es wird bei jedem Versuch neu als echtes, symlinkfreies, process-eigenes
Directory mit exaktem Modus `0700` geprüft.

Namensfakten und geöffneter Rootdescriptor müssen dasselbe Device und denselben
Inode bezeichnen.

## Exaktes Leaf

Nur das persistierte 64-stellige Hex-Leaf darf relativ zum bereits geöffneten
Rootdescriptor betrachtet werden.

Das Leaf muss ein echtes, symlinkfreies, process-eigenes Directory mit Modus
`0700` sein.

Namensfakten und geöffneter Leafdescriptor werden über Device und Inode
gebunden; ein Austausch wird nicht adoptiert.

## Unmittelbare read-only Inventur

Vor jedem Write-Claim wird das Leaf über gebundene Descriptoren vollständig
und begrenzt inventarisiert.

Die Inventur darf keine Datei anlegen, öffnen mit Schreibrecht, umbenennen,
chmodden, chownen, truncaten oder entfernen.

Ein früherer Preflightreport oder gecachter Directorybestand genügt nicht.

## Geschlossenes Artefaktset

Zulässig sind ausschließlich die kanonischen Control-Artefaktrollen, die für
genau dieses terminale Handoff persistent belegt sind.

Jeder vorhandene Name wird intern aus seiner Rolle abgeleitet und gegen
Artifact-ID, Handle, Korrelation, Bytezahl, Digest und kanonisches Decoding
gebunden.

Caller können keine Namen oder erlaubte Dateiliste ergänzen.

## Physische Dateifakten

Jedes belegte Artefakt muss eine symlinkfreie reguläre private Datei im Besitz
der effektiven Prozess-UID sein.

Zusätzliche Hardlinks, unbekannte Namen, Unterdirectories, Spezialdateien,
Sockets oder ausgetauschte Inodes sperren jede Mutation.

Eine persistierte Rolle ohne erwartete Datei und eine Datei ohne passenden
persistenten Record werden nicht stillschweigend bereinigt.

## Autoritative Abwesenheit

Eine autoritativ unbekannte Directory-ID bleibt neutrale Abwesenheit ohne
Dateisystemzugriff.

Ein sicher belegtes fehlendes Leaf eines weiterhin vollständig gebundenen
Retired-Ziels kann vor jeder Wirkung als `already_absent` abgeschlossen werden.

Abwesenheit entfernt keine Registry-, Journal-, Clearance- oder
Attempthistorie und gibt keine Identität zur Wiederverwendung frei.

## Write-Claim vor Wirkung

Nach positiver aktueller Clearance und positiver Inventur muss der Attempt
dauerhaft und atomar aus `started` in einen eigenen Write-Claim-Zustand
überführt werden.

Dieser Commit liegt zwingend vor dem ersten möglicherweise wirksamen
Dateisystemaufruf.

Genau ein erfolgreicher Zustandsübergang besitzt das Recht auf den einmaligen
physischen Aufruf.

## Kein Umdeuten von outcome_unknown

Der bestehende Zustand `outcome_unknown` beschreibt einen bereits unklaren
Mutationsausgang.

Er darf nicht nachträglich als vorwirklicher Write-Claim oder allgemeiner Lock
umgedeutet werden.

Der spätere Implementierungsslice benötigt dafür einen ausdrücklich
geschlossenen neuen Zustand und Übergang.

## Revocation-Semantik

Der atomar committierte Write-Claim ist die letzte Authorityentscheidung vor
der irreversiblen Wirkung.

Ein davor committierter Entzug verhindert den Claim; ein danach committierter
Entzug macht den bereits autorisierten einmaligen Effekt nicht rückwirkend
unentscheidbar.

Zwischen Claim und Effekt darf kein Queueing, Batchen oder verzögerter
Hintergrundlauf liegen.

## Einmalige physische Ausführung

Nach dem Claim verwendet die Ausführung nur die bereits sicher geöffneten und
gebundenen Root- und Leafdescriptoren.

Sie entfernt ausschließlich jedes vorher belegte kanonische Artefakt und
danach das nachweislich leere Leafdirectory.

Generisches rekursives Löschen, Globs, absolute Pfadmutation, Shellaufrufe und
Symlinkfolge sind verboten.

## Revalidierung je Name

Unmittelbar vor jeder Namensmutation werden Name, Typ, Eigentümer, Modus,
Linkzahl, Device und Inode erneut gegen die Inventur gebunden.

Neue Einträge oder Drift stoppen weitere Wirkungen sofort.

Nach jeder irreversiblen Namensmutation wird der jeweilige Parentdescriptor
dauerhaft synchronisiert.

## Abschlussprüfung

`removed` darf erst nach bestätigter Entfernung aller belegten Artefakte,
bestätigter Abwesenheit des Leafs und erfolgreicher Root-Synchronisierung
persistiert werden.

Ein erfolgreich zurückgekehrter einzelner Unlink ist noch kein
Cleanupabschluss.

Root, Nachbarleafs und persistente Registryfakten bleiben unverändert.

## Unklarer oder partieller Ausgang

Jeder Fehler ab dem committierten Write-Claim führt zu einem nicht blind
wiederholbaren, reconciliation-pflichtigen Ausgang.

Das gilt auch bei Timeout, Prozessabbruch, fehlender Bestätigung oder nur
teilweise entfernten Artefakten.

Der Caller erhält weder Erfolg noch die Behauptung, es sei nichts geschehen.

## Keine blinde Wiederholung

Ein write-geclaimter Attempt darf den physischen Aufruf niemals ein zweites
Mal starten.

Restart und Retry beginnen mit rein lesender Reconciliation der persistenten
Bindungen und des aktuellen Dateisystembestands.

Ein neuer Attempt darf erst nach einem ausdrücklich terminal entschiedenen
alten Ausgang geprüft werden.

## Reconciliation-Untergrenze

Sicher belegte Abwesenheit kann zu einem terminal reconciled-absent Ergebnis
führen.

Vollständig unveränderter Bestand kann nur als present festgestellt werden;
er autorisiert keinen Retry desselben Attempts.

Partieller, unbekannter oder unsicherer Bestand bleibt detailfreier Konflikt
und wird weder vervollständigt noch rekonstruiert.

## Keine Reparatur

Cleanup chmodded, chowned, ersetzt, verschiebt oder adoptiert keine Datei.

Es erzeugt keine fehlenden Artefakte neu und restauriert kein teilweise
entferntes Directory.

Manuelle Incident- oder Recoveryverfahren bleiben außerhalb dieses Vertrags.

## Neutrale Abwesenheit und Zurückweisung

Unbekanntes Ziel bleibt neutral, bevor physische Details aufgelöst werden.

Unzureichende Authority, nicht positive Clearance, falscher Attemptzustand,
nicht Retired oder unsichere Inventur werden detailarm zurückgewiesen.

Diese Ergebnisse offenbaren weder Existenz, Pfad, Leaf noch Artefaktnamen.

## Technische Unverfügbarkeit

Unlesbare Systeme of Record, Descriptorfehler, fehlende sichere
Plattformprimitive und nicht verifizierbare Dauerhaftigkeit bleiben
detailfreie technische Unverfügbarkeit.

Technische Unverfügbarkeit autorisiert keine Best-effort-Mutation und wird
nicht zu neutraler Abwesenheit normalisiert.

Der Vertrag benennt keinen neuen Exceptiontyp.

## Retention und Nichtwiederverwendung

Physischer Cleanup betrifft ausschließlich freigegebene lokale Bytes.

Directory-ID, Handle, Leaf, Actor-, Decision-, Revision-, Clearance-, Attempt-
und Outcomehistorie bleiben mindestens dauerhaft auditierbar und gegen
Wiederverwendung gebunden.

Eine spätere Policy darf länger aufbewahren, diese Untergrenze aber nicht
verkürzen.

## Kein Implementierungsslice

LQ-509 entscheidet keine Domainklasse, Portsignatur, Tabelle, Migration, SQL,
Dateisystemprimitive, Plattformunterstützung oder Adapterstruktur.

Es ergänzt keinen Cleanup-, Reconciliation-, CLI-, Route-, Timer-, Worker-,
Startup-, Shutdown- oder Production-Wiringpfad.

Head bleibt `20260826_0039` mit 39 linearen Migrationen.

## Tests

Fokussierte Vertragsprüfungen belegen die LQ-508-Eingangsbindung, aktuelle
Revalidierung, geschlossene read-only Inventur, den dauerhaften Write-Claim vor
Wirkung, einmalige descriptorrelative Mutation und Reconciliation ohne Retry.

## Nächster Slice

LQ-510 sollte geschlossene Preflight-, Write-Claim-, physische Ergebnis- und
Reconciliationwerte sowie ihre Ports definieren.

Schema, Persistenzadapter, Dateisystemwirkung und Production-Wiring bleiben
danach getrennte Slices.
