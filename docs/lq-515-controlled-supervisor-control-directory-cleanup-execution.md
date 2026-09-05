# LQ-515 — Controlled Supervisor Control-Directory Cleanup Execution

## Ergebnis

LQ-515 implementiert die kontrollierte High-Level-Composition des bestehenden
`ManifestHandoffSupervisorControlDirectoryCleanupExecution`-Ports.

Sie verbindet Started-Request, LQ-512-Preflight, LQ-511-Write-Claim,
einmalige LQ-513-Wirkung und unmittelbare LQ-514-Outcome-Persistenz.

## Einziger öffentlicher Effekt

`ControlledManifestHandoffSupervisorControlDirectoryCleanupExecution` besitzt
nur `cleanup_control_directory` als öffentlichen Fachaufruf.

Der Eingang ist ausschließlich der geschlossene bestehende Cleanuprequest mit
Attempt-ID, Actor-User-ID und Directory-ID.

Es gibt keinen separaten Pfad-, Leaf-, Rollen-, Allow- oder Outcomeinput.

## Exakter Started-Request

Vor dem Preflight löst die Composition den Attempt aktuell über seine interne
ID auf.

Nur der vollständige persistente Started-Request darf fortfahren und muss dem
übergebenen Request einschließlich Actor und Directory exakt entsprechen.

Unbekannter Attempt bleibt neutral `None`; terminale, claimed, unknown,
reconciled oder abweichende Requests liefern detailfreien Konflikt.

## Kein Retry physischer Zustände

Die High-Level-Execution adoptiert keinen bereits geclaimten Attempt als neuen
Ausführungsrequest.

Completed und Reconciliation-required werden nicht durch einen erneuten
physischen Aufruf rekonstruiert.

Statusauflösung und Crashreconciliation bleiben separate Grenzen.

## Read-only Preflight

Aus dem exakten Started-Request konstruiert die Composition intern nur den
minimalen Attempt-/Directory-gebundenen LQ-510-Preflightrequest.

Der LQ-512-Adapter löst Actor, Clearance, Retired-Ziel und Artefakte weiterhin
selbst aus persistenten Quellen auf.

Ein Preflightkonflikt beendet ohne Claim oder Wirkung.

## Neutrale Preflightabweichung

Da der Attempt unmittelbar zuvor autoritativ bekannt war, wird ein unerwartet
neutrales Preflight-`None` nicht als unbekannter Gesamtrequest ausgegeben.

Es endet konservativ als detailfreier Konflikt.

Ein strukturell fremder Preflightwert ist technische Unverfügbarkeit.

## Absent-Pfad

Ein exakt Attempt-/Directory-gebundener Absent-Preflight öffnet keinen
Write-Claim und keinen physischen Adapter.

Die Composition persistiert ausschließlich den bestehenden wirkungsfreien
`already_absent`-Abschluss aus `started`.

Das Ergebnis muss vollständiges Completed mit demselben Attempt, Directory und
Outcome sein.

## Prepared-Pfad

Nur ein vollständiger Prepared-Wert mit exakt derselben Attempt- und
Directory-ID darf einen Claimcommand bilden.

Prepared erteilt selbst keine Wirkung und wird nicht gecacht oder verzögert.

Ein abweichendes Binding endet vor Claim als Konflikt.

## Atomarer Write-Claim

Die Composition ruft den LQ-511-Claim-Port genau einmal mit dem vollständigen
Prepared-Wert auf.

Konflikt oder neutrale Abweichung endet ohne physischen Aufruf.

Nur ein vollständiger Claimed-Wert, dessen Prepared exakt dem Preflight
entspricht, erreicht LQ-513.

## Exakt ein physischer Aufruf

Nach erfolgreichem Claim ruft die Composition
`remove_control_directory(claimed)` an genau einer Codestelle auf.

Es gibt keine Schleife, keinen Retry, keinen Fallbackadapter und keinen zweiten
Aufruf nach Exception oder Persistenzfehler.

Der physische Adapter bleibt für Root-, Leaf-, Inventar- und
Dauerhaftigkeitsprüfung verantwortlich.

## Bestimmtes Removed

Ein LQ-513-Removed wird nur akzeptiert, wenn Claim-ID, Attempt-ID und
Directory-ID exakt dem Claimed-Wert entsprechen.

Danach wird genau dieser vollständige physische Wert unmittelbar an den
LQ-514-Outcome-Store gegeben.

