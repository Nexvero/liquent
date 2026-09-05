# LQ-496 — Closed Supervisor Control-Directory Cleanup Clearance Values and Ports

## Ergebnis

LQ-496 implementiert die geschlossenen revisionsgebundenen Clearancewerte und
minimalen Resolverports des LQ-495-Vertrags.

Der Slice implementiert keine Persistenz, Authoritymutation oder Dateioperation.

## Clearance-ID

`ManifestHandoffSupervisorControlDirectoryCleanupClearanceId` ist eine stabile,
repr-freie und nichtleere Identität der aggregierten Clearanceentscheidung.

Sie ist weder Attempt-ID noch Retention-Decision-ID.

Sie wird nicht aus Actor, Directory, Scope, Zeit oder Pfad abgeleitet.

## Managementrevision

Die Cleanupmanagementfähigkeit besitzt eine eigene stabile repr-freie
Revision-ID.

Die Revision bindet den aktuell gelesenen Authorityzustand.

Eine frühere Revision kann keinen späteren Entzug überstimmen.

## Holdrevision

Holdclearance besitzt eine getrennte stabile Revision-ID.

Sie repräsentiert die gemeinsame aktuelle Legal-, Incident-, Audit- und
Investigation-Holdentscheidung für das Ziel.

Sie erteilt keine Managementauthority.

## Recoveryrevision

Recoveryclearance besitzt eine eigene stabile Revision-ID.

Sie ist von Hold, Retention und Referenzfreigabe getrennt.

Terminalität erzeugt diese Revision nicht automatisch.

## Referenzrevision

Die Referenzclearance besitzt eine eigene stabile Revision-ID.

Sie bindet die aktuelle Entscheidung über physische Bytes für Journal,
Runtime, Gate, Artefakte, Claims, Audit und operative Handoffs.

Eine einzelne Tabellenabwesenheit ist keine Referenzrevision.

## Repr und Form

Alle fünf neuen IDs tragen ausschließlich einen repr-freien Stringwert.

Leere oder außen mit Whitespace versehene Werte sind ungültig.

Validierungsfehler nennen keinen konkreten Identifier.

## Managementstatus

Der Managementstatus ist auf `active` und `inactive` geschlossen.

Freie Rollen, Permissionstrings oder Allowbooleans sind ausgeschlossen.

Nur Active kann Teil eines aggregierten Clearancewerts sein.

## Gemeinsame Clearancedisposition

Hold-, Recovery- und Referenzentscheidungen verwenden exakt `clear` oder
`blocked`.

Die gemeinsame geschlossene Form vereinheitlicht nur die Disposition, nicht
ihre getrennten Systeme of Record oder Revisionen.

Blocked kann nicht lokal zu Clear normalisiert werden.

## Managementauthoritywert

Der Managementwert bindet Revision-ID, Actor-User-ID, den autoritativen
Manifest-Handoff-Scope, geschlossenen Status und aware UTC Auflösungszeit.

Actor ist ein nichtleerer interner `UserId`-String.

Der Wert enthält keine Session, Workspace-Rolle oder Researchpermission.

## Scopebindung

Managementauthority gilt ausschließlich für genau den getragenen
`ManifestHandoffRegistryScopeId`.

Ein anderer Scope desselben Actors ist keine passende Authority.

Der Wert enthält keine Directory-ID, weil die Directory→Journal→Scopebindung
im aggregierten Clearancewert geprüft wird.

## Holdentscheidung

Der Holdwert bindet seine Revision, den vollständigen Retired-Wert,
Clear/Blocked und aware UTC Entscheidungszeit.

Seine Zeit darf nicht vor Retirement liegen.

Directory-ID, Handle und Leaf stammen ausschließlich aus Retired.

## Recoveryentscheidung

Der Recoverywert besitzt dieselbe geschlossene Form mit eigener Revision.

Er kann weder Hold noch Referenzclearance vertreten.

Nur Clear kann Teil der Aggregation sein.

## Referenzentscheidung

Der Referenzwert bindet ebenfalls den vollständigen Retired-Wert und seine
eigene Revision.

Er enthält keine freie Liste, Dateinamen oder Pfade.

Die spätere Resolverimplementation verantwortet die vollständige
Artefaktklassenprüfung.

## Warum vollständiges Retired

Alle drei zielbezogenen Entscheidungen tragen den vollständigen
Retired-Domainwert statt nur einer Directory-ID.

Dadurch können Handle, Leaf und alle Lifecyclezeiten nicht zwischen den
Quellen auseinanderlaufen.

Eine ältere Retired-Projektion mit abweichenden Fakten ist ungültig.

## Aggregierter Clearancewert

`ClearedManifestHandoffSupervisorControlDirectoryCleanup` trägt:

- stabile Clearance-ID;
- den vollständigen Cleanuprequest;
- den aktuellen vollständigen Retired-Wert;
- den autoritativ abgeleiteten Handoffscope;
- den vollständigen terminalen Writer- oder Recoveryjournalview;
- die aktuelle Retentionentscheidung;
- Management-, Hold-, Recovery- und Referenzfakt;
- aware UTC Clearancezeit.

Kein Dict oder freies Evidencebundle ist zulässig.

## Vollständiger Journalview

Die Aggregation akzeptiert exakt einen Writer- oder Recoveryjournalview.

Der View muss `TERMINAL_OBSERVED`, eine Terminal-Observation-ID und sein
geschlossenes Ergebnis tragen.

Eine nackte Terminal-ID wäre unzureichend, weil sie Handle und Scope nicht
konstruktiv bindet.

## Journal-Handle-Bindung

