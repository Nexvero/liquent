# LQ-491 — Retired Supervisor Control-Directory Retention and Cleanup Contract

## Ergebnis

LQ-491 definiert die Sicherheits- und Retentionsgrenze für einen späteren
physischen Cleanup dauerhaft retirierter Supervisor-Control-Directories.

Der Slice implementiert keine Löschung, Domainwerte, Ports oder Adapter.

## Zwei getrennte Systeme

Die persistente Registry bleibt System of Record für Directory-ID, Handle,
Leaf und den irreversiblen Retired-Fakt.

Das lokale Dateisystem bleibt System of Record für Existenz, Typ, Eigentümer,
Modus, Inhalt und physische Entfernung.

Keines der Systeme darf Abwesenheit oder Freigabe des anderen erfinden.

## Retired ist notwendig

Physischer Cleanup darf ausschließlich für einen aktuell vollständig
rekonstruierten Retired-Wert geprüft werden.

Reserved und Active sind niemals cleanupfähig.

Ein terminales Journal ohne durable Retired-Transition genügt ebenfalls nicht.

## Retired ist nicht hinreichend

Retirement sperrt neue Active-Auflösung und Reaktivierung.

Es erteilt jedoch weder Retentionfreigabe noch Cleanupauthority.

Zeitablauf, Prozessende oder geringer Speicherbedarf ersetzen diese
Entscheidungen nicht.

## Interne Zielbindung

Ein späterer Cleanuprequest darf ausschließlich eine interne Directory-ID
tragen.

Root, Leaf, Handle, Pfad, Dateiname oder Inode werden nicht vom Caller
geliefert.

Der aktuelle Retired-Wert bindet das Ziel aus dem System of Record.

## Aktuelle Cleanupauthority

Cleanup benötigt eine separate aktuelle workspace- beziehungsweise
owner-kontrollierte Managementfähigkeit für genau Actor und Zielkontext.

SessionPrincipal identifiziert höchstens den Actor und erteilt selbst keine
Authority.

Caller-supplied Allowbooleans, Rollen, Membershipbehauptungen oder frühere
Authoritysnapshots sind unzulässig.

## Authority ist keine Retention

Eine berechtigte Person darf Retention-, Hold- oder Recoveryvoraussetzungen
nicht überstimmen.

Retentionfreigabe erteilt umgekehrt keine Actorauthority.

Beide Entscheidungen müssen unmittelbar vor möglicher Wirkung aktuell sein.

## Autoritative Retentionfreigabe

Eine spätere Retentionquelle muss die konkrete Directory-ID, ihren Handle,
die Datenklasse und eine stabile Policyrevision binden.

Nur eine aktuelle positive Freigabe darf den Cleanup fortsetzen.

Alter, `retired_at`, Dateizeitstempel oder Speicherfüllstand berechnen keine
Freigabe lokal.

## Keine konkrete Frist

LQ-491 legt keine Zahl von Tagen, Monaten oder Jahren fest.

Eine spätere Policy darf längere Aufbewahrung verlangen.

Sie darf die Sicherheits- und Nichtwiederverwendungsuntergrenzen dieses
Vertrags nicht verkürzen.

## Hold-Freiheit

Ein aktiver oder unklarer Legal-, Incident-, Audit- oder Investigation-Hold
sperrt jede physische Mutation.

Fehlende Holdquelle ist keine Hold-Freiheit.

Nur ein aktueller autoritativer No-Hold-Fakt ist ausreichend.

## Recovery-Freiheit

Offene Wiederherstellung, Reconciliation, Incidentanalyse oder
forensische Nutzung sperrt Cleanup.

Ein früherer erfolgreicher Prozessabschluss beendet diese Anforderungen nicht
automatisch.

Unklare Recoveryfakten bleiben fail-closed.

## Referenzuntergrenze

Das physische Directory bleibt mindestens erhalten, solange Journal,
Runtimebinding, Gatebinding oder korrelierte Control-Artefakte seine Inhalte
für Restart, Reconciliation, Audit oder Beweisführung benötigen.

Auch offene Claims, Inspektionen oder operative Handoffs können längere
Retention verlangen.

Eine einzelne terminale Tabelle darf diese Referenzen nicht überstimmen.

## Abgeschlossene Artefaktretention

Ready-, Release-Token-, Release-Consumed- und Terminal-Envelope-Fakten besitzen
eigene Retentionsgrenzen.

Ihre persistierten Metadaten und ihre physischen Bytes dürfen nicht
stillschweigend als gleichzeitig entbehrlich gelten.

Cleanup benötigt eine explizite gemeinsame Freigabe aller betroffenen
Datenklassen.

## Registryretention

Directory-ID, Handle, Leaf und alle Lifecyclezeiten bleiben unabhängig von
physischem Cleanup dauerhaft gegen Wiederverwendung gebunden.

Die Registryzeile oder ein gleichwertiger Tombstone darf nicht durch den
Filesystemcleanup entfernt werden.

Physische Abwesenheit macht keine Identität erneut verfügbar.

## Unmittelbare Revalidierung

Alle Authority-, Retention-, Hold-, Recovery-, Referenz- und Registryfakten
müssen unmittelbar vor möglicher Dateiwirkung erneut gelesen werden.

Ein Preflightreport oder früheres `eligible` ist keine Mutationsauthority.

Widerruf oder neu entstandener Hold muss spätere Entscheidungen sperren.

## Privates Root