Fremde oder unvollständige Resultate werden nicht als Removed adoptiert.

## Explizites Unknown

Ein LQ-513-Unknown wird nur mit exakt derselben Claim-, Attempt- und
Directorybindung akzeptiert.

Er wird unmittelbar persistent nach `outcome_unknown` überführt.

Die Composition behauptet weder Wirkung noch Nichtwirkung.

## Konservative Grenze nach Claim

Jede Exception, jeder Konflikt, `None`, fremde Typ oder Cross-Binding-Ausgang
des physischen Adapters wird nach Claim intern zu einem exakt gebundenen
Unknown-Effekt.

Damit bleibt selbst ein vertragswidriger oder unklarer Adapterausgang
reconciliation-pflichtig.

Nach Claim kehrt die Composition nie zu einem sicheren Preflightkonflikt oder
einem erneuten Remove zurück.

## Sofortige Outcome-Persistenz

Removed oder Unknown wird direkt nach dem einzigen physischen Aufruf ohne
Queue, Batch, Timer oder Hintergrundhandoff an LQ-514 übergeben.

Zwischen physischem Ergebnis und Persistenz findet keine neue
Authorityentscheidung statt.

Der Store wird genau einmal aufgerufen.

## Persistiertes Removed

Für Removed akzeptiert die Composition ausschließlich vollständiges
Completed/removed mit derselben Attempt- und Directory-ID und exakt derselben
`removed_at`-/`completed_at`-Zeit.

Ein Conflict, `None`, falscher Outcome oder abweichende Zeit ist technische
Unverfügbarkeit.

Die physische Wirkung wird dabei niemals wiederholt.

## Persistiertes Unknown

Für Unknown akzeptiert die Composition ausschließlich den vollständigen
Reconciliation-required-Wert mit derselben Attempt- und Directory-ID.

Andere persistente Antworten werden nicht zu Erfolg oder neutraler Abwesenheit
normalisiert.

Auch hier gibt es keinen zweiten physischen Aufruf.

## Persistenzfehler nach Wirkung

Wirft der Outcome-Store nach dem physischen Aufruf einen technischen Fehler,
wird dieser detailfrei weitergegeben.

Die Composition versucht weder denselben Storewrite in einer Schleife noch
den physischen Remove erneut.

Der persistente `write_claimed`-Fakt bleibt die sichere Crashmarkierung für die
spätere Reconciliation.

## Prozessabbruch

Ein harter Prozessabbruch zwischen Claim, physischer Wirkung und Outcomecommit
kann nicht innerhalb desselben Aufrufs geheilt werden.

Beim nächsten Start darf `write_claimed` nicht physisch wiederholt werden.

Der nächste Slice muss `write_claimed` und `outcome_unknown` rein lesend
reconciliieren.

## Keine Authority aus Session oder Request

Der Actor im Cleanuprequest wird nur gegen den persistenten Started-Request
gebunden.

SessionPrincipal, Membership, Researchpermissions und caller-gelieferte Rollen
werden nicht akzeptiert.

Aktuelle Wirkungsauthority bleibt ausschließlich im LQ-511-Claim.

## Fehlergrenze

Vor Claim bleiben bekannte fachliche Abweichungen detailfreier Konflikt und
unbekannter Attempt neutrales `None`.

Technische Dependency-, Typ- und Persistenzfehler bleiben an der bestehenden
detailfreien technischen Grenze.

Nach Claim wird jede physische Unsicherheit zunächst als Unknown persistiert.

LQ-515 benennt keinen neuen Exceptiontyp.

## Keine neue Persistenz oder Verdrahtung

LQ-515 ergänzt keine Tabelle, Migration, SQL, Domainklasse oder Portsignatur.

Es gibt keine Route, CLI, Worker-, Timer-, Startup-, Shutdown-, Appfactory-,
Compose- oder Productionverdrahtung.

Head bleibt `20260826_0040` mit 40 linearen Migrationen.

## Tests

Fokussierte Prüfungen belegen exakte Started-/Actorbindung, Absent ohne Claim,
Prepared vor Claim, genau einen physischen Aufruf, konservatives Unknown nach
Claim, unmittelbare einmalige Persistenz und fehlenden Retry-/Wiringpfad.

## Nächster Slice

LQ-516 sollte `write_claimed` nach Crash und `outcome_unknown` über denselben
sicheren lokalen Bestand rein lesend reconciliieren und terminal persistieren.

Production-Wiring bleibt danach separat.
