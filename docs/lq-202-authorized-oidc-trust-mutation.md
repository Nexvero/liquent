# LQ-202 — Authorized OIDC Trust Mutation

## Ergebnis

LQ-202 implementiert die reguläre persistente Grenze zur autorisierten
Aktivierung, Rotation und Deaktivierung des globalen OIDC-Trusts.

Authority-Auflösung, Zustandsvorbedingung, Anlage einer unveränderlichen
Revision, Umschaltung des aktiven Singletons und Speicherung der
Änderungsentscheidung werden in genau einer Datenbanktransaktion geordnet.

Der Slice ergänzt keine Route, CLI, Settings-Option oder Operator-
Authentisierung. Er ist die interne atomare Anwendungsgrenze, auf der eine
solche kontrollierte Grenze später aufbauen kann.

## Fachliche Absichten

`OidcTrustChangeKind` besitzt genau drei Werte:

- `ACTIVATE` aktiviert den ersten revisionsgebundenen Trust;
- `ROTATE` ersetzt die zuletzt ausgewählte Revision durch eine neue vollständige
  Revision;
- `DEACTIVATE` sperrt die exakt erwartete aktive Revision.

Es gibt keine generische Patch-Operation. Aktivierung und Rotation verlangen
jeweils eine bereits vollständig validierte
`TrustedOidcClientConfiguration`. Deaktivierung akzeptiert keine
Konfiguration.

Aktivierung verlangt, dass noch kein aktiver Singleton-Bestand existiert, und
nimmt keine erwartete Revision. Sie repariert oder übernimmt keinen
revisionslosen Legacy-Singleton.

Rotation und Deaktivierung verlangen eine interne `OidcTrustRevisionId` als
optimistische fachliche Vorbedingung. Sie muss exakt der im Singleton zuletzt
ausgewählten Revision entsprechen.

Deaktivierung ist nur bei aktuell aktivem Trust zulässig. Rotation kann auch
einen zuvor deaktivierten Trust kontrolliert reaktivieren, aber nur aus dessen
bewahrter exakter Vorgängerrevision und immer durch Anlage einer neuen Revision.

## Actor und Authority

`change_trust` erhält einen authentifizierten `SessionPrincipal`. Dieser
identifiziert ausschließlich den Actor und gewährt selbst keine Authority.

Der Adapter löst in derselben Schreibtransaktion aus dem System of Record auf:

- der Actor existiert als interner Nutzer,
- der Actor ist aktuell aktiv,
- seine dedizierte globale OIDC-Trust-Management-Authority ist aktuell aktiv.

Workspace, Membership, Research-Permission, Onboarding-Capability, Rolle,
Issuer, IdP-Claim, Header und caller-supplied Allow-Boolean können Authority
weder ausdrücken noch ersetzen.

Unbekannter oder inaktiver Actor sowie fehlende oder entzogene Authority
ergeben dasselbe neutrale `None`. Es wird keine Revision erzeugt und kein
Trust-Zustand verändert.

Ein committierter Authority- oder Actor-Entzug sperrt jede danach neu
begonnene Änderung. Es gibt keinen Authority-Cache und keine Übernahme aus der
Session.

## Interne Änderungsidentität

Jede Änderung trägt eine stabile repr-freie `OidcTrustChangeId`. Sie ist ein
interner Wiederholungsanker, keine öffentliche Berechtigung, kein OIDC-State
und keine Trust-Revision.

Eine exakt wiederholte bereits committete Änderungs-ID liefert dieselbe
`AuthorizedOidcTrustChange` zurück. Dabei wird weder Authority erneut geprüft
noch eine zweite Revision erzeugt.

Diese Reihenfolge ist absichtlich: Nach einem unklaren Commit-Ausgang kann die
ursprüngliche Entscheidung noch sicher aufgelöst werden, auch wenn die
Authority inzwischen entzogen wurde.

Dieselbe Änderungs-ID mit anderem Actor, anderer Absicht, anderer erwarteter
Revision oder anderer vollständiger Konfiguration erzeugt den detailfreien
`OidcTrustChangeConflict`.

Der Konflikt enthält weder Änderungs-ID noch Actor, Revision oder
Konfigurationswert und bewahrt keine ursprüngliche Fehlerkette.

## Neue Revisionen

Bei erfolgreicher Aktivierung oder Rotation erzeugt der injizierte sichere
Materialgenerator genau eine neue `OidcTrustRevisionId`.

Alle neun Konfigurationswerte werden unverändert in
`oidc_trust_revisions` gespeichert. Die Revision ist historisch unveränderlich
und wird nie auf andere Werte umgebogen.

Auch eine Rotation auf fachlich identische Konfigurationswerte erzeugt eine
neue Revision. Die Identität bezeichnet den neuen committeten Trust-Stand und
wird nicht aus Inhalt, Issuer, Zeit oder Hash abgeleitet.

Revision und vollständige Konfiguration werden anschließend gemeinsam im
LQ-201-Singleton aktiviert. Spätere Login-Starts sehen nur diesen Snapshot.
Offene Logins der Vorgängerrevision scheitern beim Callback vor Netzwerkzugriff.

