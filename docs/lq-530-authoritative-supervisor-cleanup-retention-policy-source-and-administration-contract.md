# LQ-530 — Authoritative Supervisor Cleanup Retention Policy Source and Administration Contract

## Ergebnis

LQ-530 definiert die autoritative Policyquelle und die davon getrennte
Administration für Retentionentscheidungen über Supervisor-Control-
Directories.

Der Slice implementiert keine Policywerte, Ports, Persistenz, Mutation oder
Operatorgrenze.

## Zweck

LQ-527 verbietet caller-gelieferte `retain`-/`eligible`-Entscheidungen.

LQ-528 und LQ-529 können eine bereits autoritative Evaluation geschlossen und
atomar an eine Decision binden.

LQ-530 legt fest, woher Policyrevision, Mindestaufbewahrung, Disposition und
Evaluationszeit später stammen dürfen.

## Eine geschlossene Datenklasse

Die erste Policyquelle gilt ausschließlich für
`supervisor_control_directory`.

Sie umfasst das private Control Directory und die durch den bestehenden
Cleanupvertrag gemeinsam gebundenen Control-Artefakte.

Andere Datenklassen dürfen nicht über einen freien String oder dieselbe
Revision adoptiert werden.

## Stabile Policyrevision

Jede Policyrevision besitzt eine stabile, nichtleere, repr-freie interne ID.

Die ID wird zufällig beziehungsweise sicher intern erzeugt und nicht aus Dauer,
Zeit, Actor oder Datenklasse abgeleitet.

Eine Policyrevision wird niemals einer anderen Policydefinition zugeordnet
oder wiederverwendet.

## Immutable Policyfakten

Eine Revision bindet mindestens Datenklasse, strikt positive
Mindestaufbewahrungsdauer, Erzeugungszeit und ihren unveränderlichen
Policyinhalt.

Nach Persistenz werden Dauer, Datenklasse und Inhalt nicht überschrieben.

Eine fachliche Änderung erzeugt eine neue Revision.

LQ-530 legt keine konkrete Anzahl von Tagen, Monaten oder Jahren fest.

## Dauersemantik

Die Mindestaufbewahrung ist eine strikt positive, begrenzte Zeitdauer mit
eindeutiger Sekundenauflösung.

Kalendermonate, lokale Zeitzonen, Sommerzeit und freie Dauerstrings sind nicht
Teil der ersten Semantik.

Die spätere Domain darf eine technische obere Grenze setzen, aber keine
fachliche Defaultdauer erfinden.

## Autoritative Schwelle

Für einen exakten Retired-Wert ist die früheste Policy-Schwelle
`retired_at + minimum_retention`.

Nur der Policyadapter berechnet diese Schwelle mit der aktuell aktiven
Policyrevision.

Der Operator, der Caller, Dateizeitstempel und das lokale Dateisystem berechnen
keine alternative Freigabe.

Überlauf, ungültige UTC-Werte oder eine nicht darstellbare Schwelle sind
technische Unverfügbarkeit.

## Vertrauenswürdige Evaluationszeit

Der Policyadapter erhält eine explizite vertrauenswürdige aware-UTC-Clock.

Der einmal gelesene Evaluationszeitpunkt wird sowohl für den Vergleich als
auch für `evaluated_at` derselben Evaluation verwendet.

CLI-, Request-, Dateisystem- oder Environmentzeiten werden nicht akzeptiert.

Eine regredierende oder ungültige Clock ist technische Unverfügbarkeit.

## Geschlossene Auswertung

Liegt `evaluated_at` vor der Schwelle, lautet die Evaluation `retain`.

Liegt sie auf oder nach der Schwelle, lautet sie `eligible`.

Es gibt keinen Toleranzbereich, kein Runden und keinen caller-gelieferten
Override.

Beide Ergebnisse binden dieselbe aktive Policyrevision, Datenklasse, den
vollständigen Retired-Wert und den Evaluationszeitpunkt.

## Eligible bleibt begrenzt

`eligible` belegt ausschließlich, dass die Mindestaufbewahrung der aktiven
Policyrevision erfüllt ist.

Es erteilt keine Actor-, Authority-, Hold-, Recovery-, Reference-, Retirement-
oder Dateisystemfreigabe.

LQ-508 muss vor einer Cleanup-Clearance weiterhin alle getrennten aktuellen
Quellen prüfen.

## Retain ist ein positiver Policyentscheid

`retain` ist weder Ablehnung noch technische Unverfügbarkeit.

Es darf durch LQ-529 als aktuelle append-only Cleanup-Decision persistiert
werden.

Eine spätere Evaluation kann nach Erreichen der Schwelle eine neue
`eligible`-Decision erzeugen; sie überschreibt die Retainhistorie nicht.

