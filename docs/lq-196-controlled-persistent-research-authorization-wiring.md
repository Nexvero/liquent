# LQ-196 — Controlled Persistent Research Authorization Wiring

## Ergebnis

LQ-196 bindet persistente Browser-Sessions und den persistenten Membership-
Lookup aus LQ-195 automatisch an die bestehenden Research-Read- und Research-
Start-Grenzen, sobald `create_app` eine Datenbank besitzt.

Damit fällt eine datenbankgestützte App für Research nicht mehr auf den
anonymen lokalen Entwicklungsweg zurück. Die bestehenden Session-, CSRF-,
Workspace- und Permission-Anwendungsfälle bleiben unverändert maßgeblich.

## Aktivierungsregel

Eine injizierte `database_engine` oder eine von der App aus `database_url`
erzeugte Engine aktiviert die persistente Research-Autorisierungscomposition,
wenn weder `research_sessions` noch `research_memberships` explizit gesetzt
sind.

Die Factory erzeugt dann:

- `DatabaseBrowserSessions` als aktuellen Session-Lookup;
- `DatabaseWorkspaceMemberships` als aktuellen Membership-Lookup.

Die beiden bestehenden Parameter bleiben ein unteilbares Paar. Nur einer von
beiden ist weiterhin ein Factory-Konfigurationsfehler. Sind beide explizit
gesetzt, behalten sie vollständig Vorrang und werden nicht mit persistenten
Adaptern gemischt.

Ohne App-Datenbank und ohne explizites Paar bleibt der bisherige lokale
Research-Modus bestehen. Diese Ausnahme ist an die bereits vorhandene lokale
Composition gebunden und wird durch LQ-196 nicht zu einer Production-
Fallbackentscheidung erweitert.

## Gemeinsame Session-Persistenz

Research-Authentifizierung und persistentes Logout verwenden innerhalb einer
App dieselbe `DatabaseBrowserSessions`-Instanz. Wenn LQ-194 zugleich das OIDC-
Wiring aktiviert, wird dessen bereits komponierter Session-Store ebenfalls
für Research und Logout wiederverwendet.

Damit greifen Session-Ausgabe nach Login, Research-Lookup und Logout-
Revocation auf dieselbe Engine und dieselbe persistente Tabelle zu. Es gibt
keinen zweiten Pool, keinen In-Memory-Session-Schatten und keine Kopie des
SessionPrincipal.

Eine Session identifiziert weiterhin nur den Nutzer. Sie trägt keine
WorkspaceId, Membership, Rolle oder Permission und friert keine Autorität bis
zu ihrem Ablauf ein.

## Read-Autorisierung

Status und Evidence verlangen bei datenbankgestützter App eine bekannte,
aktive, nicht abgelaufene und nicht widerrufene Browser-Session. Fehlendes,
unbekanntes, abgelaufenes oder widerrufenes Session-Cookie endet mit dem
bestehenden `401 authentication_required`.

Nach erfolgreicher Sessionauflösung wird zuerst der gespeicherte Research-Job
gefunden. Seine im unveränderlichen Experiment-Snapshot gespeicherte
`workspace_id` bestimmt den Membership-Lookup. Ein Request kann den zu
prüfenden Workspace nicht über Query, Header oder Cookie ersetzen.

Fehlende, inaktive oder unberechtigte Membership und ein unbekannter Job enden
weiterhin identisch als `404 research_job_not_found`. So wird weder die
Existenz einer fremden Ressource noch der konkrete Grund der Verweigerung
offengelegt.

## Start-Autorisierung

Die POST-Route bleibt weiterhin nur vorhanden, wenn ein Research-Resolver
explizit komponiert wurde. Eine Datenbank allein aktiviert keinen Runner und
keine lokale Datenquelle.

Ist die Route vorhanden, verlangt die persistente Composition:

- eine aktuelle Browser-Session,
- den an diese Session gebundenen CSRF-Nachweis,
- eine aktive Membership im Workspace des validierten neuen Snapshots,
- die aktuelle `research:write`-Permission.

