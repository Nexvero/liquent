# LQ-588 — Supervisor Control-directory Retirement Operator Completion Audit

## Ergebnis

LQ-588 schließt den owner-kontrollierten Retirementstrang LQ-585 bis LQ-588
ab und beseitigt den operativen Retirementblocker aus LQ-522.

Ein bekanntes Active-Directory kann nun nach aktuellem vollständigem
Terminaljournal über einen eigenen privaten One-Shot-Prozess in Retired
überführt werden. Keine Stufe danach startet automatisch.

## Geschlossene Wirkung

Der Request trägt nur die interne Directory-ID. Registry, Backendbindung,
Handle, Terminalstatus und Resultat werden aktuell aus dem System of Record
aufgelöst.

Erfolg persistiert genau eine Retirementzeit und übergibt Directory, Handle
und Zeitpunkt atomar privat. Retry rekonstruiert dieselben Fakten.

Unknown, Reserved, Nonterminal und Conflict bleiben wirkungsfrei `rejected`.
Technische Fehler bleiben detailfrei `operator_unavailable`.

## Fokussierter normaler Nachweis

Vertrag, Operator, SQLite-End-to-End-Pfad, LQ-490-Grenze, Releaseinventar und
historische Readinessguards bestehen gemeinsam mit 82 Tests unter
`-W error::DeprecationWarning`.

Der echte CLI-Pfad bestätigt private Eingaben, atomaren Resultathandoff,
geschlossene stdout/stderr-Outcomes und Engine-Disposal.

## Vollständige normale Suite

Die normale Suite besteht mit 5137 Tests und einem erwarteten Skip. 107
PostgreSQL-Integrationstests sind ausdrücklich abgewählt und separat
verpflichtend ausgeführt.

Es gibt keine Warning Summary.

## PostgreSQL

Die zwei neuen fokussierten PostgreSQL-Retirementfälle bestehen gegen jeweils
eigene migrierte Wegwerfdatenbanken.

Die vollständige PostgreSQL-Suite besteht mit 107 Tests. 5138 nicht zu diesem
Lauf gehörende Tests sind abgewählt.

Terminales Active wird über Registry- und Journalproduktionsadapter retired;
Retry bleibt zeitstabil. Nonterminal und Unknown bleiben ohne Mutation.

## Wheel und Inventar

Wheel `liquent-0.0.1-py3-none-any.whl` wurde ohne Buildisolation erfolgreich
außerhalb des Worktrees erzeugt.

Der neue Entry Point
`liquent-supervisor-control-directory-retire` ist im Wheel enthalten. Sein
`main` und Requestloader wurden direkt aus dem Paket importiert.

Quelle und Wheel stimmen bei 69 Console Entry Points und 70
Operator-Pythondateien einschließlich Initialisierer überein. Der Bestand
bleibt bei 42 Migrationen und Head `20260826_0042`.

Operational-Bundle und aktive Inventargates prüfen denselben Stand. Der
LQ-585-Vertrag ist required Contract des Bundles.

## Diff- und Scope-Audit

`git diff --check` ist sauber. Erzeugte `build/`- und
`src/liquent.egg-info/`-Zwischenprodukte wurden gezielt entfernt.

Der Strang ergänzt keine Migration, Tabelle, Domain-, Port- oder
Anwendungssignatur, Route, Appfactory-, Lifespan-, Scheduler-, Worker- oder
automatische Productionwirkung.

Es gibt keinen Commit, Push, Tag, Release, Signierung oder Deployment.

## Verbleibende Grenze

Retirement ist nun operativ erreichbar, aber weiterhin ausdrücklich manuell
und owner-kontrolliert. Supervisor-Production-Wiring und technische
Deploymentübergabe bleiben eigenständige spätere Entscheidungen.

Für den Retirement-Operatorstrang LQ-585 bis LQ-588 ist kein weiterer Slice
erforderlich.