## Genau eine aktive Revision

Für die geschlossene Datenklasse ist höchstens eine Policyrevision aktuell
aktiv.

Eine aktive Revision ist die einzige Quelle für neue Evaluationen.

Mehrere aktive Revisionen, widersprüchliche Pointer oder beschädigte
Aktivierungsfakten sind technische Unverfügbarkeit.

## Keine Defaultpolicy

Ohne aktive Revision liefert die Policyquelle keine Evaluation.

Sie fällt nicht auf eine hardcodierte Dauer, eine frühere Revision oder
`eligible` zurück.

Ein späterer Operator klassifiziert autoritative Abwesenheit neutral und
detailfrei; ein unlesbarer Policybestand bleibt technische Unverfügbarkeit.

## Aktuelle Auflösung

Jede neue Evaluation liest die aktive Revision und ihren vollständigen Inhalt
neu aus dem System of Record.

Es gibt keinen prozessübergreifenden positiven Cache und keinen vom Caller
mitgebrachten Policy-Snapshot.

Aktivierung, Ablösung oder Deaktivierung muss jede spätere Evaluation
beeinflussen.

## Historische Decisions

Bereits persistierte Decisions und Operationen behalten ihre gebundene
Policyrevision dauerhaft als Auditfakt.

Sie werden durch einen Policywechsel nicht umgeschrieben.

Eine historische `eligible`-Decision ist jedoch keine Berechtigung für eine
spätere Clearance, wenn ihre Revision nicht mehr aktuell gültig ist.

## Aktuelle Gültigkeitsprüfung

Die Policyquelle benötigt später neben Evaluation einen minimalen read-only
Lookup, der die aktuell aktive Revision für die Datenklasse liefert.

Die Clearanceauflösung muss die Policyrevision der aktuellen Decision gegen
diesen Lookup prüfen.

Fehlende, inaktive, abgelöste oder technisch unlesbare Revision sperrt eine
spätere Clearance fail-closed.

LQ-530 verdrahtet diese Prüfung noch nicht in LQ-508.

## Getrennte Administration

Policyadministration ist eine eigene Control-Plane-Fähigkeit.

Sie ist getrennt von Cleanup-Management-, Hold-, Recovery- und
Reference-Mutationsauthority sowie Research-, Membership- und Lifecycle-
Permissions.

Cleanupausführung oder eine aktive Session erteilt keine Policyauthority.

## SessionPrincipal

Ein authentifizierter `SessionPrincipal` identifiziert bei regulärer
Administration ausschließlich den Actor.

Er trägt keine Policyrolle, keine Mindestdauer und keinen Allowwert.

Der Administrationsadapter löst Actor, Datenklasse und aktuelle
Policyadministrationsauthority innerhalb jeder Mutation aus dem System of
Record neu auf.

## Separate Authority-Menge

Reguläre Policymutation benötigt eine eigene aktuelle
Retention-Policy-Management-Authority-Menge.

Diese Menge besitzt Bootstrap, regulären Lifecycle und geschlossene
Offline-Recovery als getrennte spätere Grenzen.

Ordinary Membership oder eine der vier LQ-525-Authority-Mengen ersetzt sie
nicht.

Widerruf muss jede spätere Policymutation beeinflussen.

## Initialer Bootstrap

Die erste Policyrevision und die erste Policyadministrationsauthority dürfen
später nur über einen separaten owner-kontrollierten Bootstrap entstehen.

Bootstrap ist ausschließlich zulässig, wenn weder Policyhistorie noch
Authority-Menge für die Datenklasse existiert.

Er darf atomar initiale Authority und initial aktive Policyrevision erzeugen.

Er erzeugt keine User-, Scope-, Workspace-, Membership- oder Rollenfakten.

## Reguläre Revisionserzeugung

Eine reguläre Mutation bindet Actor, Change-ID, erwartete aktuell aktive
Revision, neue intern erzeugte Revision, Datenklasse und neue Dauer.

Der Caller liefert keine neue Revision-ID, kein `eligible` und keine
Auswertungszeit.

Stale Erwartungen, ID-Kollisionen und abweichende Retries werden detailfrei
abgelehnt.

## Atomare Aktivierung

Eine neue Revision wird in derselben Transaktion vollständig persistiert und
als einzige aktive Revision veröffentlicht.

Es gibt keinen Zustand, in dem ein partieller Inhalt aktiv ist.

Die vorherige Revision bleibt immutable historisch, ist aber nach Commit nicht
mehr aktuell für neue Evaluationen.

Ein Aktivierungswiderruf darf optional zu keiner aktiven Revision führen, aber
niemals still eine ältere Revision reaktivieren.

## Keine stille Verkürzung

