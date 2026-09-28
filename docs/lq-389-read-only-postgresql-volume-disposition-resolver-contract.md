# LQ-389 — Read-only PostgreSQL Volume Disposition Resolver Contract

## Zweck

LQ-389 definiert die beobachtbare Grenze eines strikt read-only Resolvers für
die in LQ-388 eingefrorene PostgreSQL-Volume-Disposition.

Der Resolver leitet ausschließlich `retain`, `deletion_review_eligible` oder
`investigation_required` aus aktuellen autoritativen Fakten und der
vollständigen Runtime-Abschlusslineage ab.

Dieser Slice implementiert keinen Resolver, keinen Command, keinen Claim und
keine Volumenmutation.

## Prozesscharakter

Der Resolver ist eine explizit gestartete, kurzlebige Offline-Prüfung.

Er ist kein Service, Scheduler, Queue-Consumer, HTTP-Endpunkt, Deploymenthook
oder automatischer Nachfolger des Runtime-Cleanup.

Ein Aufruf prüft genau eine aktuelle Dispositionsentscheidung für genau einen
gebundenen Run und dessen exaktes Datenvolume.

Kein Ausgang startet selbst einen weiteren Prozess.

## Eigene aktuelle Resolverautorisierung

Jede Entscheidung benötigt eine neue owner-only Resolverautorisierung aus dem
privaten System of Record.

Sie muss mindestens binden:

- stabile nicht wiederverwendbare Resolverentscheidungs-ID;
- ursprüngliche Run-ID und Phase `disposable_postgres`;
- Source-Commit, immutable Image-Referenz und Compose-SHA-256;
- intern abgeleitete Identität des erhaltenen Datenvolumes;
- maßgebliche Runtime-Cleanup- und LQ-343-Abschlussreferenzen;
- bytegenaue Hashes der gebundenen historischen Evidence;
- aktuelle Retention-, Legal-Hold- und Recovery-Entscheidungsreferenzen;
- getrennte Executor-, Authorizer- und Reviewidentitäten;
- Operation ausschließlich Volume-Disposition-Resolution;
- positives aktuelles UTC-Gültigkeitsfenster.

Die Autorisierung enthält keinen gewünschten Ausgang, Delete-Boolean,
Caller-Rollennamen oder frei gelieferten Ressourcennamen.

## Actor- und Targetbindung

Der authentifizierte oder lokale Prozessactor identifiziert nur den
ausführenden Actor und gewährt keine Dispositionsauthority.

Actorstatus, Authorizerstatus, Reviewstatus, ursprünglicher Run und Zielvolume
werden bei der Entscheidung aus ihren autoritativen Quellen aufgelöst.

Inaktive, widerrufene, fehlende oder widersprüchlich gebundene Identitäten
enden fail-closed.

Der Caller darf weder Targetvolume noch Workspace-, Projekt- oder Hostscope
durch einen Allow-Wert oder eine Rolle erweitern.

Eine gewöhnliche Membership, Researchpermission oder Infrastrukturrolle ist
keine Volume-Disposition-Capability.

## Historische Abschlusslineage

Der Resolver muss die vollständige für den konkreten Run tatsächlich
entstandene Autorisierungs- und Evidence-Lineage prüfen.

Mindestens umfasst dies:

- ursprüngliche Staging- und PostgreSQL-Reconciliationkette;
- LQ-334/335-Recovery-Disposition;
- LQ-336-Autorisierung für `runtime_only`;
- initialen Runtime-Cleanup und jede tatsächlich genutzte Continuation;
- alle tatsächlich genutzten Reconciliation- und Finalizationstufen;
- gegebenenfalls die vollständige geordnete Generation-Lineage;
- finale LQ-343-Cleanup-Evidence;
- belegte Abwesenheit des LQ-339-Claims und aller Unterclaims;
- durchgängige Bestätigung des unveränderten Datenvolumes.

Nicht genutzte Continuationstufen dürfen nicht erfunden oder als fehlende
Pflichtdateien behandelt werden.

Die terminale Evidence bestimmt, welche Vorgängerkette vollständig sein muss.

## Bytegenaue und semantische Prüfung

Jedes historische Artefakt wird bytegenau gegen den von seinem autoritativen
Nachfolger gebundenen SHA-256 geprüft.

Run, Phase, Source, Image, Compose, Volume, IDs und Vorgängerbeziehungen müssen
über die gesamte Kette semantisch übereinstimmen.

Historische Autorisierungen werden nur in ihrem damaligen Kontext validiert;
ihre abgelaufenen Zeitfenster werden nicht als aktuelle Authority benutzt.

Die aktuelle Resolverautorisierung und alle aktuellen Clearance-Fakten müssen
zum Entscheidungszeitpunkt positiv gültig sein.

Dateiname, Kopie, spätere Neuformatierung oder ein inhaltlich ähnliches JSON
ersetzt keine bytegenaue Evidence.

## Geschlossene Claimlage

