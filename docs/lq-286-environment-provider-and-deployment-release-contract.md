# LQ-286 — Environment Provider and Deployment Release Contract

## Ergebnis

LQ-286 definiert die noch fehlende environmentbezogene Freigabe vor einem
echten Package-Providerzugriff.

Die interne Publication-Prozesskette aus LQ-285 ist geschlossen. Daraus folgt
aber weder die Freigabe eines konkreten Origins noch eines Credentials, Hosts,
Netzpfads oder Deploymenttargets.

Dieser Slice implementiert keinen Providerzugriff, Preflight-Command,
Deployment, Upload oder Runtime-Schalter.

## Getrennte Entscheidungsgrenze

Environment-Freigabe ist eine bewahrte betriebliche Entscheidung außerhalb des
Publication-Requests.

Sie darf nicht als caller-geliefertes `allow`, Rolle, Capability, Environment-
Variable oder Datenbankflag in die bestehenden Operatoren eingespeist werden.

Die geschlossenen Operatoren prüfen weiterhin ausschließlich ihre technischen
und persistenten System-of-Record-Verträge.

Die Betriebsorganisation entscheidet separat, ob diese Operatoren in einem
konkreten Environment überhaupt aufgerufen werden dürfen.

## Freigabeobjekt

Eine Freigabe bindet mindestens unveränderlich:

- eindeutiges Environment und verantwortliche Betriebsgrenze;
- exakt kanonischen HTTPS-Origin;
- exakt einen Package-Namen und einen Zielnamen;
- Credential-Identität und Scope, niemals den Credentialwert;
- erwartetes Providerprotokoll und create-only Semantik;
- Netzwerk-, DNS-, TLS- und Trustpfad;
- freigegebenen Publication-Host und Prozessaccount;
- geprüfte Anwendungsversion und Operational-Bundle-Identität;
- Gültigkeitsbeginn, Ablauf oder Reviewtermin;
- unabhängige Freigaben und Evidence-Referenzen.

Die Freigabe ist kein Publication-Handoff und enthält keine Handoff-,
Execution-, Attempt- oder Receipt-ID.

## Unabhängige Reviews

Mindestens die folgenden Perspektiven müssen getrennt bestätigt sein:

- Provider-/Package-Ownership und Zielsemantik;
- Security für Credential, TLS, Egress und Hostgrenze;
- Operations für Readiness, Monitoring, Incident und Recovery;
- Release-Verantwortung für exakt das freizugebende Artefakt und Environment.

Eine einzelne technische Identität oder frühere positive Publication-Evidence
ersetzt diese Reviews nicht.

Die konkrete Organisationsrolle wird nicht im Produktmodell kodiert. Der
bewahrte Nachweis muss jedoch Actor, Zeitpunkt, Umfang und Entscheidung
revisionsfest erkennen lassen.

## Provider-Origin und Paketbesitz

Der Origin muss exakt dem freigegebenen Providerendpunkt entsprechen.

Hostname-Aliase, Redirectziele, Mirrors, Fallbacks, alternative Regionen und
manuell ersetzte URLs benötigen eine neue Freigabe.

Der Package-Name `liquent` und der konfigurierte Zielname müssen beim Provider
reserviert und dem freigebenden Account eindeutig zugeordnet sein.

Typosquatting-, Namespace- oder Ownership-Konflikte schließen die Freigabe.

## Credential-Vertrag

Das Publication-Credential darf nur die minimal erforderlichen read/create
Operationen für exakt Package und Ziel erlauben.

Es darf keine Signing-, Registry-Admin-, Delete-, Yank-, Replace-, User-,
OIDC-, Deployment- oder Datenbankberechtigung tragen.

Credentialwert und Secret-Manager-Referenz erscheinen nicht in Freigabe,
Tickets, Chat, Logs, Images oder Publication-Requests.

Ausgabe, Rotation, Ablauf, Widerruf und Incident-Sperre müssen außerhalb der
Anwendung kontrolliert und nachweisbar sein.

Rotation ändert die gebundene Credential-Identität und verlangt vor dem
nächsten echten Zugriff eine erneute Scope-Prüfung.

## TLS-, DNS- und Egress-Vertrag

TLS-Zertifikatsprüfung bleibt aktiv. Es gibt keinen Disable-Schalter.

Der aktuelle Client nutzt keine Proxy- oder CA-Werte aus der Prozessumgebung,
folgt keinen Redirects und besitzt genau eine Verbindung.

DNS-Auflösung und Egress müssen auf den freigegebenen Origin und die benötigten
Provideradressen begrenzt sein. Transparente Proxies oder TLS-Interception
benötigen eine explizit kompatible, separat geprüfte Vertrauensentscheidung;
der heutige Operator besitzt dafür keine konfigurierbare CA-Grenze.

Zertifikatswechsel, Hostwechsel, Trustpfadwechsel oder neue Proxyführung
invalidieren die bestehende Freigabe.

## Protokoll- und Immutable-Create-Nachweis

Vor Production muss eine providerrepräsentative, nicht produktiv schreibende
Abnahme bestätigen:

- GET liefert Abwesenheit eindeutig als `404`;
- create-only PUT ersetzt kein vorhandenes Artefakt;
- erfolgreicher Create liefert ausschließlich das erwartete `201`-Schema;
- nachfolgendes GET liefert kanonische Identität, Revision, Name, Version und
  Wheel-Hash;
