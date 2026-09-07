# LQ-2642 — Staging OIDC Readiness Audit

## Ziel

Dieser Slice prüft, ob das gesunde Staging-System für eine authentifizierte
Benutzer- und OIDC-Abnahme bereit ist. Die Prüfung liest nur neutrale
Konfigurations- und Bestandsmerkmale. Sie aktiviert keinen Provider, erzeugt
keine Identität und öffnet keine neue öffentliche Route.

## Laufzeitbeobachtung

Die laufende Control Plane enthält keine der gemeinsam erforderlichen
`LIQUENT_OIDC_*`-Runtime-Einstellungen. OIDC-Composition ist deshalb im
Prozess nicht aktiv. Dieser Zustand ist gültig und fail-closed: Login- und
Callback-Routen werden nicht teilweise verdrahtet.

Der Container-Edge veröffentlicht weiterhin ausschließlich
`/health/live`. Alle Session-, Login-, Callback-, Research-, Readiness- und
Metrikpfade enden am abschließenden HTTPS-`404`. Ein Browser kann den internen
OIDC-Vertrag daher nicht erreichen.

Diese geschlossene Edge-Grenze entspricht dem bisherigen
Initial-Bootstrap-Vertrag. Sie ist kein Fehler des gesunden Staging-Runtimes.

## Persistenter neutraler Bestand

Am 7. September 2026 wurden ausschließlich Tabellenanzahlen gelesen. Es wurden
keine internen IDs, Providerwerte, Endpunkte, Secrets oder Identitätsmerkmale
ausgegeben.

Der beobachtete Bestand ist:

- null persistente Benutzer,
- null persistente Workspaces,
- null OIDC-Trust-Management-Autoritäten,
- null OIDC-Client-Konfigurationen,
- null externe Identitätsbindungen.

Damit ist die Datenbank migriert, aber die Identitäts- und Trust-Grundlage noch
nicht initialisiert. Eine OIDC-Anmeldung könnte gegen diesen Zustand keinen
autorisierten Benutzer auflösen und muss geschlossen bleiben.

## Erforderliche Reihenfolge

Die nächste Umsetzung muss die bereits getrennten Autoritätsgrenzen in dieser
Reihenfolge respektieren:

1. beaufsichtigter einmaliger Initial-Identity-Bootstrap,
2. beaufsichtigter einmaliger Bootstrap der OIDC-Trust-Autorität für den
   erzeugten aktiven Benutzer,
3. ausdrückliche Auswahl und externe Einrichtung eines OIDC-Providers und
   Clients für den exakten Staging-Callback,
4. geprüfte Aktivierung der vollständigen persistenten Trust-Konfiguration,
5. gemeinsame Bereitstellung aller nicht geheimen OIDC-Runtime-Limits und
   internen Callback-Ziele,
6. kontrollierter Neustart und interne Prüfung der Login- und Callback-Routen,
7. minimale öffentliche Edge-Freigabe nur der erforderlichen Session-Routen,
8. browsergebundener End-to-End-Test mit einem ausdrücklich aufgenommenen
   externen Identitätsmerkmal.

Der Provider und seine Werte dürfen nicht aus DNS, Hostnamen, Browserzustand
oder üblichen Voreinstellungen abgeleitet werden. Client-Geheimnisse gehören
weder in Git noch in die Runtime-Environment-Datei; ihre konkrete Übergabe
benötigt einen eigenen geprüften Secret-Vertrag, falls der ausgewählte Provider
eines verlangt.

## Sicherheitsgrenzen

Ein authentifizierter `SessionPrincipal` würde nur den persistent aufgelösten
Akteur identifizieren. Er verleiht weder Research-Berechtigungen noch
Workspace-Mitgliedschaft, Onboarding-Management oder OIDC-Trust-Autorität.

Die spätere externe Identitätsaufnahme muss systemseitig an genau einen aktiven
internen Benutzer gebunden werden. Claims, Callback-Parameter und
caller-supplied Rollen dürfen weder Benutzer noch Workspace oder Autorität
bestimmen.

Login-Start bleibt ein origin-gebundener `POST`; Callback bleibt ein
browsergebundener, einmalig konsumierter `GET`. Ablehnung bleibt neutral,
technische Nichtverfügbarkeit detailfrei. Erst eine vollständige grüne interne
Prüfung darf die separate Edge-Änderung erreichen.

## Grenze und nächster Schritt

Dieser Audit verändert weder Datenbankbestand noch Container, Runtime-Dateien,
Edge-Routing, DNS, Zertifikate oder Providerkonten. Er behauptet keine
OIDC-Bereitschaft und keine Benutzeraufnahme.

Als nächster separater Slice folgt der kontrollierte Initial-Identity- und
Trust-Authority-Bootstrap auf Staging. Die Providerwahl und Client-Einrichtung
bleiben danach eine explizite externe Autoritätsentscheidung.