Vor einer Disposition müssen sämtliche Runtime-Cleanup-Claims der gebundenen
Lineage evidence-first finalisiert und abwesend sein.

Ein vorhandener, technisch nicht prüfbarer oder fremd gebundener Claim ist
keine Retain-Begründung und keine Löschgrundlage.

Der Resolver liest keinen Claiminhalt zur Alters- oder Ownerheuristik, löscht
keinen Claim und startet keine Claim-Reconciliation.

Eine offene konkurrierende Volume-Disposition oder Löschoperation sperrt jede
positive Entscheidung.

## Read-only Volumebeobachtung

Der Resolver darf ausschließlich die Metadaten des intern abgeleiteten
Volumeobjekts beobachten, die für Existenz und unveränderte Runbindung
erforderlich sind.

Er mountet oder öffnet das Volume nicht, liest keine PostgreSQL-Datei, führt
kein SQL aus und startet keinen Container.

Er akzeptiert keinen caller-gelieferten Dockerstatus und keine frei gelieferte
Volumeinspektion als System-of-Record-Fakt.

Das exakt vorhandene und unverändert gebundene Volume ist Voraussetzung für
`deletion_review_eligible`.

Abwesenheit ist kein positiver Dispositionsausgang; sie erfordert getrennte
Untersuchung der möglichen früheren Mutation.

## Aktuelle Retentionentscheidung

Die Retentionquelle muss für genau Run, Volume, Datenklasse und Policyversion
eine aktuelle Entscheidung liefern.

Eine positive Clearance muss eine stabile Entscheidungs-ID, zuständigen
Authorizer, Entscheidungszeit und positives Gültigkeitsfenster besitzen.

Fehlende Clearance, noch laufende Frist oder fachlich verlangtes Retain führt
neutral zu `retain`.

Unlesbare, malformed, fremde oder widersprüchliche Retentionevidence ist
technische Nichtverfügbarkeit.

Der Resolver berechnet keine Retentionfrist und interpretiert Alter oder Kosten
nicht als Freigabe.

## Aktuelle Legal-Hold-Entscheidung

Hold-Freiheit muss als ausdrückliche aktuelle Entscheidung für genau denselben
Datenbestand vorliegen.

Ein aktiver Hold führt zu `retain`.

Ein Konflikt zwischen zuständigen Holdquellen, unklarer Scope oder mögliche
spätere Sperre führt zu `investigation_required`.

Schweigen oder Nichtauffinden eines Holddatensatzes ist keine Hold-Freiheit.

Technisch nicht lesbare Authority endet ohne Ergebnisobjekt.

## Backup- und Restore-Fakten

Die maßgebliche Recoverypolicy entscheidet, ob Backup- und gegebenenfalls
Restore-Verifikation für eine Löschprüfung erforderlich sind.

Der Resolver liest nur die autoritativen Status- und Bindungsfakten dieser
bereits abgeschlossenen Prozesse.

Er startet, wiederholt oder repariert weder Backup noch Restore.

Er prüft mindestens Backupobjektidentität, Integritätsausgang,
Policyübereinstimmung und – falls erforderlich – die gebundene positive
Restore-Verifikation.

Eine fehlende fachlich erforderliche positive Verifikation führt zu `retain`.

Widerspruch oder mögliche Fremdbindung führt zu
`investigation_required`; technische Unlesbarkeit bleibt unavailable.

## Revocation zum Entscheidungszeitpunkt

Resolverautorisierung, Actorstatus, Retentionfreigabe, Hold-Freiheit und
Recoverystatus werden bei jedem Aufruf frisch aufgelöst.

Ein früheres positives Resolverergebnis wird nicht als Authority eingelesen
und nicht als dauerhaftes Token behandelt.

Widerruf, Deaktivierung, neue Sperre oder Ablauf muss jede spätere Entscheidung
unmittelbar fail-closed beeinflussen.

Es gibt keinen positiven Cache, Grace Period oder Retry mit eingefrorenem
Vorentscheidungszustand.

## Geschlossene Abbildung

`deletion_review_eligible` ist nur zulässig, wenn gemeinsam gilt:

- aktuelle Resolverauthority und alle beteiligten Identitäten sind gültig;
- Runtime-Cleanup-Lineage und LQ-343-Abschluss sind vollständig gebunden;
- sämtliche Cleanup-Claims und konkurrierenden Operationsclaims fehlen;
- das exakte Volume ist vorhanden und unverändert rungebunden;
- keine spätere Produkt-, Migration-, Restore- oder andere Nutzung besteht;
- aktuelle Retentionclearance ist positiv;
- aktuelle Hold-Freiheit ist positiv;
- alle policyseitig erforderlichen Recoverynachweise sind positiv;
- kein Widerruf, Konflikt oder Unknown Outcome besteht.

Eine vollständig lesbare fachlich negative oder noch nicht positive
Voraussetzung ergibt `retain`.

