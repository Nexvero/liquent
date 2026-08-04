# LQ-148 — Active OIDC Client Configuration Lookup Port

## Ergebnis

Ein kleiner **read-only Port**, über den eine spätere Login-Start-Grenze die
aktuell aktive, serverseitig kontrollierte OIDC-Client-Konfiguration erhält.

**Kein** Adapter, **kein** Store, **keine** Route, **kein** Anwendungsfall,
**keine** Änderung am Konfigurationsmodell.

## Signatur

`src/liquent_platform/identity/ports.py`

```python
class ActiveOidcClientConfigurationLookup(Protocol):
    def get_active_configuration(
        self,
    ) -> TrustedOidcClientConfiguration | None: ...
```

Name **unverändert** übernommen: `ports.py` führt bereits
`WorkspaceMembershipLookup`, `BrowserSessionLookup` und
`ExternalIdentityLookup`; das Suffix `Lookup` und das Methodenpräfix `get_`
(`get_membership`, `get_session`, `get_user_id`) passen exakt. Der Port steht
direkt hinter `OidcLoginTransactionCreationStore`, damit die OIDC-Ports
beieinander bleiben.

## Zielentscheidung: genau eine aktive Konfiguration

Liquent unterstützt an dieser Grenze zunächst **genau eine** aktuell aktive
OIDC-Client-Konfiguration. Bewusst **nicht** enthalten:

- kein `get_by_issuer`,
- kein `get_by_provider`,
- kein `list_configurations`,
- keine Browserauswahl,
- kein Multi-Issuer-Routing,
- kein Enterprise-SSO-Tenant-Routing,
- kein Fallback auf eine zweite Konfiguration.

Eine spätere Erweiterung auf mehrere vertrauenswürdige Issuer braucht einen
**eigenen Vertrag** und darf die Bedeutung dieser Methode **nicht** stillschweigend
verändern.

## Struktureller Schutz gegen caller-gesteuerte Providerwahl

Die Methode hat **außer `self` keinen Parameter**. Sie akzeptiert insbesondere
keinen Issuer, Provider-Namen, keine Client-ID, keinen Tenant, Workspace,
Benutzer, Host, Header, Querywert, kein Cookie, kein Admission-Handle, keinen
Rückkehrpfad und keinen sonstigen Auswahlparameter.

Damit kann eine spätere HTTP-Grenze **schon rein typseitig** keinen vom Browser
gewählten Provider an den Port weiterreichen. Der Schutz ist **strukturell**,
nicht eine Laufzeitprüfung, die man vergessen könnte.

## Erfolgsfall

Liegt genau eine aktuell aktive, intern freigegebene Konfiguration vor, wird
**exakt dieses unveränderliche Objekt** zurückgegeben:

- **keine** Kopie mit veränderten Werten,
- **keine** Normalisierung,
- **keine** Ergänzung,
- **kein** eingefrorener neuer Trust-Status,
- **kein** hinzugefügtes Secret.

Der Besitz des Objekts entscheidet **nicht dauerhaft** über Trust. Jeder
Login-Start liest die aktuelle Konfiguration **erneut**, und der Callback muss
den aktuellen Issuer-Trust gemäß LQ-136 weiterhin **separat erneut** prüfen.

## Neutraler Leerfall

`None` bedeutet **ausschließlich**: derzeit ist keine aktive
OIDC-Client-Konfiguration für Login verfügbar.

Eine spätere Transportgrenze darf daraus **nicht** ableiten oder offenlegen,

- ob je eine Konfiguration existierte,
- ob sie deaktiviert wurde,
- ob eine Freigabe entzogen wurde,
- welcher Issuer oder Client zuvor konfiguriert war.

Der Port liefert **keine** Liste, **keine** deaktivierte Konfiguration, **keine**
alternative oder Default-Fallback-Konfiguration und **keine** Detailursache.

## Fehlergrenze

Ein echter Lese-, Konfigurations- oder Infrastrukturfehler darf **nicht**
stillschweigend in `None` umgedeutet werden.

Der Port definiert in diesem Slice **keinen** neuen Infrastrukturfehler und
**keine** Fehlerbehandlung. Eine spätere Anwendungs- beziehungsweise
Transportgrenze muss Fehler neutral behandeln, darf aber **keinen** absichtlichen
Leerzustand vortäuschen, wenn der Lookup technisch fehlgeschlagen ist.

## Read-only

Der Port liest ausschließlich. Er aktiviert und deaktiviert nichts, erzeugt,
aktualisiert und löscht nichts, rotiert kein Secret, führt keine Discovery aus,
lädt kein Signaturschlüsselset, tätigt keinen Netzwerkaufruf, verlangt
vertraglich **kein** Caching und entscheidet **keine** Workspace-Berechtigung.