Deaktivierung erzeugt keine Revision. Sie setzt ausschließlich den aktiven
Status auf inaktiv und bewahrt die zuletzt ausgewählte Revision samt
historischer Konfiguration für Audit, Retry und kontrollierte Folgerotation.

## Persistente Änderungsentscheidung

Migration `20260812_0011` ergänzt die leere Tabelle
`authorized_oidc_trust_changes`.

Sie speichert:

- die nicht wiederverwendbare Change-ID,
- die interne UserId des Actors,
- die Absicht,
- die erwartete Vorgängerrevision, falls erforderlich,
- die erzeugte Ergebnisrevision bei Aktivierung oder Rotation.

Foreign Keys binden Actor und Revisionen an die dauerhaften Foundation-Fakten.
Check Constraints erzwingen die zulässigen Formen der drei Absichten.

Die vollständige Eingabe einer Aktivierung oder Rotation bleibt über die
unveränderliche Ergebnisrevision rekonstruierbar. Ein Retry vergleicht alle
neun Werte und akzeptiert keinen nur teilweise gleichen Trust.

Die Migration erzeugt keinen Actor, keine Authority, Revision, aktive
Konfiguration oder Änderungsentscheidung und enthält keinen Seed.

## Atomarität und Konkurrenz

Für eine neue Änderung liegen in derselben Transaktion:

1. aktuelle Authority-Auflösung,
2. Sperre und Prüfung des Trust-Singletons,
3. Erzeugung und Speicherung der neuen Revision, falls erforderlich,
4. Aktivierung, Rotation oder Deaktivierung,
5. Speicherung der unveränderlichen Änderungsentscheidung.

Ein Fehler in einem Schritt rollt Revision, Singleton und Entscheidung
gemeinsam zurück. Es gibt keinen Check-then-act über mehrere Transaktionen,
keinen In-Process-Lock und keinen automatischen Retry.

PostgreSQL sperrt Entscheidungs- und Singletontabellen in fester Reihenfolge
und löst danach Actor und Authority mit Zeilensperren auf. Gleichzeitige
Änderungen erhalten genau eine sichtbare Reihenfolge.

Eine konkurrierende exakte Wiederholung wird nach dem Warten erneut aus dem
committeten Entscheidungsbestand gelesen. Beide Aufrufer erhalten dieselbe
Revision; keine zweite Generatorziehung oder Revision wird wirksam.

SQLite deckt die sequenzielle Fach-, Rollback- und Retry-Semantik ab.
PostgreSQL bleibt die normative Konkurrenzgrenze.

## Ablehnung und technische Nichtverfügbarkeit

Neutrales `None` umfasst ohne Detailunterscheidung:

- fehlende aktuelle Authority,
- inaktiven oder unbekannten Actor,
- unzulässigen aktuellen Trust-Zustand,
- fehlende oder abweichende erwartete Revision.

Eine ungültige strukturelle Operationsform, falsches Generatormaterial,
beschädigte Persistenz sowie Datenbank-, Constraint-, Encoding-,
Transaktions- oder Generatorfehler werden als detailfreie
`OidcTrustChangeStoreUnavailable` gemeldet.

Weder Ergebnis noch Exceptions oder Adapter-`repr` enthalten Actor,
Change-ID, Revision, Issuer, Client-ID, Endpoint, Redirect-URI, Scope,
Algorithmus, SQL, Tabelle, Constraint, Host, Port oder DSN. `BaseException`
bleibt ungefangen.

## Tests

Die SQLite-Tests belegen:

- strukturelle Erfüllung des neuen Ports,
- autorisierte erste Aktivierung und exakten aktiven Snapshot,
- exakten Retry ohne zweite Authority-Auflösung oder Generatorziehung,
- Konflikte bei geändertem Actor, Intent, Vorgänger oder Trust-Inhalt,
- neutrale Ablehnung fehlender und entzogener Authority,
- Rotation nur von der exakt erwarteten Revision,
- Deaktivierung ohne Verlust historischer Revisionen,
- kontrollierte Folgerotation nach Deaktivierung,
- vollständigen Rollback bei Generatorfehler,
- detailfreie technische Nichtverfügbarkeit,
- leere additive Migration und Head `20260812_0011`.

Der markierte PostgreSQL-Test startet zwei echte konkurrierende identische
Aktivierungen. Beide konvergieren auf genau eine Entscheidung und eine
Revision, ohne technischen Fehler oder zweiten Trust-Stand.

## Bewusst nicht enthalten

- keine Vergabe, Übertragung, Reaktivierung oder Entzug der Trust-Authority,
- keine HTTP-Route, CLI oder Operator-Credential,
- kein Environment-Allow und keine Startup-Mutation,
- keine Discovery, Multi-Issuer-Liste oder Client-Secret-Verwaltung,
- keine Nutzer-, Workspace-, Membership- oder Permission-Mutation,
- kein Session-Widerruf und keine rückwirkende Identitätsänderung,
- kein Deployment oder Production-Operator-Wiring.

## Nächster Schritt

LQ-203 sollte eine kontrollierte interne oder Offline-Operatorgrenze für
LQ-202 definieren und implementieren. Sie muss Change-IDs intern stabil
erzeugen und für technische Wiederholung bewahren, ohne Browser-, Session-
oder Environment-Werte in Authority oder Trust-Konfiguration umzudeuten.
