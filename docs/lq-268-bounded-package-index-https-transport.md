# LQ-268 — Bounded Package-Index HTTPS Transport

## Ergebnis

LQ-268 implementiert den begrenzten HTTPS-Transport für die in LQ-267
eingefrorene Package-Index-Schnittstelle.

Der Transport führt pro Aufruf exakt einen read-only GET oder einen
create-only PUT aus. Redirects, automatische Retries, freie URLs und rohe
Providerantworten bleiben ausgeschlossen.

## Transportgrenze

`HttpPackageIndexProviderTransport` implementiert ausschließlich:

- `inspect_package`;
- `create_package`.

Er besitzt keine Delete-, Replace-, Yank-, List-, Search-, Login- oder
Discovery-Methode.

Der Transport wird mit einem kontrolliert erzeugten `httpx2.Client`, einer
festen Policy und optional einer Monotonie-Uhr injiziert.

## Feste Versionsressource

Beide Operationen verwenden dieselbe deterministische Ressource:

```text
{origin}/v1/targets/{target}/{package}/{version}
```

Target, Paket und Version werden als einzelne URL-Segmente percent-encoded.

Der Origin stammt ausschließlich aus der bereits validierten lokalen
`PackageIndexProviderConfiguration`. Weder Caller noch Providerantwort können
Host, Port oder Pfad ersetzen.

## Read-only Inspection

Inspection verwendet genau einen HTTP-GET auf die exakte Versionsressource.

Nur folgende Antworten sind verwertbar:

- `200` mit streng typisiertem kanonischem JSON-Record;
- `404` mit vollständig leerem Body als bestätigte Abwesenheit.

Redirects, Authentication-/Authorization-Fehler, Konflikte, Rate-Limits,
Serverfehler und jeder andere Status sind technische Nichtverfügbarkeit.

Ein 404 mit Providertext oder anderem Body ist ausdrücklich keine bestätigte
Abwesenheit.

## Kanonische Inspection-Antwort

Eine erfolgreiche 200-Antwort enthält exakt:

- `canonical_artifact_id`;
- `provider_revision`;
- `package_name`;
- `package_version`;
- `wheel_sha256`;
- `visible`.

Zusätzliche, fehlende oder doppelte JSON-Member werden abgelehnt.

Der Transport erzeugt daraus ausschließlich ein
`PackageIndexArtifactRecord`. Bytegleichheit und Konfliktklassifikation bleiben
bei den bestehenden Publication-Grenzen.

## Create-only PUT

Create verwendet genau einen HTTP-PUT auf dieselbe exakte
Versionsressource.

Die Requestheader enthalten:

- `If-None-Match: *` als Create-only-Bedingung;
- den unveränderten stabilen `Idempotency-Key`;
- `Content-Type: application/json`;
- `Accept: application/json`;
- `Accept-Encoding: identity`.

Es gibt keinen PUT ohne Create-only-Bedingung und keinen zweiten Versuch im
Transport.

## Deterministische Payload

Die Create-Payload ist kanonisches kompaktes JSON mit sortierten Keys.

Sie bindet:

- Bundle-Dateiname;
- Bundle-, Signatur- und Promotion-Evidence-Bytes als Base64;
- Bundle-, Wheel-, Checksums-, Signatur- und Evidence-SHA-256.

Der Transport verändert oder rekonstruiert keine Artefakte und lädt keine
zusätzlichen Pfade.

## Requestgrößenlimit

Die vollständig serialisierte Create-Payload wird vor jedem Netzwerkzugriff
gegen `request_max_bytes` geprüft.

Eine zu große Payload erreicht weder Client noch Provider. Das Limit ist ein
positiver expliziter Policywert und nicht callersteuerbar.

## Create-Acknowledgement

Nur HTTP `201` mit exakt einem JSON-Member `provider_request_id` ist eine
syntaktisch gültige Create-Acknowledgement.

200, 202, 204, 409 und alle Fehlerstatus werden nicht als Erfolg
interpretiert. Insbesondere ist `already exists` kein Receipt.

Die Provider-Request-ID wird in `PackageIndexCreateRecord` überführt und bleibt
über die LQ-267-Grenze repr-frei.

## Credential-Übertragung

Das kurzlebige Credential wird ausschließlich als Bearer-Authorization-Header
für den konkreten Request verwendet.

Credentials mit Whitespace oder Steuerzeichen sind bereits in der lokalen
Configuration unzulässig.

Client-Cookies werden aus jedem Request entfernt. Clientseitige Auth wird beim
Send explizit deaktiviert, damit kein zweites Authentisierungsschema injiziert
wird.

Credential, Header und Origin erscheinen weder in Resultaten noch Exceptions
oder `repr`.

## Keine Redirects

Jeder Request wird mit `follow_redirects=False` gesendet.

3xx-Antworten sind technische Nichtverfügbarkeit. Authorization-Header und
Payload können dadurch nicht automatisch an einen anderen Origin gelangen.

## Keine automatische Wiederholung