Journalregistration und Terminalergebnis müssen dasselbe Handle wie Retired
tragen.

Die bestehenden Journaldomainwerte prüfen zusätzlich ihre interne
Writer-/Recoverykonsistenz.

Ein anderer terminaler Job kann nicht adoptiert werden.

## Journal-Scope-Bindung

Der getragene Scope muss exakt
`journal.registration.process_request.binding.scope_id` entsprechen.

Damit stammt der Zielscope aus dem persistenten Prozessrequest und nicht vom
Caller.

Managementauthority muss exakt denselben Scope tragen.

## Actorbindung

Der Actor des Managementwerts muss exakt dem Actor des Cleanuprequests
entsprechen.

Der Request identifiziert den Actor, während der Managementwert die aktuelle
Capabilityrevision trägt.

Ein Clearancewert kann keinen Actorwechsel darstellen.

## Directorybindung

Request, Retired, Retentionentscheidung, Hold-, Recovery- und
Referenzentscheidung müssen dasselbe vollständige Directoryziel tragen.

Cross-Directory-Evidence ist konstruktiv ungültig.

Clearance-ID oder Attempt-ID können diese Bindung nicht ersetzen.

## Positive Aggregation

Die Aggregation verlangt gleichzeitig:

- Management `active`;
- Retention `eligible`;
- Hold `clear`;
- Recovery `clear`;
- Referenzen `clear`.

Inactive, Retain oder irgendein Blocked-Wert verhindern die Konstruktion.

## Zeitordnung

Die Clearancezeit muss aware UTC sein und darf nicht vor Retirement,
Retentionentscheidung, Managementauflösung, Holdentscheidung,
Recoveryentscheidung oder Referenzentscheidung liegen.

Die Zeit erzeugt keine Clearance und ersetzt keine Revision.

## Clearance ist keine Dateiauthority

Der aggregierte Wert belegt die fachlichen Voraussetzungen zu einem
bestimmten Zeitpunkt.

Vor jeder späteren irreversiblen Wirkung müssen seine Revisionen aktuell
revalidiert und physische Fakten erneut geprüft werden.

Er enthält keinen Pfad, Leafinput oder Löschboolean.

## Management-Lookupport

Der read-only Managementport löst ausschließlich Actor-User-ID und
Manifest-Handoff-Scope auf.

Er liefert den vollständigen aktuellen Managementwert oder neutral `None` für
autoritative Unbekanntheit.

Er besitzt keine Grant-, Revoke-, Bootstrap- oder Listenoperation.

## Hold-Lookupport

Der Holdport löst ausschließlich nach interner Directory-ID auf.

Er liefert den aktuellen vollständigen Holdwert oder neutral `None`.

Er erzeugt oder verändert keinen Hold.

## Recovery-Lookupport

Der Recoveryport besitzt dieselbe read-only Directory-ID-Oberfläche mit
seinem eigenen geschlossenen Ergebniswert.

Er startet, beendet oder adoptiert keine Recovery.

## Reference-Lookupport

Der Referenzport löst ausschließlich den aktuellen vollständigen
Referenzentscheid für eine Directory-ID auf.

Er listet keine Artefakte und löscht keine Metadaten.

Unbekannt ist nicht gleich Clear.

## Aggregierter Resolverport

`resolve_control_directory_cleanup_clearance` akzeptiert ausschließlich den
geschlossenen Cleanuprequest.

Er liefert den vollständigen Cleared-Wert, den bestehenden detailfreien
Cleanupkonflikt oder neutral `None` nur vor autoritativer Zielbindung.

Er mutiert keinen Attempt und keine Datei.

## Kein Caller-Snapshot

Kein Resolverport akzeptiert einen Status, eine Revision, einen Retired-Wert,
ein Journal oder eine Decision vom Caller.

Der aggregierte Resolver muss diese Fakten aktuell aus den jeweiligen Ports
beziehen.

Es gibt kein `allowed=True` und keinen stale Cachefallback.

## Konflikt und Technik

Inactive, Retain, Blocked und bindungsfremde vollständige Fakten werden an der
Aggregation detailfrei als Cleanupkonflikt behandelt.

Unlesbare oder strukturell beschädigte Quellen bleiben getrennte technische
Unverfügbarkeit an der bestehenden Exceptiongrenze.

LQ-496 benennt keinen neuen technischen Exceptiontyp.

## Keine Persistenz oder Mutation

LQ-496 ergänzt keine Tabelle, SQL, Migration, Authorityzuordnung,
Retentionquelle, Holdsystem oder Decisionmutation.

Head bleibt `20260825_0035` mit 35 linearen Migrationen.

Die persistente Clearancefoundation folgt separat.

## Keine Datei oder Wiring

Das neue Domainmodul importiert weder `Path` noch `os`.

Es öffnet, inventarisiert, synchronisiert oder entfernt keine Datei.

Service-Facade, CLI, Route, Operator, Compose und Production bleiben
unverändert geschlossen.

## Tests

Fokussierte Prüfungen belegen fünf repr-freie IDs, geschlossene Statuswerte,
Retired-gebundene Zielentscheidungen, vollständige Journal-/Scope-/Actor-
Bindung, ausschließlich positive Aggregation, monotone UTC-Zeit, fünf minimale
read-only Resolverports und fehlende Persistenz-/Dateimacht.

## Nächster Slice

LQ-497 sollte die additive persistente Management- und Clearancefoundation mit
revisionsgebundener Actor-/Scope-/Directory-/Attemptbindung definieren.

Resolveradapter, physischer Cleanup und Production-Wiring folgen getrennt.