Das Root muss bei jedem Cleanupversuch erneut als absolutes, echtes,
symlinkfreies, process-eigenes Directory mit Modus `0700` belegt werden.

Die Prüfung erfolgt über Directorydeskriptoren und No-follow-Semantik.

Ein unsicheres oder ausgetauschtes Root ist technische Unverfügbarkeit.

## Exaktes Leaf

Nur das unveränderte Leaf des aktuellen Retired-Werts darf relativ zum
geprüften Root betrachtet werden.

Leafname und geöffneter Deskriptor müssen über Device und Inode gebunden
bleiben.

Symlinks, fremder Eigentümer oder ein anderer Modus werden nicht adoptiert.

## Geschlossene Inventur

Vor einer Löschung muss das Directory vollständig und begrenzt inventarisiert
werden.

Nur die bekannten kanonischen Control-Artefaktnamen mit erwarteten privaten
Dateifakten dürfen zulässig sein.

Unbekannte Namen, Unterdirectories, Symlinks, Spezialdateien oder zusätzliche
Hardlinks sperren Cleanup ohne Mutation.

## Artefaktprüfung

Vorhandene bekannte Artefakte müssen gegen persistierte Rolle, Artifact-ID,
Handle, Korrelation, Bytezahl und Digest erneut gebunden werden.

Kanonisches Decoding und physische Fakten müssen gemeinsam übereinstimmen.

Ein persistierter Record ohne erwartete Datei oder eine Datei ohne Record ist
keine Löschfreigabe.

## Geordnete spätere Mutation

Eine spätere Implementation darf ausschließlich belegte bekannte Dateien und
danach das leere Leafdirectory entfernen.

Nach jeder irreversiblen Namensmutation ist der jeweilige Parentdescriptor zu
synchronisieren.

Root, Nachbarleafs und Registryfakten dürfen nicht verändert werden.

## Kein rekursives Löschen

Rekursive, globbasierte oder pfadverkettete Löschung ist verboten.

Es gibt kein `rm -rf`, kein Folgen von Symlinks und kein tolerantes Entfernen
unbekannter Einträge.

Jeder Name benötigt eine geschlossene vorherige Faktenbindung.

## Konkurrenz

Fakten müssen direkt vor jeder Mutation erneut geprüft werden.

Drift, neue Dateien oder ein ausgetauschtes Leaf stoppen ohne weitere
Wirkung.

Ein späterer Lock darf diese Revalidierung ergänzen, aber nicht ersetzen.

## Autoritative Abwesenheit

Eine vor jeder Wirkung autoritativ unbekannte Directory-ID ist neutral.

Für einen dauerhaft Retired-Record kann ein bereits sicher belegtes fehlendes
Leaf ein idempotenter `already_absent`-Ausgang sein.

Er löscht jedoch weder Registryfakten noch beendet er Evidenzretention.

## Konflikt

Reserved, Active, unbekannte Inventur, Cross-Bindings und unsichere physische
Fakten sind detailfreie Ablehnung beziehungsweise Konflikt.

Sie werden nicht zu Abwesenheit normalisiert.

Der Caller erhält keine internen Namen oder Pfaddetails.

## Technische Unverfügbarkeit

Unlesbare Authority-, Retention-, Hold-, Recovery-, Registry-, Artefakt- oder
Dateisystemquellen bleiben detailfreie technische Unverfügbarkeit.

LQ-491 benennt keinen neuen Exceptiontyp.

Ein technischer Fehler autorisiert keine best-effort Löschung.

## Unklarer Mutationsausgang

Fehler nach einer möglicherweise wirksamen späteren Entfernung dürfen weder
als Erfolg noch als Nichtwirkung ausgegeben werden.

Weitere Löschungen stoppen sofort.

Ein Retry beginnt mit read-only Reconciliation aller Registry- und
Filesystemfakten statt blind dieselbe Mutation zu wiederholen.

## Keine automatische Ausführung

Cleanup darf weder bei Retirement, Prozessende, App-Shutdown, Startup noch
nach einem Timer automatisch starten.

Batch-, Background-, TTL- und Best-effort-Cleanup sind außerhalb dieses
Vertrags.

Jeder Versuch benötigt eine neue aktuelle Entscheidung.

## Keine Implementation

LQ-491 ergänzt keine Klasse, Domainwerte, Portsignatur, Tabelle, SQL,
Migration, Retentionquelle, Holdsystem, Filesystemadapter oder Operatorgrenze.

Es wird keine Datei geöffnet, verändert oder entfernt.

Head bleibt `20260825_0034` mit 34 linearen Migrationen.

## Kein Wiring

Settings, Appfactory, Service-Facade, CLI, Route, Compose, Environment und
Deployment bleiben unverändert.

Productioncleanup bleibt geschlossen.

Es gibt keinen Commit oder Push.

## Tests

Fokussierte Vertragsprüfungen belegen Retired-vor-Cleanup, getrennte aktuelle
Authority und Retention, Hold-/Recovery-/Referenzsperren, dauerhafte
Registrytombstones, sichere geschlossene Inventur, geordnete nichtrekursive
Mutation, Reconciliation nach unklarem Ausgang und fehlende Implementation.

## Nächster Slice

LQ-492 sollte geschlossene Cleanup-Entscheidungs-, Ergebnis- und
Reconciliationwerte sowie minimale read-only und Mutationsports definieren.

Persistenz, Filesystemlöschung und Production-Wiring folgen getrennt.
