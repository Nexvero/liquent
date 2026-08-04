# LQ-150 — In-Memory Active OIDC Client Configuration

## Ergebnis

Ein minimaler, flüchtiger lokaler Adapter für den bestehenden Port
`ActiveOidcClientConfigurationLookup` (LQ-148).

**Kein** Production-Wiring, **keine** dynamische Trust-Registry, **kein**
Konfigurations-Store, **keine** Reload-Funktion.

## Signaturen

`src/liquent_platform/identity/in_memory.py`

```python
@dataclass(frozen=True, slots=True)
class InMemoryActiveOidcClientConfiguration:
    configuration: TrustedOidcClientConfiguration | None = field(
        default=None,
        repr=False,
    )

    def get_active_configuration(
        self,
    ) -> TrustedOidcClientConfiguration | None:
        return self.configuration
```

## Zwei begründete Namens- und Formentscheidungen

**Name im Singular.** Die vorhandenen Adapter heißen `InMemoryBrowserSessions`,
`InMemoryExternalIdentities` und `InMemoryOidcLoginTransactions` — **Plural**,
weil sie *Sammlungen* halten. Dieser Adapter hält **genau eine** optionale
Konfiguration; ein Plural wäre irreführend, da die Einzigkeit gerade der Kern
des LQ-148-Vertrags ist.

**Frozen Dataclass statt einfacher Klasse.** Die drei vorhandenen Adapter sind
einfache Klassen mit `__init__`, weil sie ihren Zustand **mutieren**
(Snapshot-Tausch bei Claim, Add oder Rotate). Dieser Adapter ist nach
Konstruktion unveränderlich — `@dataclass(frozen=True, slots=True)` erzwingt das
sprachseitig statt per Konvention, und die Identity-Schicht nutzt diese Form
durchgängig für unveränderliche Objekte. Platziert ist er am Ende von
`in_memory.py`, direkt hinter `InMemoryOidcLoginTransactions`, damit die
OIDC-Adapter beieinander bleiben.

## Verhalten

**Mit Konfiguration:** `get_active_configuration()` liefert **exakt dasselbe
Objekt** — bei jedem Aufruf dasselbe. **Keine** Kopie, **keine** Normalisierung,
**keine** Ergänzung, **keine** Rekonstruktion, **kein** Trust-Flag, **kein**
Secret, **keine** Änderung am Objekt.

**Ohne Konfiguration** (ohne Argument oder mit explizitem `None`): Rückgabe
`None`. **Keine** Exception, **kein** Default, **kein** Fallback, **keine**
automatisch erzeugte Konfiguration und **keine** Information über frühere
Konfigurationen.

## Read-only

Der Adapter ist nach Konstruktion unveränderlich. Es gibt **keine**
`set_configuration`, `replace_configuration`, `activate`, `deactivate`,
`delete`, `clear`, `reload`, `refresh` oder `discover` und **keine** sonstige
öffentliche Mutations- oder Verwaltungs-API. Ein Zuweisungsversuch auf
`configuration` schlägt mit `FrozenInstanceError` fehl; der gespeicherte Wert
bleibt danach unverändert.

## `repr`-Grenze

Die gespeicherte Konfiguration ist mit `repr=False` verborgen. Issuer,
Authorization Endpoint, Client-ID, Redirect-URI und Scopes sind **keine**
Authentifizierungsgeheimnisse, gehören aber zur internen Sicherheits- und
Providerkonfiguration und sollen nicht beiläufig über Debug- oder
Fehlerrepräsentationen in Logs gelangen. Der Klassenname darf erscheinen.

Praktisch lautet der `repr` in **beiden** Fällen identisch
`InMemoryActiveOidcClientConfiguration()` — er verrät also nicht einmal, **ob**
eine Konfiguration gesetzt ist.

## Trust-Semantik: lokaler Snapshot, kein Trust

Der Adapter ist ausschließlich für **lokale, flüchtige Zusammensetzung**
gedacht:

- Er trifft **keine** Trust-Entscheidung.
- Er prüft **keinen** aktuellen Issuer-Trust.
- Er enthält **keinen** Aktivierungsstatus.
- Er führt **keine** Discovery aus.
- Er lädt **keine** Signaturschlüssel.
- Er aktualisiert sich **nicht** dynamisch.

Die gehaltene Konfiguration ist ein **lokaler Composition-Snapshot**, nicht
lebender Trust. Für Produktionsbetrieb oder dynamische Sperrung ist später eine
echte aktuelle Konfigurations- und Trust-Grenze erforderlich. Der Callback muss
den aktuellen Issuer-Trust gemäß LQ-136 weiterhin **separat erneut** prüfen, und
dieser lokale Adapter darf **niemals** als Begründung dienen, eine später
entzogene Issuer-Freigabe zu ignorieren.

