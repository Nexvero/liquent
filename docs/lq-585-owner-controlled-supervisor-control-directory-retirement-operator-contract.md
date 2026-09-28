# LQ-585 — Owner-controlled Supervisor Control-directory Retirement Operator Contract

## Ergebnis

LQ-585 schließt die in LQ-522 ausgewiesene operative Retirementlücke mit
einem owner-kontrollierten One-Shot-Prozessvertrag.

Der Prozess exponiert ausschließlich die bestehende LQ-490-Anwendungsgrenze.
Er erfindet keine zweite Retiremententscheidung und keine Cleanupwirkung.

## Eigener Prozess

Der feste Console Entry Point lautet
`liquent-supervisor-control-directory-retire`.

Ein Aufruf verarbeitet genau ein bekanntes Directory und beendet sich danach.
Es gibt kein Listing, keine Discovery, keinen Batch, Worker, Scheduler oder
automatischen Aufruf aus Appfactory, Lifespan oder HTTP.

## Private Konfiguration

Der Operator liest die Datenbank-URL und Backendinstanz-ID aus getrennten
privaten regulären Dateien. Er erhält keine DSN oder Backend-ID über frei
geloggte Positionsargumente.

Der Request kommt aus einer privaten JSON-Datei und enthält exakt
`directory_id`. Er enthält keinen Actor, `SessionPrincipal`, Workspace,
Membership, Rolle, Permission, Allowboolean, Handle, Leaf, Pfad,
Terminalstatus, Retentionentscheidung oder Retirementzeit.

## Autoritative Entscheidung

Der Prozess baut auf genau einer extern besessenen Engine den bestehenden
persistenten Control-Directory-Registryadapter und den für die konfigurierte
Backendinstanz gebundenen Journaladapter.

LQ-490 löst das aktuelle Directory und genau einen aktuellen Writer- oder
Recovery-Journalview aus dem System of Record. Nur Active plus vollständig
gebundenes `terminal_observed` darf den bestehenden atomaren
`retire_control_directory`-Übergang auslösen.

## Geschlossene Ergebnisse

Unbekanntes Directory, Reserved oder nichtterminales Active sowie Conflict
enden wirkungsfrei als `rejected` und erzeugen keine Ergebnisdatei.

Erfolg erzeugt atomar eine private Ergebnisdatei mit exakt `directory_id`,
`handle_id` und der tatsächlich persistenten `retired_at`-UTC-Zeit. Ein Retry
rekonstruiert dieselben Fakten.

Technische, beschädigte, unlesbare oder nichtbereite Zustände enden detailfrei
als `operator_unavailable`. SQL, URL, Dateipfad und Persistenzdetail werden
nicht ausgegeben.

## Keine Folgeaktion

Retirement startet keine Retentionevaluation, Decision, Clearance, Claim,
physische Löschung oder Reconciliation. Jede spätere Stufe bleibt ein eigener
ausdrücklicher owner-kontrollierter Aufruf.

## Retention und Nichtwiederverwendung

Directory-ID, Handle, Leaf, Journal- und Retirementfakten bleiben dauerhaft
gebunden und werden nicht zur Bereinigung gelöscht oder neu vergeben.

Die Mindestaufbewahrung beginnt erst mit der persistenten Retirementzeit; der
Operator nimmt keine Dauer oder Eligibilitybehauptung an.

## Abgrenzung

LQ-585 ergänzt keine Migration, Tabelle, Domain-, Port- oder
Anwendungssignatur, Route, App-Wiring oder Deploymentaktivierung.

LQ-586 implementiert genau diese Prozessgrenze.