Jeder Methodenaufruf baut und sendet höchstens einen HTTP-Request.

Der Transport besitzt keine Retry-Schleife, kein Backoff, kein Mirror-
Fallback und keine zweite Idempotenzidentität.

Sobald der PUT aufgerufen wurde, übernimmt die persistente LQ-257-/LQ-262-
Kette jeden möglichen Effekt als `outcome_unknown`.

## Zeitgrenzen

`PackageIndexHttpPolicy` verlangt positive:

- Connect-Zeit;
- Read-Zeit;
- Gesamtzeit;
- Response-Größe;
- Request-Größe.

Connect- und Read-Zeit dürfen die Gesamtzeit nicht überschreiten.

Der Client erhält begrenzte Connect-, Read-, Write- und Poolwerte. Zusätzlich
prüft eine injizierbare Monotonie-Uhr die Gesamtzeit zwischen allen
wesentlichen I/O-Schritten.

Nicht finite, boolesche, fehlerhafte oder rückwärts laufende Uhrwerte führen
fail-closed zu technischer Nichtverfügbarkeit.

## Antwortgrößenlimit

`Content-Length` muss, falls vorhanden, ausschließlich aus ASCII-Ziffern
bestehen und innerhalb `response_max_bytes` liegen.

Zusätzlich wird der Body inkrementell gezählt. Eine fehlende oder falsche
kleinere Längenangabe kann das tatsächliche Limit nicht umgehen.

Ein deklarierter Oversize-Body wird abgelehnt, bevor ein Chunk gelesen wird.

## Framing und Encoding

Nicht-leere verwertbare Antworten benötigen `application/json` mit optionalem
UTF-8-Charset.

Andere Media Types, ungültige Charsetwerte und komprimierte Antworten werden
abgelehnt. `Accept-Encoding: identity` hält das Byte-Limit auf die tatsächlich
übertragenen Bytes bezogen.

## Striktes JSON

Antworten werden genau einmal als UTF-8 und JSON dekodiert.

Akzeptiert werden nur Objekte mit der exakt erwarteten Membermenge. Doppelte
Member, Arrays, freie Texte, zusätzliche Felder und ungültiges UTF-8 sind
technische Nichtverfügbarkeit.

Providertexte werden nicht als fachliche Entscheidung interpretiert.

## Ressourcenabschluss

Jede erhaltene Streaming-Response wird in einem `finally`-Pfad geschlossen,
auch bei Status-, Header-, Body-, JSON-, Größen- oder Deadlinefehlern.

Der injizierte Client bleibt Eigentum der späteren Worker-Composition und wird
nicht durch einen Einzelaufruf geschlossen.

## Detailfreie Fehlergrenze

Alle normalen Client-, DNS-, TLS-, Timeout-, Framing-, Status-, Parsing- und
Providerfehler werden als `ReleasePublicationProviderUnavailable` ohne Ursache
oder Kontext weitergegeben.

Keine URL, Credential, Providerantwort, Request-ID oder Payload gelangt in die
Exception.

## Keine Production-Composition

LQ-268 erzeugt keinen realen `httpx2.Client`, liest keine Credential-Datei und
aktiviert keinen Worker.

Tests verwenden ausschließlich `MockTransport`; es erfolgt kein echter
Netzwerk- oder Providerzugriff.

## Keine Persistenz oder Migration

Der Slice verändert keine Publication-Tabelle, SQL-Abfrage, Migration oder
Bootstrap-Entscheidung.

Head bleibt `20260819_0024` mit 24 linearen Migrationen.

## Bewusst nicht enthalten

LQ-268 implementiert keine:

- Credential-Source oder Dateirechteprüfung;
- Client-/Worker-Composition;
- CLI, Scheduler, Queue oder Service-Unit;
- konkrete Production-Origin-Konfiguration;
- Proxy-, Custom-CA- oder Redirectfreigabe;
- Receipt-, Reconciliation- oder Retry-Logik;
- Delete-, Replace-, Yank- oder Deploymentoperation.

## Nachweis

34 neue Transporttests belegen:

- exakt geformten GET und create-only PUT;
- exakte URL-Segmentbindung;
- Entfernung geerbter Cookies;
- Bearer-Credential und unveränderte Idempotenz;
- leeren 404 als einzige Abwesenheit;
- strikte Status- und JSON-Klassifikation;
- deterministische Base64-Payload und Hashbindung;
- Request- und inkrementelle Responsegrößenlimits;
- Media-Type-, Charset- und Encodingregeln;
- keine Redirects oder automatischen Retries;
- Responseabschluss auf allen Pfaden;
- Gesamtdeadline und monotone Clock;
- detailfreie Transportfehler.

Die vollständige Pflichtsuite mit PostgreSQL 16 besteht:

```text
3289 passed, 534 warnings
```

Der nächste Slice LQ-269 implementiert die kontrollierte owner-only
Credential-Source und vollständige lokale Client-/Adapter-Composition. Worker-
CLI und Production-Wiring bleiben getrennt.
