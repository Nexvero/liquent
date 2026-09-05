# LQ-396 — Read-only PostgreSQL Volume Deletion Claim Inspector

## Ergebnis

LQ-396 implementiert den in LQ-395 definierten read-only Inspector als
`liquent-disposable-postgres-volume-delete-reconcile`.

Der Command klassifiziert finale Evidence, Claimabwesenheit und den aktuellen
Zustand genau eines gebundenen Volume-Deletion-Versuchs.

Er verändert weder Claim, Evidence noch Dockerressourcen.

## Neue Reconciliation-Autorisierung

Jeder Aufruf benötigt eine aktuelle private owner-only Reconciliation-
Autorisierung.

Sie bindet stabile Reconciliation-, Volume-Deletion-, Claim-, Resolver-,
Retention-, Hold- und Recovery-IDs sowie Run, Source, Image, Compose und das
intern abgeleitete Zielvolume.

Die ursprüngliche Lösch- und Resolverautorisierung sowie Lineage-, Retention-,
Hold- und Recoverydateien sind bytegenau über SHA-256 gebunden.

Operation ist exakt `inspect_disposable_postgres_volume_deletion` und Scope
exakt `data_volume_only`.

Das aktuelle UTC-Fenster ist positiv und auf höchstens eine Stunde begrenzt.

## Getrennte Identitäten

Reconciliation-Executor, -Authorizer und -Reviewer müssen drei verschiedene
opake Identitäten sein.

Gemeinsam mit den drei Lösch-, drei Resolver- und drei fachlichen Clearance-
Identitäten müssen insgesamt zwölf verschiedene Identitäten vorliegen.

Eine Kollision stoppt fail-closed und wird nicht als fachlicher Ausgang
veröffentlicht.

Der Inspector übernimmt keine Authority aus Rollen, Membership oder
Dockerkontobesitz.

## Historische Bindungsprüfung

Die ursprüngliche Lösch- und Resolverautorisierung werden in ihren damaligen
gültigen Zeitkontexten strukturell vollständig geprüft.

Dadurch wird ihre historische Bindung bestätigt, ohne eine neue
Mutationsbefugnis zu erzeugen.

Das Lineage-Manifest und jedes darin referenzierte private Artefakt werden
erneut bytegenau geprüft.

Retention-, Hold- und Recoverydateien werden gegen ihre gebundenen Hashes,
Run-, Volume- und ursprünglichen Zeitkontexte validiert.

IDs, Run, Source, Image, Compose, Volume, Scope und sämtliche Hashbeziehungen
müssen über die gesamte Kette übereinstimmen.

## Intern abgeleitete Dateien

Der finale Evidencepfad wird aus dem SHA-256 der Volume-Deletion-ID abgeleitet.

Der Claimpfad wird aus dem SHA-256 der vorab gebundenen Claim-ID abgeleitet.

Projekt und Volume entstehen ausschließlich aus der validierten Run-ID.

Caller können weder Claim-, Evidence- noch Ressourcennamen wählen.

Wildcard-, Prefix-, Labelgruppen-, Projekt- und Hostselektion bleiben
unerreichbar.

## Evidencepriorität

Der Inspector prüft finale LQ-394-Evidence vor Claim und Docker.

Exakt gebundene Evidence mit `remove_exact_volume_once`, bestätigter
Abwesenheit und Ausgang `volume_removed` ergibt
`final_evidence_present`.

Ein gleichzeitig noch vorhandener Claim wird nicht freigegeben.

Malformed, fremde oder widersprüchliche Evidence endet technisch unavailable.

Der Inspector schreibt keine Ersatz-Evidence und wiederholt keinen
Evidence-Retry.

## Not found

Fehlen finale Evidence und exakter Claim gemeinsam, lautet der Ausgang
`not_found`.

Dieser Ausgang entsteht ohne Dockerzugriff.

Er beweist weder Volumenlöschung noch Volumeexistenz und gewährt keine neue
Löschauthority.

Der Inspector erzeugt keinen Claim nachträglich.

## Exakte Claimprüfung

Nur ein offener Claim ohne finale Evidence erreicht Docker.

Der Claim muss regulär, owner-only, einfach verlinkt und kanonisches JSON sein.

Seine vollständige LQ-394-Bindung und zeitzonenbehaftete Startzeit werden
geprüft.

Fremder oder beschädigter Inhalt endet vor Docker technisch unavailable.

Der Claim wird weder geändert, gelöscht, ersetzt noch nach Alter bewertet.

## Begrenzte Dockerbeobachtung

Der Inspector führt zuerst genau eine exakte Namensliste für das intern
abgeleitete Volume aus.

Leere Liste ergibt `volume_absent_evidence_missing` ohne Inspect.

Genau ein exakter Treffer führt zu genau einem `docker volume inspect`.

Exakte Run- und Composeprojektbindung ergibt `volume_present`.

Ein eindeutig lesbares fremd gebundenes Objekt ergibt `conflict`.

Mehrere Treffer, malformed Ausgabe, Nonzero, stderr, Timeout, Truncation oder
Hard Kill bleiben technische Nichtverfügbarkeit.

## Geschlossene Ausgänge

Die CLI liefert ausschließlich:

- `not_found`;
- `final_evidence_present`;
- `volume_present`;
- `volume_absent_evidence_missing`;
- `conflict`;
- technische Nichtverfügbarkeit ohne Ergebnisobjekt.

Die feste Operation lautet
`disposable_postgres_volume_deletion_reconciliation`.

Interne IDs, Hashes, Pfade, Volume-, Claim-, Identitäts- und technische Details
bleiben privat.

## Nachweisbare Read-only-Grenze

Der Inspector besitzt keinen Volume-Remove-, Mount-, Export-, Compose-Down-,
Prune-, Force-, SQL- oder Relabelingpfad.

Er schreibt keine Reconciliation-Evidence und legt keinen weiteren Claim an.

Auch bei finaler Evidence oder Volumeabwesenheit gibt er den bestehenden Claim
nicht frei.

Kein Ausgang startet automatisch Finalizer, Continuation oder neuen
Löschversuch.

## Tests

Dreizehn Tests prüfen:

- `not_found` ohne Docker;
- `volume_present` mit bytegleich erhaltenem Claim;
- `volume_absent_evidence_missing` ohne Inspect;
- `conflict` bei fremder Projektbindung;
- finale Evidencepriorität ohne Docker;
- malformed Claim vor Docker;
- Nonzero, stderr, Timeout und uneindeutige Liste als unavailable;
- Reconciliation-Hashabweichung vor Claim und Docker;
- ausschließlich read-only Docker-argv;
- detailarme CLI und installierten Entry Point.

Alle Dockerprozesse sind fake-basiert; kein echtes Volume wird verändert.

## Bundle und Nichtziele

LQ-396 ergänzt ein Operatormodul und einen Console Entry Point.

Der Bundle-Bestand steigt auf 53 Entry Points und 57 Operatormodule.

Migrationen bleiben 27 mit Head `20260819_0027`.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Domainmodell-,
Compose-, Service-, HTTP- oder Production-Wiring-Änderung.

Der Slice implementiert keine Reconciliation-Evidence, Claimfreigabe,
Finalisierung, Continuation oder weitere Volume-Mutation.

## Nächster Slice

LQ-397 sollte den Evidence-first Finalisierungsvertrag für eindeutig
beobachtete Volume-Deletion-Zustände definieren.

Er muss `volume_present`, `volume_absent_evidence_missing`,
`final_evidence_present`, Conflict und `not_found` geschlossen behandeln und
Evidencepersistenz von Claimfreigabe sowie möglicher Continuation trennen.
