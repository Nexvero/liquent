# LQ-2644 — Confidential OIDC Client Runtime Secret

## Anlass

Die Google OpenID Connect API verlangt beim serverseitigen Austausch eines
Authorization Codes neben Client-ID, Redirect URI und Code zwingend das
Client-Secret. Liquent verwendete bereits PKCE S256, besaß aber bewusst keinen
Secretpfad und hätte einen Google-Webclient daher am Token-Endpunkt neutral
abgelehnt.

Ein Google-Client wurde vor diesem Fix nicht erstellt. Die vorbereitete
Console-Eingabe wurde verlassen, bevor ein Credential erzeugt wurde.

## Runtime-Vertrag

`PlatformSettings` nimmt `oidc_client_secret` als `SecretStr` auf. Der Wert ist
Teil der vollständigen All-or-none-OIDC-Konfiguration: OIDC kann nicht mit
einer teilweise vorhandenen Runtime-Konfiguration starten.

Die Production-Composition liest den Wert ausschließlich aus dem
Runtime-Secret und übergibt ihn getrennt von der persistenten
`TrustedOidcClientConfiguration` an die Verifier-Composition.

Der Token-Endpoint-Client hält das Secret als privaten Laufzeitwert. Er fügt es
genau dem formcodierten Authorization-Code-POST hinzu. JWKS-Abfragen,
Authorization-URLs, Browserantworten, Exceptions und Repräsentationen erhalten
den Wert nicht.

PKCE bleibt zusätzlich aktiv: Der einmalige Code-Verifier wird weiterhin
zusammen mit dem Client-Secret gesendet. Das Secret ersetzt weder State- noch
Nonce- oder Browserbindung.

## Deployment-Grenze

Der Control-Plane-Service mountet `oidc_client_secret` als Docker Secret aus
dem privaten Host-Secret-Verzeichnis. Migration, PostgreSQL, Edge, Research
Worker und andere Dienste erhalten es nicht.

Das Secret wird nicht in `runtime.env`, Compose-Interpolation, Image-Layer,
Trust-Tabellen, Dokumentation oder Roadmap gespeichert. Ein fehlendes oder
leeres Secret verhindert die automatische OIDC-Verdrahtung fail-closed.

## Persistenz bleibt providerneutral

Die persistente OIDC-Trust-Konfiguration behält unverändert ihre neun
providerneutralen, nicht geheimen Werte. Es gibt keine Migration und kein
zusätzliches Datenbankfeld.

Damit bleiben Trust-Rotation und Secret-Rotation getrennte Vorgänge. Die
Trust-Autorität kann keinen Credential-Wert lesen oder über den persistenten
Konfigurationsvertrag einschleusen.

## Verifikation

Die fokussierte Suite aus Token Exchange, Verifier-Composition,
Production-Wiring, Process-Settings und Compose-Vertrag umfasst 78 erfolgreiche
Tests.

Sie belegt insbesondere:

- Secretaufnahme nur bei vollständiger OIDC-Runtime-Konfiguration,
- secretfreie öffentliche Startup-Zusammenfassung und Repräsentation,
- genau einen geformten Token-POST mit Client-Secret und PKCE-Verifier,
- unveränderte neutrale Fehler- und Ressourcen-Lifecycle-Grenzen,
- enges Docker-Secret-Mounting ausschließlich in die Control Plane.

## Grenze und nächster Schritt

Dieser Slice erzeugt kein Google Credential, aktiviert keinen persistenten
Trust, schreibt kein Staging-Secret und verändert keinen laufenden Container
oder Edge-Pfad.

Als Nächstes kann der Google-Webclient mit der autorisierten Staging-Origin und
dem exakten Callback erzeugt werden. Sein Secret muss direkt in den privaten
Staging-Secretpfad übernommen werden. Die Codeänderung benötigt vor einem
Staging-Neustart weiterhin Review, Merge, Release und digestgebundene
Promotion.
