# LQ-192 — Persistent Active OIDC Client Configuration

## Ergebnis

LQ-192 implementiert den bestehenden parameterlosen
`ActiveOidcClientConfigurationLookup` persistent. Die Login-Grenzen können
damit genau eine aktuell aktive, ausschließlich serverseitig bestimmte
`TrustedOidcClientConfiguration` aus dem System of Record lesen.

Der Slice ergänzt eine additive Migration und einen read-only Adapter. Er
liefert keine Verwaltungs-, Import-, Seed-, Environment-, CLI-, HTTP- oder
Startup-Grenze und verdrahtet OIDC noch nicht automatisch in `create_app`.

## Persistente Form

Revision `20260812_0007` ergänzt `oidc_client_configuration` als Singleton.
Der einzige zulässige Schlüsselwert ist `1`; Primärschlüssel und Check-
Constraint schließen einen zweiten Datensatz strukturell aus.

Der Datensatz hält:

- den expliziten Aktivstatus,
- Issuer, Authorization Endpoint, Client-ID und Redirect-URI,
- Scopes in ihrer gespeicherten Reihenfolge,
- Token Endpoint und JWKS URI,
- die erlaubten Signaturalgorithmen in ihrer gespeicherten Reihenfolge,
- den Clock Skew in Mikrosekunden innerhalb der bestehenden Obergrenze.

Textwerte und die JSON-Repräsentationen der Tupel werden als Bytes gehalten.
Beim Lesen werden sie strikt als UTF-8 dekodiert. Es gibt kein Trimming,
Lowercasing, URL-Rewriting, Sortieren, Deduplizieren oder Ergänzen von Scopes
oder Algorithmen. Anschließend konstruiert der Adapter das bestehende
Domainobjekt, sodass dessen vollständige Validierung weiterhin maßgeblich ist.

Die Migration erzeugt keinen Datensatz. Eine frisch migrierte Installation hat
daher keine aktive OIDC-Konfiguration und aktiviert keinen Login.

## Lookup-Vertrag

`DatabaseActiveOidcClientConfiguration.get_active_configuration()` behält die
Portsignatur exakt bei: nur `self`, ohne Issuer, Provider, Client-ID, Tenant,
Workspace, User, Host, Header, Query, Cookie oder sonstigen Selektor.

Jeder Aufruf liest den Singleton neu. Eine später committete Deaktivierung wirkt
deshalb auf jede spätere Login-Start- oder Callback-Entscheidung. Der Adapter
hält keinen Trust-Snapshot, keinen Cache und keinen In-Process-Status.

Ein aktiver, gültiger Datensatz wird als neues unveränderliches
`TrustedOidcClientConfiguration`-Objekt mit exakt den gespeicherten Werten
zurückgegeben. Das Objekt ist weiterhin kein Beweis dauerhaft gültigen Trusts:
Login-Start liest aktuell, und der Callback muss den aktuellen Issuer-Trust wie
bisher erneut über dieselbe aktive Konfigurationsgrenze prüfen.

## Neutrale Abwesenheit

`None` bedeutet ausschließlich, dass jetzt keine aktive OIDC-Konfiguration
verfügbar ist. Das gilt sowohl für eine leere Tabelle als auch für den
vorhandenen, aber inaktiven Singleton.

Die Rückgabe unterscheidet nicht zwischen nie konfiguriert und deaktiviert,
nennt keinen früheren Issuer oder Client und bietet keinen Default oder
Fallback. Eine spätere Transportgrenze darf daraus ebenfalls keine
detailreichere Antwort ableiten.

## Technische Nichtverfügbarkeit

Fehlende Migration, Datenbank- oder Transaktionsfehler, ungültiges UTF-8,
unlesbares JSON, unzulässige Typen und ein aktiver Datensatz, der die
Domaininvarianten verletzt, sind keine neutrale Abwesenheit. Sie verlassen den
Adapter als detailfreie `OidcClientConfigurationStoreUnavailable` ohne Cause
oder Context.

Die Ausnahme enthält weder Konfigurationswerte noch SQL, Tabellen-, Constraint-,
Treiber-, Host-, Port- oder DSN-Details. Der wertfreie Adapter-`repr` zeigt
ebenfalls weder Inhalt noch Aktivstatus.

Ein inaktiver Datensatz wird nicht rekonstruiert. Sein fachlich maßgeblicher
Zustand ist neutral inaktiv; seine früheren Werte werden dadurch weder
offengelegt noch irrtümlich wieder als Trust ausgewertet.

## Read-only und Trust-Grenze

Der Adapter bietet ausschließlich den bestehenden Lookup. Es gibt kein
`create`, `set`, `replace`, `activate`, `deactivate`, `delete`, `rotate`,
`reload`, `discover` oder Listen-API.

Die Tabelle ist keine dynamische Multi-Issuer-Registry. Sie speichert weder
Client Secret, private Schlüssel, JWKS, Tokens, Claims noch Login-State,
Nonce, Code Verifier, Admission, User, Workspace, Membership, Permission oder
Session. Schlüsselmaterial wird weiterhin nur über die getrennte JWKS-Grenze
geladen und geprüft.

Insbesondere darf ein Browser keine Providerwahl in den Lookup einspeisen.
Mehrere Provider, Mandanten- oder Workspace-Routing und dynamische Discovery
würden einen neuen Vertrag erfordern und dürfen die parameterlose
Singleton-Semantik nicht stillschweigend erweitern.

## Tests

Die SQLite-Tests beweisen:

- leere und inaktive Persistenz ergeben dasselbe neutrale `None`,
- alle neun Domainwerte werden exakt rekonstruiert,
- eine spätere Deaktivierung sperrt einen späteren Lookup,
- beschädigte aktive Persistenz und fehlende Migration bleiben technisch,
- Fehler und Adapter-`repr` bleiben detailfrei,
- die Datenbank verhindert einen zweiten Singleton-Datensatz.

Der markierte PostgreSQL-Test beweist zusätzlich, dass eine committete
Deaktivierung über eine spätere neue Entscheidung sichtbar wird. PostgreSQL
bleibt die normative Runtime; SQLite deckt Migration und portable Semantik ab.

## Bewusst nicht enthalten

- keine Mutations- oder Operatorgrenze und kein initialer Konfigurationsimport,
- kein Secret Store, Key Management, Discovery, Netzwerkzugriff oder Cache,
- kein Multi-Issuer, Provider-Picker oder browsergesteuertes Routing,
- keine Login-Start-, Callback- oder Logout-Route,
- keine Verifier-, JWKS- oder HTTP-Client-Composition,
- keine automatische `create_app`-Verdrahtung,
- keine Membership-, Rollen-, Admission- oder Autoritätsänderung,
- kein Deployment, keine Umgebungsvariable und kein Production-Seed.

## Nächster Schritt

Der nächste Slice kann die kontrollierte OIDC-Verifier-Composition um diese
aktuelle persistente Konfiguration ergänzen. Dazu gehören die expliziten
HTTP-/JWKS-/Token-Verifier-Abhängigkeiten und deren Ownership; erst danach kann
LQ-177 OIDC-Start und Callback sicher automatisch verdrahten. Reguläre
Membership-Persistenz bleibt davon getrennt und weiterhin erforderlich, bevor
geschützte Research-Routen produktiv geöffnet werden.
