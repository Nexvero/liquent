# LQ-528 — Supervisor Cleanup Retention Evaluation and Operation Foundation

## Ergebnis

LQ-528 implementiert geschlossene Retention-Evaluationswerte, einen minimalen
read-only Policyport, einen minimalen Operationstore-Port und die persistente
nichtwiederverwendbare Operationfoundation aus LQ-527.

Der Slice implementiert weder Policyadapter noch Storeadapter oder Operator.

## Stabile Operation-ID

`ManifestHandoffSupervisorCleanupRetentionOperationId` ist eine stabile,
nichtleere und repr-freie interne Identität.

Sie ist weder Decision-ID noch Cleanup-Attempt-ID oder Policyrevision.

Eine Operation-ID darf dauerhaft nur ein Directory und genau eine
resultierende Decision binden.

## Minimaler Evaluationsrequest

`EvaluateManifestHandoffSupervisorControlDirectoryRetention` trägt exakt
Operation-ID und interne Directory-ID.

Der Request enthält keine Disposition, Policyrevision, Datenklasse,
Retiredprojektion, Zeit, Rolle, Session oder Alloweingabe.

Er trägt weder Handle, Leaf, Root noch Pfad.

## Geschlossene Datenklasse

`ManifestHandoffSupervisorCleanupRetentionDataClass` enthält ausschließlich
`supervisor_control_directory`.

Die Datenklasse wird von der Policyquelle geliefert und ist kein freier
Requeststring.

Andere Datenklassen benötigen spätere ausdrücklich geschlossene Werte.

## Evaluation

`EvaluatedManifestHandoffSupervisorControlDirectoryRetention` bindet Request,
vollständigen Retired-Wert, Datenklasse, Policyrevision, geschlossene
Disposition und aware UTC Evaluationszeit.

Die Directory-ID des Requests muss exakt der Retired-Bindung entsprechen.

Die Evaluationszeit darf nicht vor `retired_at` liegen.

## Geschlossene Disposition

Die Evaluation verwendet den bestehenden LQ-492-Enum mit ausschließlich
`retain` und `eligible`.

Es entsteht kein zweiter Retentionstatus und kein Booleanalias.

`eligible` bleibt ein Retentionfakt ohne Actor- oder Cleanupauthority.

## Decision-Bindungscommand

`BindManifestHandoffSupervisorControlDirectoryRetentionDecision` trägt exakt
die vollständige Evaluation und eine intern erzeugte Decision-ID.

Der Command enthält keinen Actor und keine nachträglich veränderte
Disposition.

Die spätere Storeimplementation muss aus diesen Fakten den bestehenden
LQ-492-Decisionwert erzeugen.

## Gebundenes Ergebnis

`BoundManifestHandoffSupervisorControlDirectoryRetentionDecision` bindet die
vollständige Evaluation und den bestehenden Cleanup-Decisionwert.

Retired-Wert, Policyrevision, Disposition und Decisionzeit müssen exakt der
Evaluation entsprechen.

Die Operation-ID wird ausschließlich aus dem ursprünglichen Request
projiziert.

## Detailfreier Konflikt

`ManifestHandoffSupervisorCleanupRetentionOperationConflict` ist feldlos.

Er vereinheitlicht wiederverwendete, divergente, stale oder inkompatible
Operationbindungen ohne interne Details.

Er ist kein technischer Exceptiontyp.

## Read-only Policyport

`ManifestHandoffSupervisorCleanupRetentionPolicyEvaluation` besitzt genau
`evaluate_control_directory_retention`.

Die Methode akzeptiert den minimalen Request und einen aktuell vollständig
aufgelösten Retired-Wert.

Sie liefert eine geschlossene Evaluation oder neutral `None`.

Der Port besitzt keine Policyadministration, Mutation, Liste oder
caller-gelieferte Disposition.

## Operationstore-Port

`ManifestHandoffSupervisorCleanupRetentionOperationStore` besitzt genau
`bind_control_directory_retention_decision`.

Die Methode akzeptiert ausschließlich den geschlossenen Bindungscommand.

Sie liefert Bound, detailfreien Conflict oder neutral `None`.

Die spätere Implementation muss Decisionappend und Operationbindung in einer
Transaktion ausführen.

## Revision 0041

Die additive Revision `20260826_0041` folgt ausschließlich auf
`20260826_0040`.

