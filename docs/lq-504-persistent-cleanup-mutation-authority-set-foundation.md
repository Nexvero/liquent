# LQ-504 — Persistent Cleanup Mutation Authority-Set Foundation

## Ergebnis

LQ-504 ergänzt Revision `20260826_0038` als persistente Foundation für die vier
scopegebundenen LQ-503-Mutationsauthority-Domänen.

Die Revision erzeugt getrennte leere Set-, Member-, Pointer-, Bootstrap-,
Lifecycle- und Recoveryinventare.

## Lineare Revision

Revision 0038 folgt ausschließlich auf `20260826_0037`.

Es entsteht kein Branch und kein zweiter Head.

Die Historie umfasst danach 38 lineare Migrationen.

## Vier physisch getrennte Inventare

Management, Hold, Recovery und Referenzen verwenden jeweils sechs eigene
Tabellen.

Eine frei wählbare Authority-Art oder gemeinsame polymorphe Tabelle existiert
nicht.

IDs und Fremdschlüssel können nicht zwischen Quellen wechseln.

## Set-Revisionen

Jede Quellfamilie besitzt eine Authority-Set-Tabelle aus stabiler Revision-ID,
Scope-ID, positiver Sequenz und Erzeugungszeit.

Revision und Scope sind gemeinsam eindeutig adressierbar.

Sequenzen sind pro Scope eindeutig und werden noch nicht erzeugt.

## Scopebindung

Jede Setrevision verweist auf einen bestehenden Manifest-Handoff-Scope.

Der Fremdschlüssel beweist Existenz, nicht aktuellen Active-Status.

Der spätere Adapter muss den Scope bei jedem wirksamen Authorityentscheid
erneut fail-closed prüfen.

## Vollständige Mitglieder

Jede Quellfamilie besitzt eine Membertabelle aus Setrevision, Scope, User und
Active-/Inactive-Status.

Ein User kommt innerhalb einer Setrevision höchstens einmal vor.

Jedes Mitglied verweist auf einen persistenten internen User.

## Geschlossener Memberstatus

Memberstatus ist ausschließlich `active` oder `inactive`.

Es gibt keine Rolle, Permission oder Allowspalte.

Der Status ersetzt weder aktuellen Userstatus noch Scopestatus.

## Vollständigkeit bleibt Transaktionspflicht

Die Tabellenstruktur kann nicht allein beweisen, dass ein Set alle historische
Zuordnungen kopiert oder mindestens einen wirksamen Holder enthält.

Der spätere Store muss vollständige Memberprojektion und Lockoutschutz vor dem
Current-Pointer-Commit prüfen.

Teilsets dürfen nie current werden.

## Current-Pointer

Jede Quellfamilie besitzt genau einen möglichen Current-Pointer pro Scope.

Pointerrevision und Scope verweisen zusammengesetzt auf dieselbe Setrevision.

Eine Setrevision kann höchstens einmal current referenziert werden.

## Pointer ist keine Historienmutation

Das atomare Ersetzen eines Current-Pointers überschreibt keine Setrevision oder
Memberhistorie.

Nur der Pointer bezeichnet den aktuellen vollständigen Satz.

Alte Sets bleiben dauerhaft adressierbar.

## Bootstrapentscheidungen

Jede Quellfamilie besitzt eine eigene Bootstrap-Tabelle aus Bootstrap-ID,
Target-User, Scope, Ergebnisrevision und serverseitiger Zeit.

Scope ist innerhalb der Bootstrap-Tabelle eindeutig.

Damit kann jede Domäne pro Scope höchstens einmal gebootstrappt werden.

## Bootstrap-Target-Bindung

Ergebnisrevision, Scope und Target-User verweisen zusammengesetzt auf ein
Mitglied des erzeugten Sets.

Die Struktur beweist noch nicht Active-Status oder kontrolliertes Credential.

Beides bleibt Aufgabe des späteren Bootstrapadapters.

## Lifecycle-Entscheidungen

Jede Quellfamilie besitzt eine eigene Lifecycle-Change-Tabelle.

Sie bindet Change-ID, Actor, Target, Scope, erwartete Revision,
Ergebnisrevision, geschlossenes Intent und serverseitige Zeit.

Jede Ergebnisrevision gehört höchstens einer Lifecycleentscheidung.

## Actor im erwarteten Set

Expected-Revision, Scope und Actor verweisen zusammengesetzt auf ein Mitglied
des erwarteten Sets.

Dadurch kann kein Actor aus einem anderen Scope oder einer anderen Setrevision
strukturell adoptiert werden.

Active-Status und aktueller Pointer bleiben atomare Adapterprüfungen.

## Target im Ergebnis-Set

Ergebnisrevision, Scope und Target verweisen zusammengesetzt auf ein Mitglied
des erzeugten Sets.

