# LQ-2645 — Staging Google OIDC Activation Acceptance

## Ziel

Dieser Slice hält die überprüfte Aktivierung des vertraulichen Google-OIDC-
Clients auf Staging fest. Er verbindet die zuvor getrennten Provider-, Trust-,
Runtime-, Release- und Edge-Schritte zu einem belastbaren Betriebscheckpoint.

Der Slice nimmt keine externe Identität auf. Er erzeugt weder Admission noch
Identity-Bindung, Mitgliedschaft oder fachliche Berechtigung.

## Gebundener Stand

Die Control Plane läuft aus Release `0.1.4` mit dem unveränderlichen Image-
Digest
`sha256:6d8d5c3cf8a72f12fa9209f5a4c335ee5c998066c7587d62e737ae6cbe73740a`.

Dieses Release enthält die beiden erforderlichen Runtime-Korrekturen:

- das vertrauliche OIDC-Client-Secret wird ausschließlich aus der gemounteten
  Secretdatei geladen;
- der Migrationsprozess liest ausschließlich sein Datenbank-Secret und bleibt
  von partiellen OIDC-Umgebungswerten unabhängig.

Die exakten öffentlichen OIDC-Routen sind durch den gemergten `main`-Commit
`3de14bafedcd92d054bef24c0c19c8516a5a8bfc` gebunden. Die installierte
Edge-Konfiguration ist bytegleich mit `operations/edge/staging.conf`; beide
Seiten haben SHA-256
`ba9cae67716cf66a3c39e906c0e8ba31e98eb0ab9527686b7b25d15d513b5974`.

## Provider- und Trust-Grenze

Google ist als ausdrücklich gewählter OIDC-Provider konfiguriert. Der
registrierte Callback verweist ausschließlich auf
`https://staging.liquent.ai/v1/session/oidc/callback`.

Die aktive Client-Konfiguration stammt aus dem persistenten Trust-System. Sie
wird nicht aus Host, Origin, E-Mail-Adresse, Browserzustand oder Callerwerten
abgeleitet. Der Client-Schlüssel bleibt außerhalb von Repository, Datenbank,
Release-Evidence, Logs und dieser Dokumentation.

Die globale OIDC-Trust-Management-Autorität bleibt von Workspace-
Onboarding-Management, Membership und Research-Berechtigungen getrennt.

## Runtime-Abnahme

Die wertfreie Runtime-Zusammenfassung bestätigt:

- Environment `production`;
- strukturierte Logs;
- Trading Connectivity deaktiviert;
- Research-Start deaktiviert;
- OIDC vollständig aktiviert;
- keine teilweise OIDC-Composition.

PostgreSQL, Control Plane und Container-Edge melden jeweils `healthy`. Der
öffentliche Liveness-Endpunkt antwortet mit HTTP 200 und dem erwarteten
wertfreien Servicezustand.

## Persistente Bestandsaufnahme

Eine ausschließlich aggregierte, read-only Abfrage bestätigt:

- genau einen internen Nutzer;
- genau einen internen Workspace;
- genau eine OIDC-Trust-Management-Autorität;
- genau eine OIDC-Client-Konfiguration;
- null externe Identitätsbindungen;
- null Identity-Admissions.

Interne IDs, Provider-Subject, Client-ID und andere sensible Werte wurden dabei
weder ausgegeben noch in Evidenz übernommen.

## Öffentliche Edge-Abnahme

Die Edge erlaubt weiterhin nur die ausdrücklich vorgesehenen Pfade. Ein GET
auf den POST-only Login-Endpunkt wird mit HTTP 405 abgewiesen. Ein gültiger
same-origin POST startet den Login mit HTTP 303 zum Google-
Autorisierungsendpunkt.

Der Callback erreicht die Anwendung und wird nicht mehr von der Default-Deny-
Regel des Edge mit HTTP 404 abgefangen. Alle übrigen unbekannten Pfade bleiben
geschlossen.

Die Quelländerung ist durch 203 fokussierte Edge-, Login-Start- und Callback-
Tests sowie die vollständige grüne PR-Pipeline belegt.

## Erwartetes Login-Ergebnis

Ein erfolgreicher Identitätsnachweis allein darf keinen internen Nutzer
erzeugen und keine bestehende interne Identität erraten. Da keine externe
Bindung und keine Admission existiert, muss der Callback nach erfolgreicher
Provider-Verifikation neutral ablehnen und darf keine Session ausstellen.

Dieses Ergebnis ist der beabsichtigte fail-closed Zustand. Es ist weder ein
Providerfehler noch ein Anlass für First-login-Provisioning oder Self-Sign-up.

## Nicht enthalten

Keine Änderung an Schema, Migration, Modell, Port oder Signatur. Keine neue
Route, kein breites `/v1`-Proxying und keine Änderung an DNS oder Zertifikaten.

Keine Nutzer-, Workspace-, Membership-, Rollen-, Capability- oder Research-
Permission-Mutation. Keine Aufnahme einer E-Mail-Adresse als interne
Identität. Keine Offenlegung oder Rotation eines Secrets.

## Nächster Slice

LQ-2646 soll genau eine kurzlebige, intern autorisierte Admission für den
bereits vorhandenen Staging-Nutzer und Workspace bereitstellen und sie
serverseitig an genau einen OIDC-Login-Start binden.

Der Handle darf nicht als frei übernehmbarer Query-, Formular- oder Headerwert
erscheinen. Die bestehende Onboarding-Authority muss aus dem System of Record
entschieden werden; ein Caller-Boolean, Rollenname oder eine Session allein
gewährt keine Autorität.

Erst dieser getrennte Schritt darf die verifizierte Google-Identität atomar an
den vorhandenen Nutzer binden. Reguläre Membership und Research-Permissions
bleiben auch danach eigene, ausdrücklich autorisierte Slices.
