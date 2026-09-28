# LQ-391 — Owner-only PostgreSQL Volume Deletion Authorization and Preflight Contract

## Zweck

LQ-391 definiert die separate owner-only Autorisierung und den strikt
read-only Preflight vor einer möglichen Entfernung des in LQ-390 geprüften
PostgreSQL-Datenvolumes.

Der Vertrag schließt die Authority- und TOCTOU-Lücke zwischen
`deletion_review_eligible` und einer späteren destruktiven Operation.

Dieser Slice implementiert keinen Preflight, Claim, Inspector oder
Löschoperator und verändert kein Volume.

## Keine Autoritätsvererbung

Ein LQ-390-Ausgang ist eine aktuelle read-only Eignungsaussage, aber kein
Delete-Ticket und kein dauerhaft nutzbares Capability-Token.

Runtime-Cleanup-Autorisierungen, frühere Dispositionen, Dockerzugriff,
Membership, Researchpermission, SessionPrincipal und allgemeine Owner- oder
Administratorrollen gewähren keine Volumenlöschautorität.

Die Löschprüfung benötigt eine neue owner-only Autorisierung mit eigener
stabiler, nicht wiederverwendbarer Lösch-ID.

Caller-gelieferte Allow-Booleans, gewünschte Ausgänge, Gründe oder
Ressourcennamen sind keine Authority.

## Getrennte Verantwortungen

Mindestens folgende Verantwortungen bleiben unterscheidbar:

- der Executor des späteren Preflight;
- der Authorizer der Löschoperation;
- der unabhängige Reviewer der destruktiven Entscheidung;
- die zuständigen Retention-, Legal-Hold- und Recovery-Authorizer;
- der Incident Owner für Unknown Outcome;
- der Evidence-Retention Owner.

Executor, Löschauthorizer und Reviewer müssen verschiedene aktive Identitäten
sein.

Die drei fachlichen Clearance-Authorizer bleiben ebenfalls untereinander und
von diesen Identitäten getrennt.

Besitz eines Prozesskontos ersetzt keine dieser Entscheidungen.

## Geschlossene Löschautorisierung

Eine spätere Löschautorisierung muss mindestens exakt binden:

- Schemaversion und stabile Volume-Deletion-ID;
- ursprüngliche Run-ID und Phase `disposable_postgres`;
- Source-Commit, immutable Image-Referenz und Compose-SHA-256;
- intern abgeleitete exakte Volumeidentität;
- LQ-390-Resolverautorisierung und deren bytegenauen SHA-256;
- gebundenes Lineage-Manifest und dessen bytegenauen SHA-256;
- aktuelle Retention-, Legal-Hold- und Recoveryentscheidungen samt Hashes;
- stabile IDs aller vier aktuellen Entscheidungen;
- Operation exakt Entfernung eines disposable PostgreSQL-Datenvolumes;
- Scope exakt `data_volume_only`;
- stabile nicht wiederverwendbare Claim-ID für den späteren Versuch;
- getrennte Executor-, Authorizer- und Revieweridentitäten;
- positives aktuelles UTC-Fenster von höchstens einer Stunde.

Unbekannte Felder, doppelte Schlüssel, mutable Images, gleiche Identitäten,
stale Zeit oder Hashabweichung sind technische Nichtverfügbarkeit.

## Exakter Scope

Der einzige zulässige Scope ist `data_volume_only`.

Er umfasst genau das aus dem gebundenen Run intern abgeleitete
PostgreSQL-Datenvolume.

Container, Netze, andere Volumes, Backups, Exporte, Snapshots, Images,
Evidence und Claims gehören nicht zum Mutationsbudget.

Der Scope darf nicht über CLI-Option, Prefix, Wildcard, Labelgruppe,
Composeprojekt oder Hostauswahl erweitert werden.

Eine Autorisierung für Runtime-Cleanup darf nicht hochgestuft oder mit dieser
Operation zusammengelegt werden.

## Aktuelle statt gespeicherte Resolverentscheidung