Grant, Deactivate und Reactivate sind die einzigen persistierbaren Intents.

Der Adapter muss die jeweils zulässige Statusmatrix prüfen.

## Verschiedene Vorgänger und Ergebnisse

Expected- und Result-Revision einer Lifecycleentscheidung müssen verschieden
sein.

Lifecycle überschreibt kein bestehendes Set.

Ein Retry verweist auf die bereits gebundene Ergebnisrevision.

## Recoveryentscheidungen

Jede Quellfamilie besitzt eine eigene Recovery-Tabelle aus Recovery-ID, Target,
Scope, erwarteter Revision, Ergebnisrevision und serverseitiger Zeit.

Jede Ergebnisrevision gehört höchstens einer Recoveryentscheidung.

Recovery-IDs sind nicht Lifecycle- oder Bootstrap-IDs.

## Historische Recoverybindung

Expected-Revision, Scope und Target verweisen auf historische Mitgliedschaft im
erwarteten vollständigen Set.

Ergebnisrevision, Scope und Target verweisen auf das neue Setmitglied.

Der spätere Adapter prüft geschlossenen Scope, fehlende wirksame Holder und
Active-Reaktivierung.

## Keine User- oder Scopemutation

Authoritytabellen ändern keinen User- oder Handoffscope-Status.

Ihre Fremdschlüssel erlauben weder Useranlage noch Scopeanlage.

Inaktive Foundations bleiben fail-closed und werden nicht repariert.

## Keine Seeds oder Adoption

Alle 24 Tabellen bleiben nach Migration leer.

Es gibt keinen Seed, Backfill, Bootstrap oder die Adoption bestehender Cleanup-
oder Registryauthorities.

Leerer Bestand erlaubt keine fachliche Revisionmutation.

## Append-only Untergrenze

Setrevisionen, Mitglieder, Bootstrap-, Lifecycle- und Recoveryentscheidungen
besitzen keinen Delete- oder Updatepfad in dieser Foundation.

Current-Pointer-Mutation folgt erst mit dem kontrollierten Adapter und darf nur
auf vollständig neu erzeugte Sets zeigen.

Historische IDs werden nicht wiederverwendet.

## Konkurrenz und Atomarität

Revision 0038 entscheidet noch keine Lockstrategie.

Der spätere Adapter muss neue Sets, vollständige Members, Entscheidung und
Current-Pointer in einer serialisierten Transaktion committen.

Unique-Constraints sind letzte Integritätssperren, nicht Authorityprüfung.

## Neutrale Abwesenheit

Fehlender Current-Pointer bedeutet keine wirksame Authority.

Fehlende Bootstrap-, Lifecycle- oder Recoveryentscheidung kann einen unbekannten
Retry neutral lassen.

Die Migration benennt keinen neuen Exceptiontyp.

## Keine fachliche Mutation

LQ-504 führt keinen Bootstrap-, Grant-, Deactivate-, Reactivate- oder
Recoveryadapter aus.

Es gibt keinen Lookup, Revisionsappend oder Clearanceinsert.

SessionPrincipal wird nicht persistiert oder als Authority interpretiert.

## Keine physische Wirkung

Die Tabellen speichern keine Directory-ID, Handles, Roots, Leafs, Pfade,
Dateinamen oder Artefaktbytes.

Sie öffnen, verändern und entfernen keine Datei.

Authorityfacts erteilen keine physische Cleanupwirkung.

## Downgrade

Downgrade entfernt pro Quelle zuerst Recovery-, Lifecycle-, Bootstrap-,
Current-, Member- und zuletzt Settabellen.

Die Quellen werden in umgekehrter Reihenfolge Reference, Recovery, Hold und
Management entfernt.

Cleanuprevisionen, Changebindings, Attempts und Clearances bleiben unverändert.

## Gate-Synchronisierung

Der erwartete Head wird auf `20260826_0038` gesetzt.

Das operative Bundle erwartet 38 Migrationen.

Die Roadmap veröffentlicht denselben Head und dieselbe Anzahl.

## Tests

Fokussierte Prüfungen belegen vier getrennte Inventare mit insgesamt 24 leeren
Tabellen, vollständige Scope-/Member-/Pointerbindung, eindeutige Bootstrap-
Scopes, Actor-/Targetbindung, historische Recoveryeligibility,
geschlossene Status und Intents, fehlende Seeds und reversen Downgrade.

## Nächster Slice

LQ-505 sollte den persistenten Lookup-, Bootstrap-, Lifecycle- und
Offline-Recoveryadapter gegen Revision 0038 implementieren.

Autorisierte Quellrevisionmutation, atomare Clearancecreation und physischer
Cleanup bleiben danach getrennt.
