# LQ-498 — Persistent Supervisor Control-Directory Cleanup Clearance Adapter

## Ergebnis

LQ-498 implementiert die fünf read-only Resolverports aus LQ-496 gegen die
persistenten Foundations der Revision `20260825_0036`.

Der Slice erzeugt keine Authorityrevision, Clearance oder physische Wirkung.

## Ein Adapter

`DatabaseManifestHandoffSupervisorControlDirectoryCleanupClearance` bündelt
Management-, Hold-, Recovery-, Referenz- und aggregierte Clearanceauflösung.

Die getrennten Ports und fachlichen Quellen bleiben dennoch getrennt.

## Explizite Abhängigkeiten

Der Adapter erhält Engine, Directory-Lookup, Retention-Decision-Lookup sowie
Writer- und Recovery-Journal-Lookup explizit.

Er verändert keine Appfactory und aktiviert keinen Productionpfad.

## Aktuelle Managementrevision

Management wird nur für das exakte Actor-/Scope-Paar gelesen.

Die höchste Sequenz ist der aktuelle Zustand.

Eine ältere aktive Revision kann eine neuere inaktive Revision nicht ersetzen.

## Aktiver Actor und Scope

Der Managementread bindet die Revision an den persistenten aktiven User und
den persistenten aktiven Manifest-Handoff-Scope.

Unbekannte oder inaktive Facts liefern neutral keine Managementauthority.

SessionPrincipal, Membership und Researchpermission werden nicht gelesen.

## Geschlossener Managementwert

Revision-ID, Actor, Scope, Status und UTC-Zeit werden aus der Datenbank
rekonstruiert.

Beschädigte IDs, Sequenzen, Statuswerte oder Zeiten werden nicht normalisiert.

Sie führen zur bestehenden detailfreien technischen Unverfügbarkeit.

## Aktuelle Zielrevisionen

Hold, Recovery und Referenzen lesen jeweils ihre eigene Tabelle.

Jede Auflösung verwendet die höchste Sequenz für genau eine Directory-ID.

Zwischen den Quellen wird keine Revision ausgetauscht oder abgeleitet.

## Vollständiges Retired-Ziel

Jede Zielrevision wird mit dem aktuell aufgelösten vollständigen
`RetiredManifestHandoffSupervisorControlDirectory` rekonstruiert.

Ein nicht mehr konsistent rekonstruierbares persistentes Ziel ist technische
Divergenz und keine implizite Abwesenheit.

## Clear und Blocked

Die persistente Disposition wird geschlossen als `clear` oder `blocked`
rekonstruiert.

Blocked bleibt sichtbar und wird nicht in None oder Clear umgeschrieben.

Eine fehlende Revisionszeile liefert neutral None.

## Clearance als gebundener Startpunkt

Die Aggregation beginnt mit der persistenten Clearance für die Request-
Attempt-ID.

Ohne solche Zeile gibt es neutral keine aggregierte Clearance.

Der Caller kann keine Clearance-ID oder Revision auswählen.

## Attempt-, Actor- und Directorybindung

Die gelesene Clearance muss Request-Attempt, Request-Actor und
Request-Directory entsprechen.

Eine kollidierende persistente Attemptbindung liefert den bestehenden
fachlichen Cleanupkonflikt.

## Aktuelle Retentionentscheidung

Der Adapter liest die höchste Retentionentscheidung erneut über den bestehenden
Lookup.

Nur `eligible` ist positiv.

Die gebundene Decision-ID muss weiterhin exakt die aktuelle Decision-ID sein.

## Aktuelle Managementbindung

Management wird erneut für Request-Actor und den persistent gebundenen Scope
aufgelöst.

Nur `active` ist positiv.

Die aktuelle Revision-ID muss der in der Clearance gebundenen Revision
entsprechen.

## Aktuelle Holdbindung

Hold wird erneut für das Request-Directory gelesen.

Nur `clear` und die exakt gebundene aktuelle Holdrevision sind positiv.

Eine spätere Blocked-Revision sperrt die alte Clearance.

## Aktuelle Recoverybindung

Recovery wird unabhängig erneut gelesen.

Blocked, fehlende Authority oder eine neue Revisions-ID verhindern die
Aggregation.

Terminalität ersetzt diesen Read nicht.

## Aktuelle Referenzbindung

