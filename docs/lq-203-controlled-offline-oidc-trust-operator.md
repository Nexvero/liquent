# LQ-203 — Controlled Offline OIDC Trust Operator

## Ergebnis

LQ-203 stellt LQ-202 als eigenständige Offline-Operatorgrenze bereit. Der neue
Prozess erzeugt stabile interne Change-IDs und wendet eine zuvor bewahrte,
vollständig validierte Änderungsdatei gegen die persistente atomare
Trust-Mutation an.

Es entsteht keine HTTP-Route, Browserfunktion, Startup-Mutation oder
Environment-Authority. Der Control-Plane-Prozess importiert oder startet die
Operatorgrenze nicht.

## Zweistufiger Ablauf

`liquent-oidc-trust new-change-id` erzeugt genau eine kryptografisch sichere
`OidcTrustChangeId` über den bestehenden LQ-199-Materialgenerator.

Der Operator übernimmt diese ID in eine kontrolliert gespeicherte Request-
Datei, bevor die Änderung ausgeführt wird. Die Datei ist danach der stabile
Retry-Anker.

`liquent-oidc-trust apply` erzeugt niemals spontan eine neue Change-ID. Bei
unklarem technischen Ausgang wird exakt dieselbe Datei erneut angewendet.
Damit kann LQ-202 die bereits committete Entscheidung wiederfinden, ohne eine
zweite Revision oder erneute Authority-Auswertung.

Eine neue ID bezeichnet immer einen neuen fachlichen Änderungsversuch. Das Tool
besitzt keinen automatischen Retry und verändert eine Request-Datei nicht.

## Strikte Request-Datei

Die JSON-Wurzel enthält exakt:

- interne Actor-UserId,
- bewahrte Change-ID,
- `activate`, `rotate` oder `deactivate`,
- erwartete Revision oder `null`,
- vollständige Konfiguration oder `null`.

Unbekannte und fehlende Felder werden abgelehnt. Strings werden nicht getrimmt,
normalisiert, case-gefaltet oder als URLs neu interpretiert.

Aktivierung verlangt keine Vorgängerrevision und alle neun Trust-Werte.
Rotation verlangt die erwartete Vorgängerrevision und alle neun Trust-Werte.
Deaktivierung verlangt die erwartete Revision und exakt `configuration: null`.

Scopes und erlaubte Algorithmen müssen nichtleere JSON-Listen nichtleerer
Strings sein. Clock Skew ist eine ganzzahlige Sekundenzahl und wird erneut vom
bestehenden Domainmodell auf den Bereich null bis fünf Minuten geprüft.

Es gibt kein partielles Patchen, Discovery, Defaulting, Übernehmen aus dem
aktiven Trust oder browsergewählte Providerinformation.

## Private Dateigrenze

Request und Datenbank-URL müssen vorhandene lokale reguläre Dateien sein, die
nur für ihren Owner zugänglich sind. Group-/World-Bits und symbolische Links
werden fail-closed abgelehnt.

Die Datenbank-URL wird nicht als Kommandozeilenwert oder Environment-Einstellung
akzeptiert. Dadurch erscheint sie weder in der Prozessargumentliste noch als
neue Runtime-Konfiguration.

Die Grenze liest die URL ausschließlich zum Aufbau ihrer eigenen Engine. Sie
migriert nicht, prüft keinen Provider und startet keinen HTTP-Client. Die Engine
wird bei Erfolg, Ablehnung und Fehler geschlossen.

Dateierstellung, Secret-Bereitstellung, OS-Operator-Authentisierung,
Aufbewahrung und sichere Löschung bleiben Deployment-/Betriebsverantwortung und
sind im Runbook ausdrücklich vorgeordnet.

## Keine neue Authority-Logik

Die Request-Datei enthält die interne Actor-ID, aber keinen Allow-Boolean,
Capability-Namen, Rolle, Workspace oder IdP-Claim.

Die Operatorgrenze konstruiert daraus nur einen `SessionPrincipal`. Dieser
identifiziert den Actor und autorisiert nichts.

Alle Entscheidungen über aktiven Actor, globale Trust-Authority, aktuellen
Trust-Zustand und erwartete Revision verbleiben ausschließlich bei
`DatabaseAuthorizedOidcTrustChanges` innerhalb derselben LQ-202-Transaktion.

