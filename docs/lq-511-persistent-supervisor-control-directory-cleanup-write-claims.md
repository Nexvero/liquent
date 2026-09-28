# LQ-511 — Persistent Supervisor Control-Directory Cleanup Write Claims

## Ergebnis

LQ-511 ergänzt die additive persistente Write-Claim-Foundation und den
atomaren Übergang eines Supervisor-Control-Directory-Cleanup-Attempts aus
`started` nach `write_claimed`.

Der Slice führt keine Dateisystemoperation aus.

## Additive Revision

Revision `20260826_0040` folgt linear auf `20260826_0039`.

Sie ergänzt genau eine leere Write-Claim-Tabelle sowie die für den neuen
Attemptzustand erforderlichen Constraints und Bindungen.

Die Migration erzeugt keine Claims, Attempts, Clearances oder Seedfacts.

## Eigener Zustandsfakt

`write_claimed` ist ein eigener dauerhafter Attemptzustand zwischen `started`
und einer möglicherweise wirksamen physischen Operation.

Er ist weder Alias noch Umdeutung von `outcome_unknown`.

`write_claimed_at` ist nur in Zuständen zulässig, die aus einem Write-Claim
hervorgegangen sind.

## Geschlossene Übergänge

Ein neuer Claim darf ausschließlich `started` nach `write_claimed`
überführen.

`removed` und `outcome_unknown` dürfen anschließend nur aus `write_claimed`
entstehen.

`already_absent` bleibt der einzige Completed-Ausgang direkt aus `started`,
weil dabei keine Dateiwirkung begonnen wurde.

## Reconciliation

Reconciled bleibt ausschließlich Nachfolger von `outcome_unknown`.

Ein reconciled Attempt muss deshalb ebenfalls einen früheren Write-Claim und
eine monotone Claim-/Unknown-/Reconciliationzeit besitzen.

`present` autorisiert weiterhin keinen zweiten physischen Aufruf.

## Nichtwiederverwendbare Claim-ID

Jede Claim-ID ist nichtleer und global primär gebunden.

Die Tabelle erlaubt höchstens einen Claim je Attempt.

Eine Preflight-ID darf ebenfalls höchstens einen Claim binden und kann nicht
für einen zweiten Attempt adoptiert werden.

## Vollständige Claimbindung

Jeder Claim bindet Claim-ID, Attempt-ID, Directory-ID, Clearance-ID,
Preflight-ID, Prepared-Zeit und Claimzeit.

Zusammengesetzte Fremdschlüssel binden Attempt und Directory sowie Clearance,
Attempt und Directory an exakt denselben persistenten Bestand.

Cross-Attempt-, Cross-Directory- und Cross-Clearance-Adoption scheitert auf
Schema- und Adapterebene.

## Monotone Zeiten

Der Adapter verlangt Prepared nicht vor Attemptstart oder Clearancezeit.

Claimed darf nicht vor Prepared liegen.

Unknown, Removed und spätere Reconciliation dürfen nicht vor dem persistenten
Claim liegen.

## Unresolved-Untergrenze

Der bestehende eindeutige unresolved-Directory-Index umfasst nun `started`,
`write_claimed` und `outcome_unknown`.

Damit kann kein zweiter offener Attempt für dasselbe Directory begonnen
werden, während ein Claim oder unklarer Effekt offen ist.

Completed und reconciled bleiben terminal.

## Minimaler Adapter

`DatabaseManifestHandoffSupervisorControlDirectoryCleanupWriteClaims`
implementiert ausschließlich den LQ-510-Write-Claim-Port.

Er akzeptiert nur den vollständigen
`ClaimPreparedManifestHandoffSupervisorControlDirectoryCleanup`-Command.

Pfad, Root, Leaf, Dateiname, Inventarliste, Rolle oder Allowboolean werden
nicht akzeptiert.

## Retry zuerst

Attempt und vorhandener Claim werden vor jeder neuen Authorityauflösung
gelesen.

Ein exakt gebundener bereits committierter Claim wird mit derselben Claim-ID,
Prepared-Bindung und Claimzeit rekonstruiert.

Ein Retry erzeugt keinen zweiten Claim und öffnet selbst keinen zweiten
physischen Aufruf.

