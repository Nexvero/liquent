# LQ-401 — Read-only PostgreSQL Volume Deletion Continuation Reconciliation Contract

## Zweck

LQ-401 definiert die strikt read-only Reconciliation eines offenen
LQ-400-Volume-Deletion-Continuation-Claims nach unbekanntem Ausgang.

Sie klassifiziert Evidence-, Claim- und exakten Volumezustand ohne Mutation.
Dieser Slice implementiert keinen Command, Inspector oder Write.

## Separate Reconciliation-Authority

Lösch-, Finalisierungs- und Continuation-Autorisierung gewähren keine
nachträgliche Reconciliation-Authority.

Ein späterer Inspector benötigt eine neue owner-only Autorisierung mit
stabiler, nicht wiederverwendbarer
Volume-Deletion-Continuation-Reconciliation-ID.

Sie muss mindestens geschlossen binden:

- Continuation-Reconciliation-, Continuation- und Continuation-Claim-ID;
- Finalization-, Reconciliation-, Volume-Deletion- und ursprüngliche Claim-ID;
- Volume-Disposition-, Retention-, Legal-Hold- und Recoveryentscheidungs-ID;
- Run-ID und Phase `disposable_postgres`;
- Source-Commit, immutable Image-Referenz und Compose-SHA-256;
- intern abgeleitete exakte Volumeidentität;
- SHA-256 der Continuation-, Finalisierungs-, Reconciliation-, Lösch- und
  Resolverautorisierung;
- Lineage-, Retention-, Hold- und Recoveryhashes;
- Operation exakt
  `inspect_disposable_postgres_volume_deletion_continuation`;
- Scope exakt `data_volume_only`;
- neue getrennte Executor-, Authorizer- und Revieweridentitäten;
- positives aktuelles UTC-Fenster von höchstens einer Stunde.

Caller liefern weder Zustand, Claimstatus, Volumename, Rolle noch
Allow-Boolean.

## Keine geerbte Authority

Ein früheres LQ-396-, LQ-398- oder LQ-400-Ergebnis gewährt keine
Inspectorauthority.

SessionPrincipal, Membership, Researchpermission, Rollenname und Prozesskonto
sind ebenfalls keine Reconciliation-Authority.

Der Actor identifiziert den Inspector, erlaubt aber allein keine Entscheidung.

Deaktivierung, Widerruf, fehlende Bindung oder Identitätsüberschneidung stoppt
fail-closed.

## Vollständige historische Bindung

Der Inspector validiert Resolver-, Lösch-, Reconciliation-, Finalisierungs-
und Continuation-Autorisierung sowie Lineage-, Retention-, Hold- und
Recoveryartefakte erneut.

Historische Autorisierungen werden nur in ihrem damaligen gültigen Kontext
strukturell geprüft. Die neue Reconciliation-Autorisierung muss aktuell sein.

IDs, Run, Source, Image, Compose, Volume, Scope, Identitäten und sämtliche
Hashbeziehungen müssen exakt übereinstimmen.

Neue Inspectorauthority repariert keine historische Evidence und verlängert
kein früheres Zeitfenster.

## Evidence hat Vorrang

Der private Continuation-Evidencepfad wird ausschließlich aus dem
vollständigen SHA-256 der stabilen Continuation-ID abgeleitet.

Vor Claimprüfung und vor jedem Dockerzugriff wird dort vorhandene Evidence
vollständig gegen die historische LQ-400-Bindung geprüft.

Exakt gebundene Evidence ergibt `continuation_evidence_present`.

Ein gleichzeitig noch vorhandener Continuation-Claim wird weder freigegeben
noch verändert. Fehlender Continuation-Claim ändert den Evidenceausgang nicht.

Malformed, teilweise oder fremd gebundene Evidence ist technische
Nichtverfügbarkeit und wird nicht ignoriert, ersetzt oder umbenannt.

## Neutrale Abwesenheit

Fehlen exakt gebundene Continuation-Evidence und der aus der
Continuation-Claim-ID abgeleitete Unterclaim gemeinsam, lautet der Ausgang
`not_found`.

`not_found` ist keine Aussage über das Volume, den ursprünglichen Claim oder
die historische Ausführung und erreicht Docker nicht.

Ein fremder, beschädigter oder technisch unklarer Unterclaim ist niemals
neutrale Abwesenheit.

Der Inspector erzeugt keinen fehlenden Claim nachträglich.

## Kanonischer Unterclaim

Ein vorhandener Continuation-Claim muss regulär, owner-only, einfach verlinkt
und kanonisch gebunden sein.

Er enthält dieselben IDs, Hashes, exakte Volumeidentität, Operation, Scope,
drei Continuation-Identitäten, das einzelne Mutationsbudget und eine
zeitzonenbehaftete Startzeit.

Alter, Dateiname, Prozessstatus oder vermutete Aufgabe beweist keinen Zustand.

Der Claim wird ausschließlich aus dem vollständigen SHA-256 der vorab
gebundenen Continuation-Claim-ID adressiert; Suche, Prefix und Wildcard sind
verboten.

## Ursprünglicher Claim bleibt erforderlich

Bei offenem Unterclaim muss auch der ursprüngliche LQ-394-Claim vorhanden,
kanonisch und exakt an dieselbe historische Kette gebunden sein.

Fehlen, Beschädigung oder Fremdbindung des ursprünglichen Claims ergibt
`conflict`, sofern die Artefakte technisch lesbar sind.

Eine zwischenzeitliche LQ-398-Finalization-Evidence oder originale
LQ-394-Evidence bei offenem Unterclaim widerspricht dem erwarteten
Unknown-Outcome-Zustand und ergibt ebenfalls `conflict`.

