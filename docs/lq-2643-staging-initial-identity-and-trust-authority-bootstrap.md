# LQ-2643 — Staging Initial Identity and Trust-Authority Bootstrap

## Ziel

Dieser Slice führt die einmalige persistente Identitätsgrundlage auf Staging
aus. Er erzeugt die minimalen internen Fakten, die für eine spätere, getrennte
OIDC-Provider-Aktivierung erforderlich sind.

Der Slice nimmt keine externe Identität auf, aktiviert keinen OIDC-Client und
erteilt weder Workspace-Mitgliedschaft noch Research-Berechtigungen.

## Voraussetzungen

Vor der Mutation war die Staging-Datenbank am Migrationsstand
`20260826_0042`. Der neutrale Bestand enthielt null Benutzer, null Workspaces,
null OIDC-Trust-Management-Autoritäten, null OIDC-Client-Konfigurationen und
null externe Identitätsbindungen.

Der verwendete Operator stammt aus dem bereits laufenden, digestgebundenen
Release `0.1.1`:

`ghcr.io/nexvero/liquent@sha256:80154c0da57fc4c832a4cf8fe2a8250f25b6c85c61de06d317f88c3f07801a67`.

Das Datenbank-Secret war als private reguläre Datei vorhanden. Die vorgesehenen
Ergebnisziele existierten noch nicht.

## Ausführung

Der Identity-Bootstrap lief in einem kurzlebigen, nicht privilegierten
Container auf dem internen `liquent_data`-Netzwerk. Root-Dateisystem und
Datenbank-Secret waren read-only; nur das private Ergebnisverzeichnis war
schreibbar.

Der Operator meldete `bootstrapped` und schrieb atomar genau einen internen
Benutzer, einen internen Workspace und ihre initialen Revisionsfakten. Die
erzeugten stabilen IDs wurden nicht in Standardausgabe, Logs oder diese
Dokumentation übernommen.

Aus dem geschützten Ergebnis wurde ausschließlich der erzeugte interne
Benutzerbezug in eine separate private Übergabedatei übertragen. Damit lief
anschließend der getrennte OIDC-Trust-Authority-Bootstrap unter denselben
Laufzeitbegrenzungen.

Auch dieser Operator meldete `bootstrapped`. Er erzeugte genau die globale
OIDC-Trust-Management-Autorität für den zuvor systemseitig erzeugten aktiven
Benutzer. Er erzeugte keine Trust-Revision und keine Providerkonfiguration.

## Persistentes Ergebnis

Die neutrale Bestandszählung nach beiden Commits ergab:

- genau einen persistenten Benutzer,
- genau einen persistenten Workspace,
- genau eine OIDC-Trust-Management-Autorität,
- null OIDC-Client-Konfigurationen,
- null externe Identitätsbindungen.

Die vollständigen Bootstrap-Resultate und die enge Benutzer-ID-Übergabe liegen
unter `/opt/liquent/evidence/identity-bootstrap`. Das Verzeichnis hat Modus
`0700`; alle drei Dateien haben Modus `0600`. Verzeichnis und Dateien gehören
`root:root`.

## Autoritätsgrenzen

Die internen `UserId`- und `WorkspaceId`-Werte sind stabile,
nicht wiederzuverwendende Systemfakten. Sie werden nicht aus E-Mail-Adresse,
OIDC-Subject, Browserwert oder Provider-Claim abgeleitet.

Die OIDC-Trust-Management-Autorität erlaubt nur die getrennte Verwaltung der
globalen Trust-Konfiguration. Sie ist keine Workspace-Mitgliedschaft, keine
Onboarding-Management-Capability und keine Research-Berechtigung.

Eine spätere authentifizierte Session identifiziert nur den über eine
persistente externe Bindung aufgelösten Akteur. Weder die Session noch ein
OIDC-Claim darf daraus zusätzliche Autorität ableiten.

## Grenze und nächster Schritt

Dieser Slice verändert weder Edge-Routing noch Runtime-Einstellungen, DNS,
Zertifikate oder externe Providerkonten. Er erstellt keine Mitgliedschaft,
keine Capability, keine externe Identitätsbindung und keine Admission.

Als nächster separater Schritt muss ein OIDC-Provider ausdrücklich ausgewählt
und ein Client für den exakten Staging-Callback eingerichtet werden. Erst nach
geprüfter persistenter Trust-Aktivierung, sicherer Secret-Übergabe und interner
Login-Prüfung darf eine minimale Edge-Freigabe folgen.