## Keine browsergesteuerte Auswahl

`get_active_configuration()` behält exakt die parameterlose Portsignatur. Weder
Browser noch Aufrufer können Issuer, Provider, Client, Tenant, Workspace, User,
Host, Header, Querywert, Cookie, Admission-Handle oder Rückkehrpfad übergeben.
Die Konfiguration wird **ausschließlich** beim serverseitigen Aufbau der
Adapterinstanz festgelegt.

## Keine duplizierte Validierung

Der Adapter validiert Issuer, Authorization Endpoint, Client-ID, Redirect-URI
und Scopes **nicht erneut** — diese Invarianten gehören
`TrustedOidcClientConfiguration` (LQ-146). Er speichert ausschließlich ein
bereits konstruiertes Konfigurationsobjekt oder `None`.

## Tests

`tests/test_in_memory_active_oidc_client_configuration.py` — 33 fokussierte
Tests.

**Mit Konfiguration:** strukturelle Kompatibilität über eine typisierte
Portvariable · Rückgabe ist `is`-identisch mit dem übergebenen Objekt ·
wiederholte Aufrufe liefern dasselbe Objekt · alle fünf Werte bleiben exakt und
das Objekt gleicht einem frisch konstruierten.

**Ohne Konfiguration:** Konstruktion ohne Argument, mit explizitem `None` und
wiederholte Leer-Lookups liefern jeweils `None`.

**Unveränderlichkeit:** Zuweisung auf `configuration` scheitert mit
`FrozenInstanceError`; der gespeicherte Wert bleibt danach identisch · neun
Mutations-/Verwaltungsnamen sind parametrisiert als nicht vorhanden belegt.

**`repr`:** enthält den Klassennamen, aber weder Issuer, Endpoint, Client-ID,
Redirect-URI noch einen der Scopes.

**Signaturen:** die Lookup-Methode nimmt exakt `["self"]` · elf konkrete
Auswahlparameter sind parametrisiert ausgeschlossen · die Rückgabeannotation ist
identisch mit der des Ports und entspricht der ausgewerteten Union · der
Konstruktor nimmt exakt `["self", "configuration"]`, also **keine** Uhr, keinen
Generator, keinen Netzwerk-Client und keine Discovery-Abhängigkeit — anders als
`InMemoryOidcLoginTransactions`, das eine Uhr entgegennimmt.

Geprüft wird ausschließlich der LQ-150-Vertrag: **keine** Modulflächenprüfung,
**keine** globalen Importverbote, **keine** AST-Prüfung über `in_memory.py`,
**keine** Substring-Suche über das Modul und **keine** Verbote künftiger
legitimer Adapter.

## Bewusst nicht enthalten

- keine Änderung am Port oder am Konfigurationsmodell,
- keine dynamische Trust-Registry, kein Konfigurations-Store,
- keine Datei- oder Environment-Konfiguration, keine Reload-Funktion,
- keine Aktivierungs-/Deaktivierungsfunktion,
- kein Multi-Issuer, keine Providerauswahl, kein Enterprise-SSO,
- keine Discovery, kein Signaturschlüssel-Loading, kein Netzwerk, keine
  DNS-Prüfung,
- keine externe OIDC-/OAuth-Bibliothek,
- kein Authorization-Request-Builder (LQ-147 ist abgeschlossen),
- keine Login-Start-Route, kein HTTP-Redirect, keine Entscheidung über Route,
  Methode oder Status,
- kein Callback, keine Token- oder Claim-Verarbeitung,
- keine Admission- oder Autorisierungslogik, keine Session-Erzeugung,
- keine Persistenz oder Migration, kein Production-Wiring,
- kein Deployment oder VPS-Zugriff, keine Proxy-/CORS-Konfiguration,
- keine CI-/Grype-Änderung, keine Änderung der CPython-Ausnahmen.

## Nächster Schritt

Damit sind alle drei Bausteine der Login-Start-Kette lokal zusammensetzbar:
aktive Konfiguration lesen (LQ-148/LQ-150) → Login-Transaktion starten (LQ-144)
→ Authorization Request bauen (LQ-147). Ein späterer Slice kann die
**verbindende Login-Start-Grenze** definieren und zuletzt die **Route** mit der
in LQ-145 verschobenen Entscheidung über Pfad, Methode und Redirect-Status.