Die Reihenfolge und Fehlercodes der bestehenden Anwendungsgrenze ändern sich
nicht. `research:read` allein erlaubt keinen Start. Der Resolver und Job-Store
werden erst nach erfolgreicher CSRF- und Autorisierungsprüfung erreicht.

## Aktueller Entzug

Jeder HTTP-Request löst die Session serverseitig neu auf. Jede Research-
Autorisierung liest anschließend Membership, Foundation-Status und Permissions
neu über LQ-195.

Ein committierter Session-Widerruf, eine Membership-Deaktivierung, ein
inaktiver Nutzer oder Workspace und ein Permission-Entzug wirken deshalb auf
die nächste Anfrage. Es gibt keinen Route-, Middleware- oder Process-Cache für
Autorität.

Bereits abgeschlossene Research-Jobs und Evidence werden durch Entzug nicht
gelöscht oder umgeschrieben; ihre spätere Sichtbarkeit wird erneut entschieden.

## Ownership und Factory-Verhalten

Die Factory besitzt keine injizierte Engine und disposed sie nicht. Eine intern
aus `database_url` erzeugte Engine behält den vorhandenen Lifespan-gebundenen
Besitz. Die Research-Adapter erzeugen und schließen keine Engine selbst.

Composition führt keinen Session- oder Membership-Lookup beim App-Aufbau aus.
Die Datenbank wird erst durch Readiness oder einen Request benutzt. Es gibt
keinen Startup-Seed, Bootstrap, Membership-Import oder implizite Freigabe.

Explizite Research-Abhängigkeiten bleiben für isolierte Tests und bewusste
manuelle Composition erhalten. Das Datenbank-Wiring überschreibt sie nicht und
ergänzt kein fehlendes Gegenstück.

## Technische Fehlergrenze

Neutrale Authentifizierungs- und Autorisierungsentscheidungen behalten ihre
bestehenden 401-, 403- und 404-Verträge. Technische Session- oder Membership-
Nichtverfügbarkeit wird nicht als fehlende Membership oder unbekannte Session
getarnt und erzeugt keine fachliche Antwort mit irreführendem Zustand.

Persistenzfehler bleiben in ihren Adaptern detailfrei. Kein Session-Identifier,
CSRF-Wert, UserId, WorkspaceId, Permission, SQL oder DSN-Detail wird in eine
fachliche Fehlermeldung übernommen.

## Tests

Die LQ-196-Tests belegen:

- eine datenbankgestützte App verweigert anonymen Research-Read mit 401,
- persistente Session plus aktive Membership und `research:read` erlauben den
  Jobstatus im serverseitig gespeicherten Workspace,
- committierter Permission-Entzug versteckt einen zuvor sichtbaren Job beim
  nächsten Request neutral als 404,
- vollständig explizite Research-Abhängigkeiten behalten Vorrang.

Die bestehenden Research-Read-, Research-Start-, LQ-177-Logout- und LQ-194-
OIDC-Wiring-Tests laufen unverändert weiter. Damit ist sowohl der lokale
explizite Modus als auch die persistente Production-Composition nachgewiesen.

## Bewusst nicht enthalten

- keine Membership- oder Permission-Mutation, Einladung oder Rollenverwaltung,
- keine automatische Membership aus Bootstrap, Onboarding, Admission oder Login,
- kein persistenter Research-Job- oder Evidence-Store,
- kein neuer Resolver, Runner oder Datenquellenzugriff,
- keine neue Route, Middleware oder Änderung öffentlicher Fehlercodes,
- kein Audit-Log, keine Admin-API und kein Operator-CLI,
- kein Deployment und keine Shared-Environment-Freigabeentscheidung.

## Nächster Schritt

Die zuvor offenen persistenten Identity-, OIDC-, Session- und Research-
Autorisierungsgrundlagen sind jetzt kontrolliert verdrahtet. Der nächste Slice
kann LQ-177 als Ganzes gegen seine ursprünglichen Blocker auditieren und den
Status präzise abschließen oder verbleibende konkrete Lücken benennen.
Reguläre Membership-Mutation bleibt unabhängig davon ein späterer expliziter
Control-Plane-Slice.
