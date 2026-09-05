# LQ-198 — Authorized OIDC Trust Management Contract

## 1. Status und Ziel

LQ-198 ist eine reine Architekturentscheidung. Der Slice implementiert keine
Python-Typen, Ports, Adapter, Migration, Tabelle, SQL-Strategie, Route, CLI,
Settings, Tests oder Production-Verdrahtung.

LQ-192 speichert genau eine aktive OIDC-Client-Konfiguration, absichtlich
read-only. LQ-197 kann den OIDC-Prozess sicher betreiben, erzeugt aber keinen
Issuer-Trust. Offen ist damit, wer eine Konfiguration erstmalig aktivieren,
rotieren oder deaktivieren darf und wie laufende Logins bei Rotation
fail-closed bleiben.

Dieser Vertrag entscheidet die beobachtbare Autoritäts-, Revisions-,
Atomaritäts-, Wiederholungs- und Fehlersemantik vor jeder Mutation.

## 2. Eigene systemweite Authority

OIDC-Trust-Verwaltung erfordert eine dedizierte, persistente,
**systemweite** Management-Capability. Sie ist nicht workspacebezogen, weil die
aktive OIDC-Konfiguration die Authentifizierungsgrenze des gesamten Prozesses
bestimmt.

Keine bestehende Tatsache impliziert diese Capability:

- weder `research:read` noch `research:write`,
- keine gewöhnliche Workspace-Membership,
- keine workspacebezogene Onboarding-Management-Capability,
- kein Bootstrap-Nutzer oder Bootstrap-Workspace,
- keine Admission oder externe Identitätsbindung,
- keine erfolgreiche OIDC-Anmeldung oder Browser-Session.

Insbesondere darf die LQ-184-Capability nicht von „darf in einem Workspace
onboarden“ zu „darf globale Issuer-Trust-Grenzen ändern“ umgedeutet werden.

## 3. Akteur und aktuelle Auflösung

Der reguläre Anwendungsfall erhält einen bereits authentifizierten
`SessionPrincipal`. Dieser identifiziert den Akteur, gewährt aber keine
Authority. Die Management-Grenze löst selbst aus dem System of Record auf:

1. der Akteur existiert als dauerhafter interner Nutzer;
2. der Akteur ist aktuell aktiv;
3. die dedizierte systemweite OIDC-Trust-Capability ist aktuell aktiv.

Transport oder Aufrufer dürfen keinen alternativen UserId, Rollennamen,
Capability-Namen oder Allow-Boolean einspeisen. Ein Admin-Header, Environment-
Flag, IdP-Claim, E-Mail-Match oder Besitz einer Session ist kein Ersatz.

Entzug der Capability oder Deaktivierung des Akteurs sperrt jede später
begonnene Trust-Änderung. Kein Cache, Token oder langlebiger
Composition-Snapshot darf eine frühere Authority fortschreiben.

## 4. Bootstrap der ersten Trust-Authority

Die erste systemweite Trust-Authority kann nicht durch den regulären Pfad
entstehen, weil dieser bereits einen autorisierten Akteur voraussetzt. Dafür
ist eine spätere, eigene Offline-Bootstrap-Grenze erforderlich.

LQ-198 legt weder deren Signatur noch Operator-Authentisierung fest. Verbindlich
ist lediglich:

- keine HTTP-Route, kein Browser- oder Login-Bootstrap;
- kein Environment-Allow-Flag und kein Migration-Seed;
- keine automatische Vergabe an den ersten Login oder jedes Workspace-Admin;
- atomare Anlage genau einer initialen Authority-Tatsache;
- zustandsbasierte dauerhafte Schließung nach erfolgreicher Initialisierung;
- keine Wiederöffnung durch Deaktivierung, Restore oder Konfigurationswechsel.

Persistenzgrundlage und Bootstrap müssen vor der regulären Mutation in eigenen
Slices implementiert werden.

## 5. Erlaubte fachliche Änderungen

Die spätere reguläre Grenze kennt genau drei Absichten:

- **initial aktivieren:** wenn noch nie eine aktive Trust-Revision bestand;
- **rotieren:** eine neue vollständig validierte Revision atomar aktivieren;
- **deaktivieren:** die aktuelle Revision für neue Starts und Callbacks sperren.

Es gibt kein partielles Patchen einzelner Felder. Aktivierung und Rotation
erhalten immer eine vollständige, bereits als
`TrustedOidcClientConfiguration` validierte Konfiguration mit allen neun
Werten. Kein Feld wird aus Discovery, Browserinput, Host-/Forwarded-Headern,
Tokens oder der vorherigen Revision ergänzt.

Deaktivierung nimmt keine Ersatzkonfiguration und aktiviert keinen Default.
Löschen, Zurückrollen durch Überschreiben, Multi-Issuer-Listen und
browsergesteuerte Providerwahl gehören nicht zu diesem Vertrag.

## 6. Stabile Trust-Revision

Jede erfolgreich aktivierte Konfiguration erhält eine intern erzeugte,
global eindeutige und nicht wiederverwendbare Trust-Revision. Eine Revision
bezeichnet genau den unveränderlichen Satz aller neun Konfigurationswerte.

Die Revision wird nicht aus Issuer, Client-ID, Zeit, URL oder Konfigurationshash
abgeleitet und nicht vom Browser gewählt. Auch eine Rotation auf byteidentische
Werte erzeugt eine neue Revision, wenn sie als neuer fachlicher Vorgang
committet wird. Eine alte Revision wird niemals auf neue Werte umgebogen.