Eine reguläre Nachfolgerevision darf die aktuell aktive
Mindestaufbewahrungsdauer nicht verkürzen.

Gleiche oder längere Dauer ist zulässig, sofern die separate Authority und die
erwartete Revision aktuell sind.

Eine fachlich notwendige Verkürzung benötigt einen späteren ausdrücklich
separaten, höher kontrollierten Ausnahmevertrag und bleibt bis dahin
unsupported.

Damit kann reguläre Administration Cleanup nicht unbemerkt beschleunigen.

## Verlängerung wirkt sofort

Eine längere aktive Revision beeinflusst jede spätere Evaluation unmittelbar.

Eine unter der alten Revision erzeugte `eligible`-Decision darf unter der
neuen längeren Revision keine neue Clearance mehr tragen.

Eine neue Evaluation kann deshalb wieder `retain` ergeben.

Die Decisionhistorie bleibt unverändert erhalten.

## Deaktivierung

Kontrollierte Deaktivierung entfernt die aktive Policyquelle für spätere
Evaluationen und Clearances.

Sie löscht keine Revision, Decision oder Operation.

Reaktivierung einer früheren Revision ist keine reguläre Abkürzung und benötigt
eine neue explizite Revision beziehungsweise eine separat definierte Recovery.

## Offline-Recovery

Recovery darf ausschließlich einen bereits historisch gebundenen, weiterhin
sicheren Policy- und Authorityzustand unter einem geschlossenen
Notfallvertrag wiederherstellen.

Sie darf keine neue kürzere Dauer, neue Person oder freie Revision erfinden.

Recovery ist ein separater owner-kontrollierter Prozess ohne
`SessionPrincipal` und keine normale Policymutation.

Die genauen Recoveryvoraussetzungen folgen mit den späteren Typen und Ports.

## Append-only Historie

Policyrevisionen, Inhalte, Aktivierungen, Deaktivierungen, Changes,
Authority-Sets und Recoveries bleiben append-only beziehungsweise dauerhaft
nicht wiederverwendbar gebunden.

Es gibt keinen Delete-, Rewrite-, Rename- oder ID-Recyclingpfad.

Aufbewahrung gilt mindestens so lange, wie Decisions, Operationen, Clearances,
Claims, Outcomes oder Auditfakten darauf verweisen können.

LQ-530 legt keine konkrete Tabellenform oder Löschfrist fest.

## Detailfreie Ergebnisse

Neutrale Abwesenheit bleibt von fachlichem Conflict und technischer
Unverfügbarkeit unterscheidbar.

Ungültige, stale, unautorisierte oder lockout-verursachende Mutationen werden
detailfrei zusammengefasst.

SQL-, Policy-, Authority-, Actor- und Persistenzdetails verlassen die Grenze
nicht.

LQ-530 benennt keinen neuen technischen Exceptiontyp.

## Keine Policy-Discovery

Die spätere Betriebsgrenze listet oder sucht keine Policyrevisionen, Actors,
Authority-Mitglieder oder Datenklassen.

Bekannte IDs und erwartete Revisionen stammen aus getrennt kontrolliertem
Handoff.

Es gibt kein öffentliches HTTP-, Browser- oder freies Diagnoseinterface.

## Keine Folgeaktion

Policyerzeugung, Aktivierung oder Evaluation startet keine Retentionoperation,
Decision, Clearance, Retirement oder physische Cleanupwirkung.

Jeder Schritt benötigt seine eigene geschlossene Grenze und aktuelle Prüfung.

Der Policyadapter ruft LQ-529 nicht selbst auf.

## Keine Implementation in LQ-530

Dieser Slice ergänzt keinen Domainwert, Port, Adapter, Operator, Entry Point,
Tabelle, SQL oder Migration.

Appfactory, HTTP, Compose, Runbooks und Deployment bleiben unverändert.

Das Paketinventar bleibt bei 63 Entry Points und 68 Operatorfiles.

Head bleibt `20260826_0041` mit 41 linearen Migrationen.

## Tests

Statische Vertragstests prüfen immutable Revisionen, geschlossene Datenklasse,
positive monotone Dauer, aktuelle Einzelauswahl, deterministische
retain/eligible-Schwelle, getrennte Authority, Bootstrap/Lifecycle/Recovery,
keine stille Verkürzung, Widerruf und fehlende Folgeaktion.

Sie behaupten keine Policyimplementation oder PostgreSQL-Evidence.

## Nächster Slice

LQ-531 definiert die geschlossenen Policy-, Authority-, Bootstrap-, Lifecycle-
und Recoverywerte sowie minimale read-only und Mutationsports.

Persistenz, Evaluationadapter, Operator, Retirement und Deployment bleiben
getrennte Folgeslices.