Der Preflight muss den LQ-390-Resolver mit denselben bytegenau gebundenen
System-of-Record-Dateien frisch ausführen.

Nur ein aktuell erneut ermitteltes `deletion_review_eligible` kann die weitere
Prüfung erreichen.

Ein gespeicherter stdout-Wert, Tickettext, früheres Ergebnisobjekt oder
caller-gelieferter Ausgang ist unzulässig.

`retain` ergibt eine neutrale Ablehnung ohne Mutation.

`investigation_required` stoppt für Untersuchung.

Technische Nichtverfügbarkeit bleibt detailfrei unavailable und darf nicht in
Ablehnung oder Erfolg umgedeutet werden.

## Erneute Authority- und Revocationauflösung

Der Preflight lädt bei jedem Aufruf erneut:

- aktuelle Löschautorisierung und Identitätsstatus;
- aktuelles Lineage-Manifest und alle referenzierten Artefakte;
- aktuelle Retentionclearance;
- aktuelle Legal-Hold-Entscheidung;
- aktuelle Recoverypolicy sowie Backup-/Restorestatus;
- aktuelle Claimlage;
- aktuelle read-only Volumeidentität.

Widerruf, Deaktivierung, neuer Hold, Retentionänderung, Recoveryregression oder
Ablauf muss jede spätere Entscheidung fail-closed beeinflussen.

Es gibt keinen positiven Cache, keine Grace Period und keinen Retry mit
eingefrorenen Vorentscheidungsfakten.

## Vollständige Lineagebindung

Die in LQ-390 geprüfte tatsächliche Runtime-Abschlusslineage bleibt vollständig
und bytegenau gebunden.

Der Preflight prüft erneut mindestens Staging-Evidence,
Recovery-Disposition, Runtime-Cleanup-Autorisierung, jede tatsächlich genutzte
Continuation- und Finalizationstufe sowie finale LQ-343-Evidence.

Nicht genutzte Stufen werden nicht erfunden.

Jede ID-, Hash-, Run-, Source-, Image-, Compose- oder Volumeabweichung endet
technisch unavailable oder bei vollständig lesbarer Fremdbindung als
`rejected` gemäß der späteren geschlossenen Abbildung.

Historische Autorisierungen werden nicht verlängert; sie beweisen nur ihre
damalige gebundene Reihenfolge.

## Aktuelle Retentionclearance

Retention muss für genau Run, Datenklasse, Policyversion und Zielvolume
weiterhin ausdrücklich `cleared` sein.

`retain`, noch laufende Frist oder eine vollständig lesbare neue
Retentionentscheidung ohne Freigabe ergibt `rejected`.

Fehlender Datensatz, beschädigte Datei, Hashabweichung oder technisch nicht
auflösbare Policyauthority ist unavailable.

Alter, Kosten, Größe oder Runtimeabwesenheit ersetzen keine Clearance.

Der Preflight berechnet keine Frist und ändert keine Retentionentscheidung.

## Aktuelle Legal-Hold-Freiheit

Hold-Freiheit muss aktuell und ausdrücklich für denselben gebundenen
Datenbestand vorliegen.

Ein aktiver Hold ergibt `rejected`.

Konflikt, mögliche Fremdbindung oder widersprüchliche zuständige Holdquellen
ergeben `investigation_required`.

Schweigen oder fehlender Hold-Datensatz beweist keine Hold-Freiheit und ist
technische Nichtverfügbarkeit.

Der Preflight erzeugt, löst oder repariert keinen Legal Hold.

## Aktuelle Recoverynachweise

Die aktuelle Recoverypolicy bestimmt weiterhin, ob Backup und Restore-
Verifikation erforderlich sind.

Erforderliches Backup muss an dieselbe stabile Backup-ID und denselben
Integritäts-SHA-256 gebunden positiv `verified` sein.

Erforderlicher Restore muss an dieselbe stabile Restore-ID gebunden positiv
`verified` sein.

`pending`, widerrufen, abgelaufen oder fachlich nicht mehr positiv ergibt
`rejected`.

