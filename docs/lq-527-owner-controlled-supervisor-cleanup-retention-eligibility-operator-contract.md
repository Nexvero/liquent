# LQ-527 — Owner-controlled Supervisor Cleanup Retention-Eligibility Operator Contract

## Ergebnis

LQ-527 definiert die owner-kontrollierte Prozessgrenze, über die eine
autoritative Retentionpolicy später genau eine Cleanup-Retentionentscheidung
für ein bekanntes Supervisor-Control-Directory erzeugen darf.

Der Slice implementiert noch keinen Operator und erfindet keine Policyquelle.

## Ausgangslage

LQ-492 definiert die geschlossenen Dispositionen `retain` und `eligible`.

LQ-494 kann eine vollständig gebundene Decision append-only persistieren und
die aktuelle Decision lesen.

Es fehlt weiterhin die autoritative Quelle, welche die Retentionpolicy und
ihre aktuellen Eingabefakten auswertet.

Ein Operator darf diese Lücke nicht durch eine manuelle Alloweingabe schließen.

## Separater Prozess

Die spätere Grenze ist ein eigener ausdrücklich gestarteter, kurzlebiger
owner-kontrollierter Prozess.

Sie ist von Authority-Set-, Quellrevision-, Retirement- und Cleanupoperatoren
getrennt.

Ein Prozess verarbeitet genau einen Request und beendet sich anschließend.

## Minimaler Request

Der Request trägt ausschließlich eine stabile Operation-ID und eine interne
Control-Directory-ID.

Die Operation-ID ist keine Decision-ID, Policyrevision oder Authority.

Der Request enthält weder Retired-Wert noch Handle, Leaf, Root, Pfad,
Datenklasse, Zeitpunkt oder Dateisystemfakt.

## Keine caller-gelieferte Entscheidung

Der Request enthält insbesondere kein `eligible`, `retain`, `disposition`,
`allow`, Boolean, Alter, TTL, Fristdatum oder Rollenfeld.

Er enthält keine caller-gelieferte Policyrevision.

CLI-Flags und Environmentwerte dürfen diese ausgeschlossenen Felder nicht
ersetzen.

Der Process Owner darf die fachliche Policyentscheidung nicht über die
Prozessgrenze behaupten.

## Autoritative Policyquelle

Eine spätere systemeigene Evaluationsgrenze löst für die Directory-ID die
aktuell wirksame Retentionpolicy und alle von ihr benötigten Fakten auf.

Sie liefert eine geschlossene Evaluation oder neutrale Abwesenheit, niemals
einen freien Mapping-, Rollen- oder Allowwert.

Die konkrete Policyquelle, ihr Administrationsweg und ihre Persistenz werden
in LQ-527 nicht festgelegt.

Ohne verfügbare autoritative Policyquelle bleibt der Operator technisch
nicht verfügbar; er fällt nicht auf lokale Regeln zurück.

## Policyrevision

Die Evaluation bindet eine stabile, nichtleere Revision der tatsächlich
ausgewerteten Policy.

Die Revision stammt aus der Policyquelle und nicht aus dem Request.

Ein späterer Policywechsel muss bei einer späteren Operation sichtbar werden.

Eine alte positive Evaluation ist keine Berechtigung für eine neue Decision.

## Datenklassenbindung

Die Policyevaluation muss ausdrücklich die Datenklasse des
Supervisor-Control-Directories und alle von ihr erfassten Control-Artefakte
binden.

Eine Freigabe für eine andere Datenklasse, einen anderen Scope oder ein
anderes Ziel darf nicht übernommen werden.

LQ-527 legt keine offene Datenklassenzeichenkette im Operatorrequest fest.

## System-of-Record-Ziel

Der Operator löst die Directory-ID aktuell aus der persistenten Registry auf.

Nur ein vollständig rekonstruierter, unverändert gebundener Retired-Wert darf
an die Policyevaluation weitergereicht werden.

Unbekannte Directory-ID ist neutrale Abwesenheit.

Reserved, Active, widersprüchliche oder beschädigte Lifecyclefakten sind keine
Retentionfreigabe.

## Retired bleibt nur Voraussetzung

Retired allein erzeugt weder `eligible` noch `retain`.

`retired_at`, Prozessende, Journalterminalität, Dateizeit, Directorygröße oder
freier Speicher werden im Operator nicht als Policy ausgewertet.

Der Operator besitzt keine eingebaute Defaultfrist.

## Aktuelle Faktenermittlung

Die Policyquelle liest ihre benötigten aktuellen Retention-, Legal-, Audit-,
Incident-, Recovery- und Referenzfakten aus ihren Systemen of Record.

Unbekannte oder technisch unlesbare Pflichtfakten dürfen nicht positiv
normalisiert werden.

LQ-527 behauptet nicht, dass die bereits getrennten Cleanup-Hold-, Recovery-
und Referencequellen allein eine vollständige Retentionpolicy bilden.

Diese Quellen werden vor physischer Wirkung weiterhin separat revalidiert.

## Geschlossene Evaluation

Die Evaluation liefert ausschließlich `retain` oder `eligible` zusammen mit
Policyrevision, exakter Retired-Bindung und einem systemeigenen
Evaluationszeitpunkt.

`retain` ist ein autoritativer positiver Aufbewahrungsentscheid und kein
technischer Fehler.