OS- oder Datenbankzugriff ersetzt diese Authority nicht. Fehlt sie, endet die
Anwendung neutral abgelehnt und erzeugt keine Revision.

## Ausgaben und Exit-Codes

Erfolgreiche neue Änderungen und exakte committete Wiederholungen geben nur
`{"outcome":"applied"}` aus und enden mit Exit 0.

Neutrale fachliche Ablehnung gibt nur `{"outcome":"rejected"}` aus und endet
mit Exit 5. Actor-, Authority-, Trust- oder Revisionsbestand werden nicht
unterschieden.

Ungültige Eingabe, Change-ID-Konflikt und technische Nichtverfügbarkeit erhalten
getrennte konstante detailfreie Fehlercodes und unterschiedliche non-zero
Exits. Provider-, Konfigurations-, Request-, Datenbank- und Exceptiondetails
werden nicht reflektiert.

`argparse` darf ausschließlich Kommando- und Dateipfadfehler melden; Trust-
Werte selbst werden nie als Argumente angenommen. `BaseException` bleibt
ungefangen.

## Prozessbesitz und Fehler

Jeder `apply`-Aufruf baut genau eine eigene Datenbank-Engine und schließt sie im
`finally`. Injizierte Engines der transportfreien Test-/Anwendungsfunktion
bleiben dagegen im Besitz des Aufrufers.

Fehlendes oder veraltetes Schema wird nicht automatisch repariert. Es endet wie
andere Datenbankfehler als bestehende detailfreie technische
Nichtverfügbarkeit.

Die Grenze fängt unerwartete reguläre Exceptions am Prozessrand ab und
vereinheitlicht sie, ohne Cause, SQL, DSN oder Eingabewert auszugeben.

## Packaging und Betrieb

Der additive Console Entry Point heißt `liquent-oidc-trust`. Er importiert
weder ASGI-App noch OIDC-Runtime-Wiring und führt bei `new-change-id` keinerlei
Datenbank- oder Providerzugriff aus.

Das Runbook `operations/runbooks/oidc-trust-management.md` beschreibt
Vorbedingungen, private Dateien, exakte Aktivierungs-, Rotations- und
Deaktivierungsformen, Retry-Regel, neutrale Ausgaben und Cleanup.

Es enthält keine reale URL, UserId, Change-ID, Revision oder Provider-
Konfiguration und ist keine automatische Deployment-Prozedur.

## Tests

Die Tests belegen:

- sichere Erzeugung einer opaken Change-ID ohne Datenbankzugriff,
- exakte unveränderte Parsing- und Domainvalidierung,
- Ablehnung unbekannter, fehlender und falsch geformter Felder,
- Owner-only-Anforderung und Ablehnung unsicherer Dateirechte,
- repr-freie Request-Daten,
- erfolgreiche Aktivierung über die reale LQ-202-Persistenz,
- exakten Retry derselben Datei nach Authority-Entzug ohne zweite Revision,
- neutrale Authority-Ablehnung ohne Konfigurationsdetail,
- konstante detailfreie Eingabefehler und Exit-Codes,
- unveränderte bestehende CLI- und Release-Verträge.

## Bewusst nicht enthalten

- keine Operator-Weboberfläche oder API,
- keine interaktive Eingabe oder automatische Request-Erzeugung,
- keine Speicherung der Change-ID außerhalb der LQ-202-Entscheidung,
- keine Vergabe oder Mutation globaler Trust-Authority,
- keine automatische Migration, Discovery oder Provider-Connectivity-Prüfung,
- kein Client Secret, Secret Store oder Schlüsselmanagement,
- kein Deployment, Neustart oder Session-Widerruf,
- keine Membership-, Permission-, Nutzer- oder Workspace-Mutation.

## Nächster Schritt

LQ-204 sollte den verbliebenen LQ-177-Abschlussblocker nach implementierter
Trust-Mutation und Operatorgrenze erneut vollständig auditieren. Dabei ist zu
prüfen, ob noch eine sichere reguläre Authority-Mutation oder ein explizites
Deployment-/Recovery-Gate fehlt; beides darf nicht stillschweigend in diese
Offline-Grenze aufgenommen werden.