Referenzen werden ebenfalls aus ihrer eigenen aktuellen Quelle gelesen.

Nur die gebundene aktuelle Clear-Revision kann Teil des Ergebniswerts sein.

Der Adapter berechnet keine Referenzfreiheit aus Tabellenabwesenheit.

## Journalauflösung

Writer- und Recoveryjournal werden für das Handle des aktuellen Retired-Werts
inspiziert.

Genau ein Journalview muss vorhanden sein.

Kein oder zwei Views sind technische persistente Divergenz.

## Terminalitätsprüfung

Der eine View muss `TERMINAL_OBSERVED`, Terminal-Observation-ID und Ergebnis
tragen.

Die Terminal-ID muss exakt der Clearancebindung entsprechen.

Eine nackte Terminalzeile ohne vollständigen Journalview genügt nicht.

## Scope aus dem Journal

Der endgültige Domainwert prüft erneut, dass der gebundene Scope aus der
Journalregistration stammt.

Ein caller-supplied Scope existiert an der Aggregationssignatur nicht.

Abweichende Journal-, Handle- oder Scopefakten sind nicht positiv.

## Revalidierung bei jedem Aufruf

Der Adapter hält keinen Authority- oder Revisioncache.

Jede spätere Auflösung liest Management, Retention und alle drei Zielrevisionen
erneut.

Committer Entzug oder Blockierung wirkt damit auf spätere Entscheidungen.

## Historische Clearance

Eine überholte Clearancezeile bleibt als immutable Historie erhalten.

Sie ist kein Fortsetzungsrecht und wird bei Revisionsabweichung als Konflikt
zurückgewiesen.

LQ-498 löscht oder aktualisiert sie nicht.

## Neutrale Abwesenheit

Eine fehlende Management- oder Zielrevision liefert am jeweiligen Lookup None.

Eine fehlende Clearance für die Request-Attempt-ID liefert ebenfalls None.

Diese Ergebnisse offenbaren keine fremden IDs oder Zustandsdetails.

## Fachliche Zurückweisung

Eine vorhandene, aber nicht mehr positive oder nicht mehr aktuelle
Clearancebindung liefert den bestehenden detailarmen Cleanupkonflikt.

Es wird kein neuer Ablehnungs- oder Exceptiontyp eingeführt.

## Technische Unverfügbarkeit

Mehrdeutige Zeilen, beschädigte Werte, unmögliche Sequenzen, inkonsistente
Lifecyclefacts und unzulässige Datenbankdialekte enden an der bestehenden
`ManifestHandoffRegistryUnavailable`-Grenze.

Interne Daten oder SQL-Details werden nicht nach außen getragen.

## Keine Mutationen

Der Adapter enthält weder INSERT, UPDATE noch DELETE.

Er vergibt und entzieht keine Managementfähigkeit.

Er erzeugt keine Hold-, Recovery-, Referenz- oder Clearanceentscheidung.

## Keine physische Wirkung

Es gibt keinen Pfadread, Filesystemscan, Open-, Unlink- oder Rmdir-Aufruf.

Der bestehende Cleanup-Execution-Port wird nicht implementiert oder geöffnet.

Eine positive Auflösung entfernt keine Bytes.

## Keine neue Persistenzentscheidung

LQ-498 ergänzt keine Tabelle, Migration, Spalte oder Constraint.

Head und Migrationsanzahl bleiben `20260825_0036` und 36.

Revisionserzeugung benötigt eine spätere explizite Mutationsgrenze.

## Keine Verdrahtung

Settings, Appfactory, CLI, Route, Operator, Compose und Deployment bleiben
unverändert.

Der Adapter wird nicht automatisch instanziiert.

## Tests

Fokussierte statische Prüfungen belegen fünf Resolvermethoden, höchste
Sequenzen, aktive Actor-/Scopebindung, getrennte Zielquellen, Attemptbindung,
aktuelle Revisionsvergleiche, eindeutige terminale Journalauflösung,
detailfreie Fehlergrenze und das Fehlen von Mutation und Dateiwirkung.

## Nächster Slice

LQ-499 sollte die autorisierte append-only Mutationsgrenze für Management-,
Hold-, Recovery- und Referenzrevisionen sowie die atomare Clearanceerzeugung
definieren.

Production-Wiring und physischer Cleanup bleiben danach eigene Slices.