Widerspruch, Fremdbindung oder möglicher Ersatz des Backupobjekts ergibt
`investigation_required`.

Technisch unlesbare Recoveryevidence bleibt unavailable.

Der Preflight startet weder Backup noch Restore und liest keine
PostgreSQL-Inhalte.

## Claimfreiheit vor dem Preflight

Vor jeder positiven Preflightentscheidung müssen alle historischen
Runtime-Cleanup-Claims und jeder Volume-Deletion-Claim fehlen.

Ein sichtbarer erwarteter oder fremd gebundener Claim ist technische
Nichtverfügbarkeit und sperrt die Entscheidung.

Der Preflight liest keinen Claiminhalt zur Altersheuristik, löscht keinen Claim
und startet keine Claim-Reconciliation.

Claimabwesenheit ist keine Löschauthority; sie beweist nur, dass keine bekannte
konkurrierende Operation offen ist.

## Vorab gebundene Claimidentität

Die Löschautorisierung muss die spätere exakte Claim-ID bereits vor dem
Preflight binden.

Der Claimname und seine Bindung werden ausschließlich aus Lösch-ID, Run,
Volume, Autorisierungshash und Operation abgeleitet.

Der Preflight erzeugt diesen Claim noch nicht.

Nur der spätere mutierende Operator darf ihn owner-only per exklusiver
Neuanlage vor dem ersten möglichen Effekt schreiben und durable machen.

Damit können Preflight und Claimanlage nicht als scheinbar atomare
read-only Operation vermischt werden.

Eine Kollision oder vorhandene Claimdatei erlaubt weder Ersatz-ID noch
Überschreiben.

## Exakte read-only Volumebeobachtung

Nach vollständiger Authority-, Evidence- und Claimprüfung darf der Preflight
genau das intern abgeleitete Volume read-only inspizieren.

Das Volume muss vorhanden sein und weiterhin ausschließlich die erwartete
Run- und Composebindung tragen.

Der Preflight mountet oder öffnet das Volume nicht, liest keine Datei, führt
kein SQL aus und startet keinen Container.

Abwesenheit ergibt `investigation_required`, weil eine mögliche frühere
Mutation nicht als neutraler Erfolg behandelt werden darf.

Fremde, zusätzliche oder widersprüchliche Bindung ergibt ebenfalls
`investigation_required`.

Dockerfehler, Timeout, Truncation oder malformed Output ist technische
Nichtverfügbarkeit.

## Geschlossene Preflightausgänge

Ein späterer Command darf ausschließlich liefern:

- `ready`;
- `rejected`;
- `investigation_required`;
- technische Nichtverfügbarkeit ohne Ergebnisobjekt.

`ready` verlangt gemeinsam:

- aktuelle gültige Löschautorisierung;
- drei getrennte aktive Executor-/Authorizer-/Revieweridentitäten;
- frisch erneut ermitteltes `deletion_review_eligible`;
- unveränderte vollständige Lineage und Hashbindung;
- weiterhin positive Retention-, Hold- und Recoveryfakten;
- Abwesenheit aller historischen und künftigen Operationsclaims;
- vorhandenes exakt rungebundenes Zielvolume;
- keine spätere Nutzung, Revocation oder konkurrierende Operation.

`ready` erzeugt keinen Claim und autorisiert keinen Effekt ohne erneute
vollständige Prüfung im mutierenden Operator.

## Neutrale und technische Grenzen

Vollständig lesbare fachliche Ablehnung ergibt `rejected`.

Widerspruch, fremde Bindung, Volumeabwesenheit oder möglicher konkurrierender
Effekt ergibt `investigation_required`.

Malformed oder technisch unlesbare Authority und Evidence, unsichere
Dateirechte, I/O-Fehler sowie mehrdeutige Prozessausgänge enden detailfrei ohne
Ergebnisobjekt.

Technische Nichtverfügbarkeit ist weder `rejected` noch
`investigation_required`, Abwesenheit oder Erfolg.