Historische Revisionen bleiben mindestens so lange identifizierbar, wie eine
Login-Transaktion, technische Wiederholung oder Sicherheitsauswertung darauf
verweisen kann. Konkrete Tabellen, Fristen und Löschverfahren bleiben später,
aber Restore oder Reimport dürfen eine alte Revision nicht unter neuer
Bedeutung reaktivieren.

## 7. Bindung von Login-Start und Callback

Die heutige Bindung nur an `expected_issuer` reicht für sichere Rotation nicht.
Bei gleichem Issuer könnten sich Client-ID, Redirect-URI, Token Endpoint, JWKS
URI, Algorithmen oder Clock Skew ändern, während eine alte Login-Transaktion
noch offen ist.

Darum muss ein späterer Slice die aktive Trust-Revision beim Login-Start
atomar mit der Pending-Transaktion speichern. Der Callback muss die aktuell
aktive Revision erneut lesen und bytegenau mit der erwarteten Revision der
beanspruchten Transaktion vergleichen, **bevor** der Authorization Code an
einen Token Endpoint gesendet oder ein JWKS geladen wird.

Fehlt die aktuelle Revision, ist sie deaktiviert oder stimmt sie nicht überein,
endet der Callback als neutrale Ablehnung ohne Netzwerkzugriff. Es gibt keinen
Fallback auf Issuer-Gleichheit, frühere Konfiguration, Cache oder Discovery.

Eine Rotation invalidiert damit alle noch offenen Starts der vorherigen
Revision fail-closed. Bereits beanspruchte Transaktionen werden nicht
zurückgesetzt und kein Authorization Code wird wiederholt präsentiert.

## 8. Atomare Änderung und Konkurrenz

Authority-Auflösung, Prüfung der aktuellen Trust-Revision, Anlage der neuen
unveränderlichen Revision, Aktivierung beziehungsweise Deaktivierung und
Speicherung der Änderungsentscheidung müssen in einer konsistenten
Schreibtransaktion wirksam werden oder gar nicht.

Ein Check-then-act über getrennte Transaktionen ist unzulässig. Gleichzeitige
Rotationen, Deaktivierung und Authority-Entzug werden durch das normative
Persistenzsystem geordnet. Genau eine Reihenfolge wird sichtbar; es gibt keinen
In-Process-Lock, automatischen Retry oder Last-write-wins ohne
Änderungsidentität.

Nach Commit sehen spätere Login-Starts und Callbacks ausschließlich den neuen
aktiven Zustand. Bereits erfolgreich verifizierte Identitäten und bestehende
Liquent-Sessions werden nicht rückwirkend umgedeutet; deren Widerruf bleibt die
separate Session-Grenze.

## 9. Änderungsidentität und Wiederholung

Jeder fachliche Trust-Wechsel besitzt eine intern erzeugte, persistente und
nicht wiederverwendbare Änderungsidentität. Sie ist kein öffentlicher
Idempotency-Key, kein OIDC-State und keine Trust-Revision.

Eine exakte technische Wiederholung derselben Änderungsidentität liefert die
bereits committete Entscheidung, ohne zweite Revision und ohne erneute
Authority-Auswertung, selbst wenn die Authority später entzogen wurde. So kann
ein unklarer Commit-Ausgang sicher aufgelöst werden.

Dieselbe Änderungsidentität mit anderer Absicht, anderen Konfigurationswerten
oder anderem Akteur ist ein detailfreier Konflikt. Eine neue fachliche Änderung
benötigt eine neue intern kontrollierte Änderungsidentität. Transport erzeugt
sie nicht spontan bei jedem Retry.

## 10. Ablehnung und technische Nichtverfügbarkeit

Unbekannter oder inaktiver Akteur, fehlende oder entzogene Authority,
unzulässiger Zustandsübergang und revisionsbezogene Vorbedingungsabweichung
enden als einheitliche detailfreie fachliche Ablehnung. Sie verrät weder
Authority-, Nutzer- noch Trust-Bestand.

Konflikt derselben Änderungsidentität mit anderem Inhalt bleibt davon getrennt.
Datenbank-, Transaktions-, Generator-, Decodierungs- oder Strukturfehler sind
detailfreie technische Nichtverfügbarkeit und dürfen nicht als Ablehnung oder
Erfolg getarnt werden.

Keine Antwort oder Exception enthält Akteur, Issuer, Client-ID, Endpoint,
Redirect-URI, Scope, Algorithmus, Revision, Änderungsidentität, SQL, DSN oder
ursprüngliche Fehlerkette. `BaseException` bleibt ungefangen.

## 11. Nicht enthalten und Folgeordnung

Nicht enthalten sind Modell- oder Portnamen, Signaturen, Exceptions, Adapter,
Migrationen, Tabellen, SQL, Tests, Route, CLI, Operator-Credential, Audit-Log,
Secret Store, Discovery, Multi-Issuer, Deployment oder Mutation.

Die sichere Folgeordnung lautet:

1. persistente systemweite OIDC-Trust-Authority und stabile Revisionstypen;
2. einmaliger Offline-Bootstrap der ersten Trust-Authority;
3. revisionsgebundene Login-Transaktion und Callback-Neuprüfung;
4. atomare autorisierte Aktivierungs-/Rotations-/Deaktivierungsgrenze;
5. kontrollierte Operator- oder interne Transportgrenze;
6. danach erneuter LQ-177-Abschlussaudit.

Membership-/Permission-Verwaltung bleibt eine getrennte Authority- und
Mutationskette. Kein Folgeslice darf beide globalen beziehungsweise
workspacebezogenen Verwaltungsdomänen in eine allgemeine Admin-Rolle mischen.
