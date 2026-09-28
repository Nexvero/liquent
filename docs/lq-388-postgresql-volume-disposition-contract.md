# LQ-388 — PostgreSQL Volume Disposition Contract

## Zweck

LQ-388 definiert die separate Disposition des nach erfolgreichem Runtime-
Cleanup erhaltenen PostgreSQL-Datenvolumes.

Der Vertrag entscheidet, unter welchen Voraussetzungen ein späterer read-only
Resolver `retain`, `deletion_review_eligible` oder
`investigation_required` feststellen darf.

Dieser Slice implementiert weder Resolver noch Löschoperator und verändert
kein Volume.

## Ausgangslage

Ein ordnungsgemäß abgeschlossener LQ-387-Prozess entfernt Container und Netze,
finalisiert den LQ-339-Cleanup-Claim und erhält das exakte rungebundene
Datenvolume.

Runtime-Cleanup-Evidence ist deshalb eine notwendige Vorgeschichte, aber keine
Volumenlöschautorität.

`runtime_only`, `runtime_removal_finalized`, freigegebene Cleanup-Claims und
Abwesenheit der Runtime dürfen nicht als vollständige Umgebungsentsorgung
umgedeutet werden.

## Eigenständige Authority-Grenze

Volume-Disposition ist von Runtime-Cleanup, Research-Berechtigungen,
Membership, Infrastrukturrollen und Besitz des Dockerkontos getrennt.

Eine allgemeine Admin-, Owner- oder Operatorbezeichnung gewährt keine
Disposition oder Löschbefugnis.

Der spätere Resolver muss Actor, Zielvolume und ursprünglichen Run aus dem
privaten System of Record binden.

Caller-gelieferte Allow-Booleans, gewünschte Outcomes, Ressourcennamen,
Retentionstatus, Backupstatus oder Legal-Hold-Aussagen sind keine Authority.

## Maßgebliche System-of-Record-Fakten

Vor jeder positiven Disposition müssen mindestens bytegenau lesbar und
untereinander konsistent sein:

- ursprüngliche Staging-, Reconciliation- und Claim-Reconciliation-Evidence;
- LQ-334/335-Disposition und ihre gebundene Autorisierung;
- LQ-336-Cleanup-Autorisierung;
- vollständige Runtime-Cleanup-Autorisierungs- und Evidence-Lineage;
- finale LQ-343-Cleanup-Evidence und belegte Freigabe aller Cleanup-Claims;
- unveränderte Run-, Source-, Image-, Compose- und Volumeidentität;
- aktuelle Retentionentscheidung für genau dieses Volume;
- aktuelle Legal-Hold-Entscheidung für genau diesen Datenbestand;
- erforderliche Backup- und Restore-Verifikation;
- getrennte Actor-, Authorizer- und Reviewidentitäten;
- aktuelle UTC-Zeitwerte und bytegenaue SHA-256-Bindungen.

Dateinamen, Dockerlabels, Alter, Kosten, fehlende Runtime oder sichtbare
Volumeabwesenheit ersetzen diese Fakten nicht.

## Unveränderte Volumeidentität

Das Ziel muss das exakte Volume sein, das in der ursprünglichen Runbindung und
in jeder Runtime-Cleanup-Beobachtung erhalten wurde.

Die Identität wird intern aus den autoritativen Artefakten abgeleitet und nicht
als frei wählbarer Name angenommen.

Umbenennung, Labelreparatur, Auswahl per Präfix, Wildcard, Composeprojekt oder
Ähnlichkeit ist unzulässig.

Ein fehlendes, zusätzliches, fremd gebundenes oder abweichend gelabeltes
Volume führt nicht zu Löschbarkeit, sondern zu Untersuchung oder technischer
Nichtverfügbarkeit entsprechend der Evidencequalität.

## Retain als sichere Untergrenze

`retain` ist der normale geschlossene Ausgang, solange nicht sämtliche
strengeren Voraussetzungen für eine Löschprüfung positiv vorliegen.

Retain verändert keine Retentionfrist, erzeugt keinen Backupauftrag und
erlaubt weder Mount noch Export, Restore oder Löschung.

Alter, Inaktivität, Speicherdruck, Kosten oder Abschluss des Runtime-Cleanup
dürfen Retain nicht automatisch überstimmen.

Eine spätere neue Entscheidung benötigt neue aktuelle Authority und darf eine
frühere Retain-Entscheidung nicht überschreiben.

## Retentionfreigabe

Eine positive Löschprüfung verlangt eine ausdrückliche aktuelle
Retentionfreigabe aus dem zuständigen System of Record.

Sie muss genau Run, Volume, Datenklasse, zuständige Policyversion,
Entscheidungs-ID, Authorizer und Gültigkeitsfenster binden.

Abgelaufene, allgemeine, fremde oder nur aus einer Frist berechnete Freigabe
ist nicht ausreichend.

Der Resolver berechnet keine Aufbewahrungsfrist und ergänzt keine fehlende
Policyentscheidung.