## Keine Adoption

Ein Claim ohne Attempt, ein Attempt ohne Clearance oder eine abweichende
Prepared-, Directory-, Clearance- oder Preflightbindung ist kein Retry.

Diese Fälle enden als technische Korruption oder detailfreier Konflikt und
werden weder vervollständigt noch überschrieben.

## Aktuelle Revalidierung vor neuem Claim

Für einen neuen Claim rekonstruiert der Adapter Actor und Ziel ausschließlich
aus Attempt, Clearance, Registry und terminalem Journal.

Er liest aktuellen aktiven User und Scope sowie aktuelle Eligible-Retention-,
Active-Management-, Clear-Hold-, Clear-Recovery- und
Clear-Referenzrevisionen in derselben Transaktion.

Alle Revisionen und das Terminalobservation-Binding müssen exakt der
persistierten Clearance entsprechen.

## Revocation

Ein vor der Claimtransaktion committierter Authorityentzug oder neuer Blocker
verhindert den neuen Claim fail-closed.

Ein bereits committierter exakter Claim bleibt als historischer Fakt
auflösbar, ohne aktuelle Authority erneut zu behaupten.

Er darf nur durch die spätere kontrollierte Einmal-Ausführung konsumiert oder
read-only reconciled werden.

## Atomarer Commit

Claimzeile und Attempttransition werden in derselben Datenbanktransaktion
geschrieben.

Entweder Claim und `write_claimed_at` committen gemeinsam oder keine der
beiden Änderungen bleibt bestehen.

Die bedingte Attemptmutation muss exakt eine `started`-Zeile treffen.

## Serverseitige Fakten

Claim-ID und aware UTC Claimzeit werden intern erzeugt.

Der Caller kann weder Claim-ID noch Claimzeit, Actor, Scope oder aktuelle
Quellrevisionen wählen.

Prepared-ID und Prepared-Zeit stammen aus dem geschlossenen internen
Preflightwert und werden unverändert gebunden.

## PostgreSQL und SQLite

PostgreSQL serialisiert neue Claims über feste Locks aller beteiligten
Authority-, Journal-, Registry-, Attempt-, Clearance- und Claimtabellen.

SQLite bleibt die kontrollierte Testgrenze mit derselben atomaren
Transaktionssemantik.

Andere Dialekte scheitern detailfrei.

## Bestehende Attemptrekonstruktion

Der persistente Cleanupadapter rekonstruiert `write_claimed` als vollständigen
LQ-510-Claimed-Wert.

Claimpflichtige Unknown-, Removed- und Reconciled-Zustände validieren dabei
Claim-ID, Preflight, Clearance und monotone Zeiten erneut.

Historisches `already_absent` bleibt konstruktiv claimfrei.

## Fehlergrenze

Autoritativ unbekannte Attempt-ID bleibt neutral, bevor eine erwartete
Bindung besteht.

Zustands-, Authority- und Cross-Binding-Abweichungen liefern den bestehenden
detailfreien Cleanupkonflikt.

Persistenzkorruption und Infrastrukturfehler bleiben detailfreie technische
Unverfügbarkeit; LQ-511 benennt keinen neuen Exceptiontyp.

## Keine physische Wirkung

Migration und Adapter importieren weder `Path` noch öffnen, inventarisieren,
entfernen oder synchronisieren sie Dateien.

Der Claim behauptet keine bereits erfolgte Dateiwirkung.

Es gibt keine Route, CLI, Worker-, Timer-, Startup-, Shutdown- oder
Productionverdrahtung.

## Head

Der lineare Migrationsstand ist jetzt `20260826_0040` mit 40 Migrationen.

## Tests

Fokussierte Prüfungen belegen lineare additive Migration, leere Claimtabelle,
zusammengesetzte Bindungen, geschlossenen Zustandsautomaten, Retry-first,
aktuelle Revalidierung und den atomaren bedingten Übergang ohne Datei-I/O.

## Nächster Slice

LQ-512 sollte den sicheren lokalen read-only Cleanup-Preflight implementieren.

Physische Entfernung, Outcome-Persistenz, Reconciliation und
Production-Wiring bleiben danach getrennte Slices.