Aktiver Hold und erforderlicher, noch nicht positiver Backup-/Restorestatus
sind insbesondere Retain-Fälle.

Widersprüchliche autoritative Fakten, Fremdbindung, Volumeabwesenheit oder
möglicher konkurrierender Effekt ergeben `investigation_required`.

## Bedeutung von deletion_review_eligible

Der positive Ausgang gewährt ausschließlich die Möglichkeit, eine getrennte
owner-only Löschautorisierung zu prüfen.

Er ist kein Delete-, Docker-, Mount-, Export-, Claim- oder Backupauftrag.

Er darf nicht direkt an einen Löschoperator weitergereicht werden, ohne die
aktuellen System-of-Record-Fakten und Revocations erneut zu prüfen.

Er bestätigt weder physische Löschung noch vollständige Datenentsorgung.

## Technische Nichtverfügbarkeit

Unsichere Dateitypen oder Rechte, Hashabweichung, malformed Evidence,
unauflösbare Authority, I/O-Fehler und technisch unbekannter Quellzustand
enden detailfrei ohne Ergebnisobjekt.

Technische Nichtverfügbarkeit ist nicht `retain`,
`investigation_required`, Abwesenheit oder Ablehnung.

Sie darf nicht durch Fallbackwerte, breitere Rechte, alternative Dateien oder
caller-gelieferte Behauptungen repariert werden.

Der Vertrag benennt keinen neuen Exceptiontyp.

## Detailarme beobachtbare Ausgabe

Ein erfolgreicher späterer Resolver gibt ausschließlich aus:

- kanonische Schemaversion;
- feste Operation für PostgreSQL-Volume-Disposition;
- genau einen der Ausgänge `retain`, `deletion_review_eligible` oder
  `investigation_required`.

Run-, Volume-, Evidence-, Claim-, Backup-, Restore-, Hold-, Identitäts-, Hash-,
Zeit- und Pfaddetails bleiben privat.

Technische Nichtverfügbarkeit liefert kein Ergebnisobjekt und keine internen
Fehlerdetails.

Exitcode, API- oder Funktionssignatur werden in diesem Slice nicht festgelegt.

## Keine Writes und keine Seiteneffekte

Der Resolver schreibt keine Dispositionsevidence, Claims, Lockdateien,
Marker, Retention- oder Holdentscheidungen.

Er ändert keine Rechte, Labels, Ressourcennamen oder Autorisierungen.

Er führt kein Volume-Remove, Compose-Down, Prune, Backup, Restore, Export oder
Cleanup aus.

Monitoring, Auditlogging und ein späterer persistenter Entscheidungsnachweis
bleiben außerhalb dieser read-only Grenze.

## Konkurrenz und TOCTOU-Grenze

Die read-only Entscheidung kann die spätere Löschmutation nicht atomar gegen
neue Holds, Revocations oder konkurrierende Nutzung schützen.

Darum muss eine spätere Löschautorisierungs- und Preflightgrenze sämtliche
aktuellen Fakten erneut prüfen und einen eigenen exklusiven Claim vorsehen.

Ein positives Resolverergebnis darf nicht als Beweis fortdauernder
Löschbarkeit verwendet werden.

LQ-389 entscheidet keine Lock-, Transaktions- oder Claimimplementierung.

## Retention und Nichtwiederverwendung

Resolverentscheidungs-ID, gebundene Quellentscheidungen, historische Lineage
und ihre Hashbeziehungen müssen mindestens so lange unterscheidbar bleiben,
wie Audit, Widerruf, Löschprüfung oder Unknown-Outcome-Aufklärung davon
abhängen.

Keine ID oder Evidence darf unter neuer Bindung oder Bedeutung wiederverwendet
werden.

Eine spätere neue Entscheidung erhält eine neue ID und ersetzt keine frühere
Evidence.

Dieser Vertrag legt keine konkrete Frist, Tabelle oder Ablageform fest.

## Nichtziele und Bundle

LQ-389 entscheidet keine konkrete JSON-Eingabestruktur, Signatur, Exception,
Funktionssignatur, CLI, Docker-argv, Timeout-, Port-, Modell- oder
Persistenzimplementierung.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Compose-, Service-,
Scheduler-, HTTP-, Monitoring-, Test- oder Production-Wiring-Änderung.

Der Slice implementiert keinen Resolver, Autorisierungsgenerator,
Retentiondienst, Holdsystem, Backup-/Restoreprozess, Claim oder Operator.

Bundle-Gates bleiben bei 49 Entry Points, 53 Operatormodulen, 27 Migrationen
und Head `20260819_0027`.

## Nächster Slice

LQ-390 sollte den strikt read-only Volume-Disposition-Resolver gemäß diesem
Vertrag als lokale Operatorgrenze implementieren.

Die Implementierung muss geschlossene Eingaben, private Evidenceprüfung,
aktuelle Revocationauflösung und detailarme Ausgänge testen, ohne Claims,
Volumeinhalte oder Ressourcen zu verändern.