Dieser Vertrag legt keine konkrete Frist oder Archivierungsstrategie fest.

## Legal Hold

Legal Hold ist eine eigenständige fail-closed Sperre.

Nur eine aktuelle autoritative Feststellung, dass für genau den gebundenen
Datenbestand kein Hold die Disposition blockiert, kann die Prüfung
fortsetzen.

Schweigen, fehlender Datensatz, unbekannter Zuständigkeitsbereich oder eine
caller-gelieferte Negation beweist keine Hold-Freiheit.

Ein aktiver, widersprüchlicher oder nicht abschließend auflösbarer Hold führt
zu `retain` beziehungsweise `investigation_required`; niemals zu Löschung.

Eine spätere Sperre muss alle noch nicht abgeschlossenen Entscheidungen
widerrufen und bei späteren Entscheidungen wirksam sein.

## Backup- und Restore-Nachweis

Wenn die maßgebliche Retention- oder Recoverypolicy einen Backupnachweis
verlangt, muss dieser für genau den Volumeinhalt vorliegen.

Mindestens zu binden sind Backup-ID, unveränderliche Objektidentität,
Erstellungszeit, Integritätsnachweis, Policyversion und zuständiger Owner.

Wo Restore-Verifikation vorgeschrieben ist, genügt weder erfolgreiche
Backuperstellung noch bloße Lesbarkeit des Backupobjekts.

Die Restore-Evidence muss einen getrennten kontrollierten Restoreversuch,
dessen Integritätsausgang und die Bindung an dasselbe Backup nachweisen.

Backup oder Restore autorisiert für sich keine Volumenlöschung.

LQ-388 startet keinen Export, liest keine Datenbankinhalte und definiert kein
Backupformat, Storageziel oder Restoreverfahren.

## Geschlossene Dispositionen

Ein späterer read-only Resolver darf ausschließlich liefern:

- `retain`;
- `deletion_review_eligible`;
- `investigation_required`;
- technische Nichtverfügbarkeit ohne Ergebnisobjekt.

`deletion_review_eligible` bedeutet nur, dass eine separate owner-only
Löschautorisierung geprüft werden darf.

Kein Dispositionsausgang ist selbst ein Dockeraufruf, Deleteauftrag,
Claimwrite, Mount, Export oder Nachweis vollständiger Entsorgung.

## Voraussetzungen für deletion_review_eligible

Der positive Ausgang ist nur zulässig, wenn gemeinsam gilt:

- Runtime-Cleanup und LQ-343 sind für denselben Run vollständig finalisiert;
- alle Cleanup-Claims sind nach Evidence-first-Finalisierung abwesend;
- die vollständige historische Lineage ist unverändert erhalten;
- das Volume ist exakt und ausschließlich dem ursprünglichen Run gebunden;
- keine spätere Produkt-, Migration-, Restore- oder andere Nutzung existiert;
- die aktuelle Retentionfreigabe umfasst exakt dieses Volume;
- der aktuelle Legal-Hold-Nachweis erlaubt die weitere Prüfung;
- alle policyseitig erforderlichen Backup-/Restore-Nachweise sind positiv;
- keine konkurrierende Disposition oder Löschoperation ist offen;
- Actor, Authorizer und Reviewer sind getrennt und aktiv;
- alle aktuellen Zeitfenster sind positiv und nicht abgelaufen.

Fehlt eine strengere fachliche Voraussetzung, lautet der Ausgang `retain`.

Widerspruch, Fremdbindung oder möglicher konkurrierender Effekt lautet
`investigation_required`.

## Separate spätere Löschautorisierung

Auch `deletion_review_eligible` gewährt keine Mutation.

Ein späterer Vertrag muss eine neue owner-only Autorisierung mit stabiler,
nicht wiederverwendbarer Lösch-ID verlangen.

Sie muss mindestens Dispositions-ID, Run-ID, intern abgeleitete Volumeidentität,
Hashes aller maßgeblichen Evidence, Operation, Actor, Authorizer,
Gültigkeitsfenster und exakten Mutationsumfang binden.

Die Autorisierung darf keinen Wildcard-, Präfix-, Labelgruppen-, Projekt- oder
Hostweiten Umfang zulassen.

Eine neue Autorisierung verlängert keine historische Freigabe und kann einen
zwischenzeitlichen Hold oder Widerruf nicht überstimmen.

## Revocation und erneute Entscheidung

Retentionfreigabe, Hold-Freiheit, Backupstatus und Löschautorisierung müssen
bei jeder späteren Entscheidung erneut aus dem System of Record aufgelöst
werden.

Ein Widerruf oder eine neue Sperre muss alle noch nicht begonnenen
Mutationsentscheidungen fail-closed stoppen.

Bereits ausgegebene positive Dispositionen sind keine dauerhaft nutzbaren
Tokens und dürfen nicht zwischengespeichert als Authority wiederverwendet
werden.

Nach einem möglichen Effekt wird der Zustand ausschließlich über eine
separate Reconciliation geklärt.

## Evidence-first und Unknown Outcome