> **Erzwungene Formulierung:** Der Docstring sagt „loads no signing key set"
> statt „loads no JWKS". Grund ist der vorbestehende, zu breite LQ-139-Test
> `test_ports_module_has_no_token_trust_http_or_persistence_logic`: Er
> durchsucht per `inspect.getsource(ports_mod)` die **gesamte** Datei nach
> Substrings wie `jwks` und kann nicht unterscheiden, ob ein Vorkommen die
> Nutzung beschreibt oder sie **ausschließt**. Die Vertragsaussage ist
> unverändert. Der Test selbst wurde **nicht** angefasst — seine Verengung auf
> den Claim-Port bleibt ein eigener Slice.

## Tests

`tests/test_active_oidc_client_configuration_lookup_port.py` — 23 fokussierte
Tests.

**Vertrag:** Ein Stub erfüllt den Port strukturell · der Erfolgsfall liefert das
`is`-identische Objekt, das zusätzlich einem frisch konstruierten gleicht (der
Port kopiert und mutiert also nicht) · kein aktiver Eintrag ergibt ein neutrales
`None` · drei aufeinanderfolgende Lookups sehen den jeweils aktuellen
Stub-Zustand — Konfiguration, entzogene Freigabe, rotierte Client-ID — womit
belegt ist, dass der Vertrag **keinen** eingefrorenen Trust-Zustand festschreibt
· ein echter Stub-Fehler propagiert als `RuntimeError` und wird **nicht** zu
`None`.

**Keine caller-gesteuerte Auswahl:** die Signatur enthält exakt `["self"]` ·
parametrisiert wird geprüft, dass 14 konkrete Auswahlparameter (`issuer`,
`provider`, `provider_name`, `client_id`, `tenant`, `tenant_id`,
`workspace_id`, `user_id`, `host`, `headers`, `query`, `cookie`,
`admission_id`, `return_path`) **nicht** existieren · die Rückgabeannotation ist
die **ausgewertete** Union `TrustedOidcClientConfiguration | None`, nicht deren
Schreibweise.

**Read-only und reine Deklaration:** ein AST-Test, der **ausschließlich** die
Quelle dieses einen Protocol-Typs untersucht, belegt genau eine Methode
`get_active_configuration` — also keine Mutationsmethode — und einen reinen
`...`-Rumpf ohne Discovery-, Netzwerk-, Caching- oder Trust-Logik. Der Test
trifft **keine** Aussage über den Rest von `ports.py`.

**Test-Stubs:** beide Stubs existieren ausschließlich in der Testdatei und sind
weder aus `ports.py` noch aus dem Identity-Paket exportiert.

## Zwei begründete Abweichungen von der Testliste

**„Kein Adapter oder Store wird ergänzt" ist bewusst kein Test.** Ein
`assert not hasattr(in_memory_mod, "InMemoryActiveOidcClientConfigurationLookup")`
würde exakt das bei LQ-142 korrigierte Über-Reichweiten-Problem neu einführen:
Es würde scheitern, sobald ein legitimer späterer Slice den Adapter ergänzt —
ohne einen Vertragsbruch anzuzeigen. Belegt wird es stattdessen am PR-Diff, der
exakt vier Dateien umfasst.

**„`TrustedOidcClientConfiguration` bleibt unverändert"** ist in die
Identitätsprüfung gefaltet: Das zurückgegebene Objekt ist `is`-identisch mit dem
gehaltenen **und** gleich einem frisch konstruierten. Eine erneute
Feldlisten-Prüfung wäre eine Dublette des LQ-146-Tests.

## Bewusst nicht enthalten

- kein Adapter, kein In-Memory-Adapter, kein Konfigurations-Store,
- keine Datei- oder Environment-Konfiguration,
- kein Secret, kein Client-Secret,
- keine Aktivierungs-/Deaktivierungsfunktion, kein Trust-Registry-Modell,
- keine Multi-Issuer-Auswahl, kein Providerparameter, kein Enterprise-SSO,
- keine Discovery, kein JWKS, kein Netzwerk, keine DNS-Prüfung,
- keine OIDC-/OAuth-Bibliothek,
- kein Authorization-Request-Builder (LQ-147 ist abgeschlossen),
- keine Login-Start-Route, kein HTTP-Redirect, keine Entscheidung über Route,
  Methode oder Status,
- kein Callback, keine Token- oder Claim-Verarbeitung,
- keine Admission- oder Autorisierungslogik, keine Session-Erzeugung,
- keine Persistenz oder Migration, kein Production-Wiring,
- kein Deployment oder VPS-Zugriff, keine Proxy-/CORS-Konfiguration,
- keine CI-/Grype-Änderung, keine Änderung der CPython-Ausnahmen,
- kein redundanter Anwendungsfall, der nur den Port aufruft und das Ergebnis
  unverändert weiterreicht.

## Nächster Schritt

Mit diesem Port ist die Eingangsseite der Login-Start-Kette vollständig
beschrieben: aktive Konfiguration lesen (LQ-148) → Login-Transaktion starten
(LQ-144) → Authorization Request bauen (LQ-147). Ein späterer Slice kann den
**lokalen Adapter** für diesen Port ergänzen, danach die **Login-Start-Grenze**,
die die drei Schritte verbindet, und zuletzt die **Route** mit der in LQ-145
verschobenen Entscheidung über Pfad, Methode und Redirect-Status.