Sie erzeugt genau eine leere
`manifest_handoff_supervisor_cleanup_retention_operations`-Tabelle.

Es gibt keinen Seed, Backfill, Scan und keine Bestandsadoption.

## Persistente Operationsbindung

Jede Zeile speichert Operation-ID, Directory-ID, Decision-ID,
Policyrevision, Datenklasse, Disposition, Evaluationszeit und Bindungszeit.

Die Operation-ID ist Primärschlüssel und damit nicht wiederverwendbar.

Eine Decision-ID darf höchstens einer Retentionoperation gehören.

## Decision- und Directorybindung

Der zusammengesetzte Fremdschlüssel aus Decision-ID und Directory-ID verweist
auf die bestehende eindeutige LQ-493-Decisionbindung.

Eine Operation kann dadurch keine Decision eines anderen Directorys
referenzieren.

Die Foundation erzeugt die Decision noch nicht selbst.

## Geschlossene persistente Werte

`data_class` erlaubt ausschließlich `supervisor_control_directory`.

`disposition` erlaubt ausschließlich `retain` oder `eligible`.

Operation-ID und Policyrevision müssen nichtleer sein.

Die Bindungszeit darf nicht vor der Evaluationszeit liegen.

## Warum Evaluation dupliziert gebunden wird

Policyrevision, Datenklasse, Disposition und Evaluationszeit bleiben an der
Operation sichtbar, auch wenn später eine neuere aktuelle Decision existiert.

Die spätere Adapterrekonstruktion muss diese Werte gegen die referenzierte
Decision erneut exakt prüfen.

Die Tabelle ist kein alternativer aktueller Decisionlookup.

## Atomare spätere Mutation

Eine spätere Storeimplementation muss zuerst nach Operation-ID auf exakten
Retry prüfen.

Bei einer neuen Operation muss sie Retired-Wert und Evaluation erneut binden,
Decision und Operation gemeinsam schreiben und erst danach Erfolg liefern.

Ein partieller Decisionappend ohne Operationzeile darf nicht committet werden.

## Keine Policyimplementation

LQ-528 entscheidet weder Frist, Alter, Legal Hold, Audit, Incident, Recovery,
Referenzfreiheit noch Datenklassendauer.

Es gibt keinen Default und keine lokale `now - retired_at`-Berechnung.

Fehlende Policyquellen bleiben für einen späteren Operator technische
Nichtverfügbarkeit.

## Keine Authority- oder Folgeaktion

Die Typen tragen keinen `SessionPrincipal`, User, Rolle, Membership oder
Permission.

Die Foundation erzeugt keine Clearance, keinen Cleanup-Attempt, kein
Retirement und keine Dateiwirkung.

Management-, Hold-, Recovery- und Referencequellen bleiben unverändert.

## Keine Löschung

Revision 0041 definiert keinen Deletepfad.

Operation-ID, Evaluation und Decisionbindung bilden eine dauerhafte Audit- und
Nichtwiederverwendungsuntergrenze.

Der Downgrade entfernt ausschließlich die neue leere/gesonderte
Operationstabelle als explizite Migrationsentscheidung.

## Keine Runtimeverdrahtung

Es gibt keinen Policyadapter, Storeadapter, Operator, Entry Point, HTTP-,
Appfactory-, Compose-, Worker-, Scheduler- oder Deploymentpfad.

Das Paketinventar bleibt bei 63 Entry Points und 68 Operatorfiles.

## Synchronisierte Gates

Der eindeutige Head ist `20260826_0041` mit 41 linearen Migrationen.

Roadmap, Migrationgate, Operational-Bundle-Inventar und synthetische
Wheelfixture werden auf denselben Stand aktualisiert.

## Tests

Statische Tests prüfen repr-freie IDs, minimalen Request, geschlossene
Evaluation, exakte Bound-Bindung, zwei minimale Ports, lineare leere Revision,
Primär-/Unique-/Fremdschlüssel, Constraints und fehlende Runtimewirkung.

Sie behaupten keine ausgeführte PostgreSQL-Evidence.

## Nächster Slice

LQ-529 implementiert den persistenten atomaren Retention-Operationstore gegen
Revision 0041.

Policyadapter, Operator, Retirement, Deployment und verpflichtende
PostgreSQL-Evidence bleiben separat.