Ein späterer Löschoperator muss vor dem ersten Effekt einen exklusiven,
run- und volumengebundenen Claim evidence-sicher anlegen.

Nach bestätigter Entfernung muss finale private Evidence atomar geschrieben,
durabel gemacht und bytegenau zurückgelesen werden, bevor der Claim
freigegeben werden darf.

Timeout, Prozessverlust, Hostverlust oder fehlende Ausgabe nach möglichem
Effekt ist Unknown Outcome.

Unknown Outcome darf weder als Erfolg noch als Abwesenheit oder Ablehnung
interpretiert werden und erlaubt keinen Blind-Retry der Löschung.

Der einzige technische Folgeweg ist ein späterer getrennt autorisierter
read-only Inspector; dessen Vertrag und Implementierung sind nicht Teil von
LQ-388.

## Neutrale Ablehnung und technische Nichtverfügbarkeit

`retain` und `investigation_required` sind detailarme Ergebnisobjekte ohne
interne IDs, Pfade, Hashes, Ressourcennamen oder Fehlerdetails.

Fehlende positive fachliche Freigabe kann neutral zu `retain` führen.

Malformed, unlesbare, unsichere, widersprüchlich gehashte oder technisch nicht
auflösbare Authority- und Evidenceobjekte führen detailfrei zu technischer
Nichtverfügbarkeit ohne Ergebnisobjekt.

Technische Nichtverfügbarkeit darf nicht in `retain`,
`investigation_required`, Erfolg oder Abwesenheit umgedeutet werden.

Dieser Vertrag benennt dafür keinen neuen Exceptiontyp.

## Löschungsnachweis und Kommunikationsgrenze

Selbst ein später bestätigtes fehlendes Volume beweist nur die Entfernung des
exakten Volumeobjekts im gebundenen Environment.

Backups, Exporte, Snapshots, Replikate, Logs und historische Evidence besitzen
eigene Retention- und Dispositionsgrenzen.

„Vollständig entsorgt“ darf erst kommuniziert werden, wenn alle dafür
maßgeblichen Datenkopien durch ihre jeweiligen Systeme of Record abgeschlossen
sind.

Öffentliche Ausgaben bleiben auf kanonischen Ausgang, Exitklasse, opaque
Runreferenz und UTC-Zeit begrenzt.

## Retention und Nichtwiederverwendung

Run-, Volume-, Dispositions-, Claim-, Lösch-, Backup-, Restore- und
Legal-Hold-IDs sowie ihre Autorisierungen und Evidence müssen mindestens so
lange eindeutig unterscheidbar bleiben, wie Audit, Widerruf, Reconciliation,
Retry oder Unknown-Outcome-Aufklärung davon abhängen.

Keine ID, Evidence oder Volumeidentität darf unter neuer Bindung oder Bedeutung
wiederverwendet werden.

Löschung des Datenvolumes beendet nicht automatisch die Retention der
Entscheidungs-, Claim- und Löschungsevidence.

Der Vertrag legt keine konkrete Tabelle, Ablageform oder Frist fest.

## Verbotene Abkürzungen

Unzulässig sind insbesondere:

- `docker compose down --volumes`, Prune und gruppenweite Entfernung;
- Auswahl nach Wildcard, Präfix, Labelgruppe oder frei geliefertem Namen;
- manuelles Mounten, Öffnen, SQL-Lesen oder Exportieren als Dispositionsprobe;
- Ableitung von Hold-Freiheit aus Abwesenheit einer Antwort;
- Ableitung von Backupqualität aus Dateiexistenz;
- Löschen oder Reparieren von Claims und Evidence von Hand;
- automatisches Retry, Polling oder Starten eines Löschoperators;
- Wiederverwendung alter Dispositionen nach Widerruf oder Ablauf;
- Kommunikation vollständiger Entsorgung allein aus Volumeabwesenheit.

## Nichtziele und Bundle

LQ-388 entscheidet keine konkrete JSON-Struktur, Signatur, Exception,
Funktionssignatur, CLI, Docker-argv, Timeout-, Claim- oder Evidenceimplementierung.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Modell-, Compose-,
Service-, Scheduler-, HTTP-, Monitoring-, Test- oder Production-Wiring-
Änderung.

Der Slice erstellt kein Backup, keinen Restore, Export, Legal Hold, Resolver,
Inspector, Operator oder Volume-Delete.

Bundle-Gates bleiben bei 49 Entry Points, 53 Operatormodulen, 27 Migrationen
und Head `20260819_0027`.

## Nächster Slice

LQ-389 sollte den strikt read-only PostgreSQL-Volume-Disposition-Resolver
definieren.

Er muss die gebundene Runtime-Abschlusslineage sowie aktuelle Retention-,
Legal-Hold- und erforderliche Backup-/Restore-Fakten aus dem System of Record
auflösen und ausschließlich die geschlossenen detailarmen Ausgänge liefern.

Volume-Mutation, Claimpersistenz und Löschoperator bleiben weiterhin separat.