Kein Claim wird freigegeben, übernommen oder ersetzt.

## Exakte read-only Volumebeobachtung

Nur bei fehlender Continuation-Evidence und vollständig gebundenem offenen
Doppelclaim darf Docker read-only erreicht werden.

Der Inspector leitet Projekt- und Volumename ausschließlich aus dem
System-of-Record-Kontext ab.

Zuerst wird eine exakte Namensliste mit verankerter Filterung gelesen.

Ist genau das Volume vorhanden, bestätigt ein einzelnes exaktes Inspect die
rungebundene owner-only Compose-Zuordnung.

Docker-Events, Logs, Historie, Mount, Export, Volumeinhalte und SQL bleiben
unerreichbar.

## Geschlossene Zustandsmatrix

Bei offenem exakt gebundenem Doppelclaim sind nur drei lesbare Zustände
zulässig:

- exakt vorhandenes und korrekt gebundenes Volume ergibt `volume_present`;
- exakt bestätigte Abwesenheit ergibt
  `volume_absent_evidence_missing`;
- vorhandenes, aber fremd oder widersprüchlich gebundenes Volume ergibt
  `conflict`.

`volume_present` beweist weder einen sicheren früheren Misserfolg noch, dass
das Objekt nicht zwischenzeitlich unter demselben Namen ersetzt wurde.

Keiner dieser Ausgänge erlaubt automatisch einen weiteren Remove.

`volume_absent_evidence_missing` bestätigt nur aktuelle lokale Abwesenheit,
nicht die ursprüngliche Prozessantwort oder vollständige Datenentsorgung.

## Technische Nichtverfügbarkeit

Malformed Output, Nonzero, stderr, Timeout, Truncation, Hard Kill, ungültiges
UTF-8, doppelte JSON-Schlüssel oder uneindeutige Namenslisten bleiben
detailfreie technische Nichtverfügbarkeit ohne Ergebnisobjekt.

Unavailable wird nicht als Konflikt, Abwesenheit, Erfolg oder Fortschritt
umgedeutet.

Private Pfade, IDs, Hashes, Dockerantworten und technische Fehlerdetails
verlassen die Grenze nicht.

## Strikte Read-only-Grenze

Erlaubt sind ausschließlich private Dateireads, die exakte Volume-Namensliste
und gegebenenfalls ein exaktes Volume-Inspect.

Claimanlage, Claimfreigabe, Evidencewrite, Volume-Remove, Force, Prune,
Compose-Down, Mount, Export, Container- oder Networkmutation und SQL sind
verboten.

Auch bei bestätigter Abwesenheit bleiben beide Claims unverändert.

Der Inspector startet weder LQ-398 noch LQ-400 und erzeugt keine
Finalization- oder Continuation-Evidence.

## Geschlossene Ausgabe

Der spätere Command darf ausschließlich liefern:

- `continuation_evidence_present`;
- `not_found`;
- `volume_present`;
- `volume_absent_evidence_missing`;
- `conflict`;
- technische Nichtverfügbarkeit ohne Ergebnisobjekt.

Die Ausgabe enthält nur kanonische Schemaversion, feste Operation
`disposable_postgres_volume_deletion_continuation_reconciliation` und den
geschlossenen Ausgang.

Alle privaten Details bleiben verborgen.

## Retention und Nichtwiederverwendung

Continuation-Reconciliation-, Continuation-, Continuation-Claim-,
Finalization-, Reconciliation-, Lösch- und ursprüngliche Claim-ID sowie alle
Autorisierungen, Claims, Evidence und Quellartefakte bleiben mindestens so
lange unterscheidbar, wie Audit, Retry, Reconciliation oder Finalisierung
davon abhängen.

Keine ID, Claimdatei, Evidence oder Volumeidentität darf unter neuer Bindung,
anderem Scope oder neuer Bedeutung wiederverwendet werden.

Volumeabwesenheit, Evidencefund oder Claimfreigabe beendet diese Untergrenze
nicht. Eine konkrete Frist oder Ablageform wird nicht festgelegt.

## Grenzen der Aussage

Alle Ausgänge betreffen ausschließlich den lokalen Zustand des exakten
Docker-Volumeobjekts und der gebundenen privaten Artefakte.

Backups, Exporte, Snapshots, Replikate, Logs und andere Speicherorte besitzen
eigene Retention- und Dispositionsgrenzen.

Der Inspector liefert niemals die Aussage „alle Daten entsorgt“.

## Nichtziele und Bundle

LQ-401 entscheidet keine konkrete JSON-Struktur, Signatur, Exception,
Funktionssignatur, CLI, Docker-argv, Timeout-, Claim- oder
Evidenceimplementierung.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Modell-, Compose-,
Service-, Scheduler-, HTTP-, Monitoring-, Test- oder Production-Wiring-
Änderung.

Der Slice implementiert keinen Inspector, Finalizer, Evidencewriter,
Claimrelease, Continuation oder Volume-Remove.

Bundle-Gates bleiben bei 55 Entry Points, 59 Operatormodulen, 27 Migrationen
und Head `20260819_0027`.

## Nächster Slice

LQ-402 sollte den strikt read-only
Volume-Deletion-Continuation-Claim-Inspector gemäß diesem Vertrag
implementieren.

Fake-basierte Tests müssen Evidencepriorität, neutrale Abwesenheit,
Doppelclaimbindung, exakte Volumeanwesenheit und -abwesenheit, Conflict,
technische Fehler, CLI und vollständige Writefreiheit prüfen.

Claimfinalisierung, erneute Continuation und Freigabe des ursprünglichen
LQ-394-Claims bleiben separate spätere Slices.