`eligible` ist nur ein Retentionfakt und keine Actor-, Cleanup- oder
Dateisystemauthority.

## Decision-Erzeugung

Erst nach erfolgreicher Evaluation wird eine neue stabile Decision-ID intern
erzeugt und ein bestehender LQ-492-Decisionwert konstruiert.

Der Evaluationszeitpunkt wird nicht durch die Prozesswallclock ersetzt.

Der Decisionwert muss Directory, Handle und Leaf exakt aus demselben
aufgelösten Retired-Wert tragen.

Der LQ-494-Adapter prüft diese Retiredbindung beim Append erneut.

## Operation-Idempotenz

Die Operation-ID benötigt vor einer Implementation eine dauerhafte
nichtwiederverwendbare Bindung an Directory, Evaluation und resultierende
Decision-ID.

Eine exakte Wiederholung muss dasselbe Ergebnis liefern, ohne die Policy ein
zweites Mal als neue Decision zu materialisieren.

Dieselbe Operation-ID mit anderer Directorybindung wird detailfrei abgelehnt.

Die bestehende Decision-ID-Idempotenz allein genügt nicht, weil die Decision-ID
nicht caller-geliefert werden darf.

## Crashsicherer Ergebnishandoff

Die spätere Implementation muss die Operation-/Decisionbindung dauerhaft
sichern, bevor ein Prozessverlust das Ergebnis unauffindbar machen kann.

Eine private Ergebnisdatei ist zusätzlich atomar und owner-only zu schreiben,
ersetzt aber nicht die persistente Operationbindung.

Ein Crash nach Decisionappend darf keinen zweiten Policyentscheid mit neuer
Decision-ID erzeugen.

Die konkrete Foundation für diese Bindung folgt separat.

## Private Konfiguration

Der spätere Prozess erhält Datenbank- und Policyquellenkonfiguration nur über
explizite private Dateien.

Dateien sind descriptorgebunden, no-follow, owner-only, single-link,
größenbegrenzt und strikt UTF-8 zu lesen.

Es gibt keinen Environmentfallback, keine Secretargumente und keine
interaktive Eingabe.

## Geschlossene Ergebnisse

Ein Erfolg gibt ausschließlich Operation-ID, Directory-ID, Decision-ID,
Policyrevision und die geschlossene Disposition aus.

Neutrale Abwesenheit oder fachliche Ablehnung wird detailfrei als `rejected`
klassifiziert.

Eine autoritative `retain`-Evaluation ist erfolgreicher Decisionappend und
wird nicht als Ablehnung oder technische Unverfügbarkeit versteckt.

Technische Nichtverfügbarkeit wird getrennt und detailfrei als
`operator_unavailable` ausgegeben.

LQ-527 benennt keinen neuen Exceptiontyp.

## Keine Sessionauthority

Der Retentionprozess verlangt keinen `SessionPrincipal` und leitet aus einer
Session keine Policyauthority ab.

Ownerkontrolle ist eine Deployment- und Runbookgrenze, keine fachliche Rolle
im Request.

Falls eine spätere Policyadministration Actorprovenienz verlangt, ist sie eine
separate Authority- und Persistenzentscheidung.

## Keine Folgeaktion

Das Persistieren von `retain` oder `eligible` startet keine Clearance, keinen
Cleanup-Attempt und keine physische Dateiwirkung.

Es mutiert keine Management-, Hold-, Recovery- oder Referencequelle.

Es retirert kein Directory und ruft keinen anderen Operator auf.

## Keine Discovery oder Automatik

Die Grenze listet oder sucht keine Directories, Policies, Decisions oder
Retentionkandidaten.

Sie besitzt kein Batch, keine Schleife, Queue, Worker, Scheduler, TTL, Cron,
Startup-, Shutdown- oder Backgroundausführung.

Jede Operation benötigt eine bekannte Directory-ID und einen ausdrücklichen
Aufruf.

## Keine lokale Policyabkürzung

Die Operatorimplementation darf nicht lediglich `now - retired_at`, mtime,
Directorygröße oder Festplattenfüllstand berechnen.

Sie darf keine fehlenden Holds, Recoveryfakten oder Referenzen als frei
interpretieren.

Testfixtures oder manuelles SQL sind keine Productionpolicyquelle.

## Keine Implementation in LQ-527

Dieser Slice ergänzt keinen Entry Point, Operator, Policyadapter,
Operationstore, Domainwert, Port, Tabelle, SQL oder Migration.

Appfactory, HTTP, Compose, Deployment und Runbooks bleiben unverändert.

Das Paketinventar bleibt bei 63 Entry Points und 68 Operatorfiles.

Head bleibt `20260826_0040` mit 40 linearen Migrationen.

## Tests

Statische Vertragstests prüfen den minimalen Request, das Verbot einer
caller-gelieferten Disposition, aktuelle systemeigene Policyevaluation,
Retiredbindung, Operation-Idempotenz, crashsicheren Handoff, geschlossene
Ergebnisse und fehlende Folgeaktion.

Sie behaupten keine Policyimplementation oder PostgreSQL-Evidence.

## Nächster Slice

LQ-528 definiert die geschlossenen Retention-Policy-Evaluationswerte, den
minimalen read-only Evaluationsport und die persistente Operationbindung.

Policyadministration, Operatorimplementation, Retirement, Deployment und
verpflichtende PostgreSQL-Evidence bleiben getrennt.