- vorhandene gleiche oder abweichende Versionen werden nicht überschrieben;
- Redirects, unerwartete Statuscodes und fremde Medienformate scheitern
  fail-closed;
- Responsegrößen und Zeitgrenzen sind für das Environment tragfähig.

Ein echter Production-Testupload ist in LQ-286 ausdrücklich nicht erlaubt.

## Quota, Rate Limits und Sichtbarkeit

Providerquota, Paketgrößenlimit und Rate Limits müssen die begrenzte
GET/PUT/GET-Sequenz sowie eine spätere read-only Reconciliation tragen.

Die erwartete Sichtbarkeitslatenz muss innerhalb der freigegebenen
Gesamtdauer liegen oder als möglicher Unknown Outcome betrieblich behandelt
werden.

Rate-Limit-Retryheader autorisieren keine automatische Wiederholung. Der
bestehende Worker führt keine Polling- oder Backoff-Schleife aus.

## Host- und Prozessgrenze

Der freigegebene Host muss mindestens gewährleisten:

- dediziertes nicht interaktives Publication-Konto;
- owner-only lokale Eingaben und Credentialquelle;
- exakte installierte Migration und Operational-Bundle-Version;
- kontrollierten Datenbank- und Provider-Egress;
- synchronisierte Wall- und monotone Clock;
- ausreichend privaten Speicher für unveränderliche Artefakte;
- keine Shell-Traces, Core-Dumps oder Secret erfassende Diagnosehooks.

HTTP-App, Webruntime und Deploymentstartup erhalten keinen Zugriff auf die
Publication-Credentials oder Offline-Operatoren.

## Monitoring und minimale Telemetrie

Monitoring darf nur Prozessstart, Environment, technische Dauer, Exitcode,
Outcome-Familie und genehmigte stabile Referenzen erfassen.

Nicht erfasst werden Credential, Authorization-Header, DSN, lokale Pfade,
Providerbody, Registryinventar, Signaturbytes oder private Requestdateien.

Fehlende Telemetrie darf nicht durch breit aktiviertes HTTP-, SQL- oder
Shell-Debuglogging kompensiert werden.

## Incident und Unknown Outcome

Für Timeout, Verbindungsverlust, verlorene Ausgabe, Providerstörung,
Credentialverdacht und Hashkonflikt muss vor Freigabe ein erreichbarer
Incidentweg benannt sein.

Nach möglichem PUT gilt fehlende Bestätigung niemals als Abwesenheit.

Der Incidentweg bewahrt alle IDs und Eingaben, sperrt bei Bedarf Credential
oder Egress und verwendet ausschließlich den bestehenden beaufsichtigten
Reconciliation-Pfad. Er erzeugt keine neue Execution-ID und keinen manuellen
Ersatzupload.

Providerseitiges Delete, Yank oder Replace ist kein Rollback dieses Systems und
benötigt einen späteren eigenen Vertrag.

## Deployment-Freigabe

Deployment und Package-Publication bleiben getrennte Entscheidungen.

Eine Application-Rollbackentscheidung zieht ein bereits veröffentlichtes Package nicht zurück.
Umgekehrt deployt ein veröffentlichtes Package keine Runtime und ändert keine
HTTP-App.

Die Deploymentfreigabe muss Image-/Artefaktdigest, Konfiguration, Migration-
Readiness, Backup-/Restore-Nachweis, Healthchecks und Rollbackgrenze separat
binden.

LQ-286 fügt den Offline-Operatoren keinen Deployment-Hook hinzu.

## Gültigkeit und Widerruf

Jede Änderung an Origin, Package, Ziel, Credential-Identität oder Scope,
Trustpfad, Host, Prozessaccount, Bundle-Version oder Providerverhalten beendet
die bisherige Freigabe für spätere Starts.

Widerruf muss vor dem nächsten Prozessstart wirksam sein, mindestens durch
Credentialentzug, Egress-Sperre oder Entzug der operativen Aufrufberechtigung.

Ein bereits gestarteter möglicher Providerwrite wird anschließend als Unknown
Outcome reconciled und nicht als sicher verhindert behauptet.

## Freigabeergebnis

Das Ergebnis ist genau eine der betrieblichen Entscheidungen:

- `approved` für den exakt gebundenen Umfang und Zeitraum;
- `rejected` ohne Publication;
- `expired` oder `revoked` für alle späteren Starts;
- `unavailable` wenn erforderliche Nachweise technisch nicht beurteilbar sind.

Diese Begriffe sind kein neues Domainmodell und keine neue Exceptionfamilie.
Sie beschreiben nur den extern bewahrten Approval-Record.

## Bewusst nicht enthalten

LQ-286 entscheidet kein Schema, SQL, Port, Modell, Signatur, Migration, CLI,
Dateiformat, Secret-Manager-Produkt, Providerkonto oder Deploymentwerkzeug.

Es erzeugt keinen Seed, Testupload, DNS-Aufruf, TLS-Handshake, Credentialread,
Providerrequest, Package, Tag, Commit, Push, Deployment oder Rollback.

Head und Bundle-Inventar bleiben unverändert.

Die vollständige PostgreSQL-16-Pflichtsuite besteht mit 3396 Tests und 588
bestehenden Warnungen.

## Nächster Slice

LQ-287 sollte eine konkrete evidence-basierte Provider-Readiness-Checkliste und
deren detailarmen Offline-Auditnachweis implementieren, weiterhin ohne
Production-Upload oder automatische Freigabe.
