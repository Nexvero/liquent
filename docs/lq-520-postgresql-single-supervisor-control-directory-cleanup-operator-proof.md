# LQ-520 — PostgreSQL Single Supervisor Control-Directory Cleanup Operator Proof

## Ergebnis

LQ-520 ergänzt den ersten echten PostgreSQL-End-to-End-Nachweis für den
owner-kontrollierten LQ-519-Einzel-Operator.

Der Test verwendet die bestehende pro Test wegwerfbare, bis zum aktuellen Head
migrierte PostgreSQL-Datenbank.

## Kein Ersatzbackend

Der Nachweis besitzt keinen SQLite-, In-Memory- oder Mock-Datenbankfallback.

Ohne explizite PostgreSQL-Testkonfiguration wird er nach der bestehenden
Fixturepolicy übersprungen beziehungsweise im verpflichtenden Gate laut
abgelehnt.

## Vollständige Ausgangskette

Der Test sät einen aktiven User, aktiven Registry-Scope, Manifest-Handoff-
Attempt und dessen Execution-Claim.

Backend, Preparation, Handlebinding, Terminalobservation und Journaljob werden
vollständig gebunden.

Das Writer-Journal besitzt eine gültige lineare Historie bis
`terminal_observed`.

## Retired Directory

Ein persistentes Control Directory bindet exakt denselben Journalhandle.

Sein Lifecycle ist monoton von reserved über active nach retired belegt.

Der persistierte Leafname ist ein gültiger interner 64-Zeichen-Wert.

## Aktuelle Cleanupquellen

Die neueste Cleanupentscheidung ist `eligible`.

Management ist für denselben Actor und Scope aktiv.

Hold, Recovery und References sind für dasselbe Directory jeweils aktuell
`clear`.

Damit kann ausschließlich die echte LQ-508-Grenze eine Clearance erzeugen.

## Privater lokaler Root

Der Test erstellt einen privaten `0700`-Root und darunter exakt das persistiert
gebundene leere `0700`-Leaf.

Es werden keine Artefaktrecords gesät; der erwartete persistente und lokale
Bestand ist daher auf beiden Seiten exakt leer.

Der Produktionsadapter darf nur dieses belegte leere Leaf entfernen.

## Private Operatoreingaben

Datenbank-URL, Backend-ID, Root und Execute-Request werden in getrennten
`0600`-Dateien bereitgestellt.

Der Test ruft den echten `operator.main`-Pfad mit denselben vier Dateioptionen
wie der paketierte Console Entry Point auf.

Es gibt keinen Monkeypatch der Composition oder Wirkung.

## Execute-Nachweis

Der echte Operator prüft Readiness, baut LQ-517 auf, erzeugt intern eine
Attempt-ID und fordert aktuelle Clearance an.

Preflight bestätigt das sichere leere Leaf, der persistente Write Claim wird
genau einmal erstellt und die physische Grenze entfernt das Leaf.

Der Outcome-Store schließt denselben Attempt als `completed/removed` ab.

## Sichtbarer Ausgang

stdout enthält genau Attempt-ID, Directory-ID und `outcome=removed`.

Die Attempt-ID stammt aus der Operatorgrenze und war kein Requestfeld.

Absolute Root- oder Datenbankwerte werden nicht ausgegeben.

## Persistenter Beweis

Nach dem Operatorlauf liest der Test den Attempt über eine unabhängige
Fixtureverbindung erneut.

State ist `completed`, Outcome ist `removed` und `completed_at` ist gesetzt.

Es existiert genau eine persistente Cleanup-Write-Claim-Zeile.

## Physischer Beweis

Der private Root ist nach Erfolg leer.

Das exakte Leaf wurde entfernt und weder ein alternatives Leaf noch eine
zusätzliche Datei wurde erzeugt.

Der Test nutzt keinen rekursiven Cleanup als Teil der Behauptung.

## Expliziter Reconcile-Aufruf

Anschließend wird derselbe echte Operator mit dem separaten `reconcile`-
Befehl und der ausgegebenen Attempt-/Directory-Bindung aufgerufen.

Der bereits terminal completed Attempt ist kein zulässiger
Reconciliationkandidat.

Der geschlossene Ausgang ist deshalb `rejected`.

## Keine zweite Wirkung

Nach dem Reconcile-Aufruf bleibt der Attempt unverändert
`completed/removed` ohne Reconciliationoutcome.

Die Zahl persistenter Write Claims bleibt genau eins und der Root bleibt leer.

Damit belegt der Test, dass ein terminaler Attempt weder adoptiert noch erneut
physisch ausgeführt wird.

## Abgedeckte Grenzen

Der Nachweis durchläuft echte private Eingabeprüfung, Datenbankengine,
Readiness, LQ-517-Composition, LQ-508-Clearance, LQ-512-Preflight,
LQ-511-Claim, LQ-513-Wirkung, LQ-514-Outcome und LQ-515-Execution.

Der zweite Prozessaufruf erreicht die geschlossene LQ-516-Zustandsprüfung.

## Bewusste Begrenzung

LQ-520 erzeugt keinen künstlichen Unknown-Effekt und simuliert keinen Crash
zwischen physischer Wirkung und Outcome-Commit.

Damit beweist dieser Slice nicht den positiven absent/present/conflict-
Reconciliationpfad eines bestehenden Unknown-Claims.

Dieser Nachweis bleibt separat, damit der erfolgreiche Remove-Pfad nicht durch
Test-Doubles oder injizierte Fehler verfälscht wird.

## Keine Productionänderung

LQ-520 verändert keinen Operator, Adapter, Domainwert, Port oder Entry Point.

Es ergänzt keine Migration, Tabelle, Spalte, SQL-Produktionsanweisung oder
automatische Aktivierung.

Head bleibt `20260826_0040` mit 40 linearen Migrationen.

## Tests

Eine statische Begleitprüfung stellt sicher, dass der Integrationstest die
echte PostgreSQL-Fixture und den echten Operator verwendet, die vollständige
Authoritykette sät und terminale Persistenz sowie fehlende Zweitwirkung prüft.

## Nächster Slice

LQ-521 sollte einen persistenten `write_claimed`-/`outcome_unknown`-Crashzustand
auf PostgreSQL aufbauen und die positive read-only Reconciliation über den
echten Operator für absent, present und conflict nachweisen.

Automatische Planung, Directorydiscovery und Batchcleanup bleiben geschlossen.