Dieser Vertrag benennt keinen neuen Exceptiontyp.

## Detailarme Ausgabe

Eine spätere CLI-Ausgabe enthält ausschließlich kanonische Schemaversion,
feste Preflightoperation und einen geschlossenen Ausgang.

Run-, Volume-, Claim-, Evidence-, Retention-, Hold-, Recovery-, Identitäts-,
Hash-, Zeit- und Pfaddetails bleiben privat.

Technische Nichtverfügbarkeit liefert keine internen Fehlerdetails.

Konkreter Entry-Point-Name, Argumentliste, Exitcode und Funktionssignatur
werden in diesem Slice nicht festgelegt.

## Anforderungen an den späteren Löschoperator

Der spätere Operator muss dieselbe Löschautorisierung und sämtliche aktuellen
Fakten unmittelbar vor dem ersten Effekt erneut vollständig validieren.

Er darf keine caller-gelieferte oder gespeicherte `ready`-Antwort akzeptieren.

Er muss den vorab gebundenen Claim exklusiv und durable anlegen, bevor er genau
einen Volume-Remove versucht.

Nach Claimanlage darf nur das intern abgeleitete exakte Volume adressiert
werden.

Compose-Down, `--volumes`, Prune, Wildcard-, Prefix-, Labelgruppen- und
Hostcleanup bleiben verboten.

## Unknown Outcome und Evidence-first

Nach dem ersten möglichen Volumeeffekt ist Timeout, Prozessverlust,
Hostverlust oder fehlende eindeutige Ausgabe Unknown Outcome.

Der Claim und sämtliche Eingabeartefakte bleiben unverändert erhalten.

Blind-Retry des Remove, manuelles Nachlöschen, Claimlöschung und Annahme von
Abwesenheit als Erfolg sind verboten.

Der einzige technische Folgeweg ist ein separater owner-only read-only
Inspector mit eigener aktueller Autorisierung.

Bestätigte Entfernung benötigt später finale private Evidence per exklusiver
Anlage, durablem Write und bytegenauer Rücklesung vor Claimfreigabe.

LQ-391 implementiert weder Inspector noch Finalizer.

## Retention und Nichtwiederverwendung

Run-, Volume-, Resolver-, Retention-, Hold-, Recovery-, Lösch- und Claim-IDs
sowie sämtliche Autorisierungen und Evidence müssen mindestens so lange
unterscheidbar bleiben, wie Audit, Widerruf, Löschung, Reconciliation,
Evidence-Retry oder Unknown-Outcome-Aufklärung davon abhängen.

Keine ID, Evidence oder Volumeidentität darf unter neuer Bindung, anderem Scope
oder neuer Bedeutung wiederverwendet werden.

Volumeabwesenheit oder Claimfreigabe beendet die Evidence-Retention nicht.

Dieser Vertrag legt keine konkrete Frist, Tabelle oder Ablageform fest.

## Nichtziele und Bundle

LQ-391 entscheidet keine konkrete JSON-Struktur, Signatur, Exception,
Funktionssignatur, CLI, Docker-argv, Timeout-, Claimdatei- oder
Evidenceimplementierung.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Modell-, Compose-,
Service-, Scheduler-, HTTP-, Monitoring-, Test- oder Production-Wiring-
Änderung.

Der Slice implementiert keinen Autorisierungsgenerator, Preflight, Claim,
Inspector, Finalizer oder Volume-Remove.

Bundle-Gates bleiben bei 50 Entry Points, 54 Operatormodulen, 27 Migrationen
und Head `20260819_0027`.

## Nächster Slice

LQ-392 sollte den strikt read-only PostgreSQL-Volume-Deletion-Preflight gemäß
diesem Vertrag implementieren.

Er muss die aktuelle LQ-390-Auflösung erneut ausführen, Löschauthority,
Revocations, Lineage, Claimfreiheit und exakte Volumeidentität prüfen und nur
die geschlossenen detailarmen Ausgänge liefern.

Claimanlage und Volume-Remove bleiben weiterhin unimplementiert.
