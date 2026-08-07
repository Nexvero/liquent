# LQ-170 — Controlled OIDC JWKS Cache Refresh

## Zweck und Signatur

Der bestehende Single-Slot-Cache erhält **eine** explizite Refresh-Operation.
Sie **führt** einen Refresh aus und **entscheidet nicht**, ob er zulässig ist.

```python
# src/liquent_platform/identity/oidc_jwks_cache.py
def refresh_jwks(
    self, configuration: TrustedOidcClientConfiguration
) -> Mapping[str, object]: ...
```

Keine weiteren öffentlichen Methoden und **kein** Parameter für Token,
ID-Token, `kid`, Algorithmus, vorherigen Verifikationsausgang, `force`,
Retryanzahl oder eine freie URI. Die URI stammt ausschließlich aus
`configuration.jwks_uri`, bytegenau und ohne Normalisierung.

## Ablauf

1. Vorhandenen Slot **sofort** verwerfen — vor dem Uhrlesen und vor dem Loader.
2. Die injizierte monotone Uhr kontrolliert lesen.
3. **Genau einmal** `loader.load_jwks(configuration)` aufrufen.
4. Nach erfolgreichem Laden die Uhr erneut kontrolliert lesen.
5. `expires_at = loaded_at + jwks_cache_ttl` bilden; endlich **und** strikt
   größer als `loaded_at`.
6. Erst dann den einzigen Slot setzen: bytegenaue `jwks_uri`, exakt das
   geladene Mapping, neue Ablaufgrenze.
7. Genau diesen neuen Snapshot zurückgeben.

Verworfen wird **unabhängig** von Frische, Ablauf und URI-Gleichheit:
`refresh_jwks` ist bewusst **kein** Hit-Pfad und kann daher nie ausliefern, was
es ersetzen soll. Der verworfene erste Messwert dient der instanzweiten
Monotonie und meldet eine unbrauchbare Uhr **vor** dem Netzaufruf.

## Fehlerverhalten

`OidcVerificationUnavailable` wird neutral weitergereicht; jeder andere normale
Loader- oder Uhrfehler wird in eine **neue** neutrale Exception übersetzt, ohne
Details oder Cause. In allen Fällen bleibt der Cache leer: **kein** Rollback,
**keine** Wiederherstellung des vorherigen Snapshots, **kein** stale fallback,
**kein** zweiter Loader-Aufruf, **kein** Retry.

`BaseException` wird nicht abgefangen und nicht neutralisiert. Weil der Slot
bereits vor dem ersten Uhrlesen verworfen ist, bleibt auch bei einer abrupten
Unterbrechung von Loader oder Uhr kein alter Snapshot servierbar.

## Gemeinsame Ladegrenze

Laden, TTL-Stempel und Speichern liegen in **einem** privaten Helfer, den beide
Wege nutzen: `get_jwks(...)` bei leerem, abgelaufenem oder URI-fremdem Slot und
`refresh_jwks(...)` nach dem zwingenden Verwerfen. Der Helfer setzt keinen Slot
vor vollständigem Erfolg und trifft keine Refresh-Entscheidung; der jeweilige
Aufrufer hat den Slot bereits verworfen. Kein rekursiver Aufruf zwischen den
beiden öffentlichen Methoden, keine neue Klasse, keine generische Abstraktion.

`get_jwks(...)` bleibt **beobachtbar unverändert**: erster Miss liest die Uhr,
lädt genau einmal, liest erneut und speichert; ein frischer Treffer kostet einen
Uhrlesevorgang und keinen Load; Ablauf und URI-Wechsel verwerfen vor dem Laden;
die TTL beginnt nach dem Laden; Float-Sättigung bleibt beim ersten Aufruf
neutral.

## Kapazitäts-, Uhr- und Geheimnisgrenze

Weiterhin **strukturell genau ein** Slot: Ein Refresh ersetzt, er erweitert und
vereinigt nie. Kein Dictionary, kein LRU, kein wachsender Verlauf, keine zweite
Cache-Partition und keine tokengesteuerte Partition. Nach erfolgreichem Refresh
liefert ein `get_jwks` innerhalb der TTL denselben neuen Snapshot **ohne**
weiteren Loader-Aufruf.

Alle Uhrregeln aus **LQ-167** gelten unverändert und werden hier nicht
wiederholt; sie greifen für beide Uhrlesevorgänge des Refresh genauso.

Weder URI noch Schlüssel, Mappinginhalte oder Refreshdetails erscheinen in
`repr`, Exceptions, Logs, Telemetrie oder Metriklabels. Dieser Slice fügt keine
Logging- oder Metrikfunktion hinzu.

## Warum die Methode nicht entscheidet

Ob ein Refresh zulässig ist, hängt nach LQ-168 §3 an acht Bedingungen, die
sämtlich im **Token** liegen. Der Cache sieht kein Token und darf keines sehen:
Ein Parameter für `kid` oder den vorherigen Verifikationsausgang reichte die
private LQ-169-Ergebnisform an eine Infrastrukturkomponente durch und weichte
genau die Grenze auf, die LQ-168 §5 zieht; ein `force`-Flag oder eine
Retryanzahl wäre derselbe Fehler in klein. Entscheidungsfrei bleibt die
Obergrenze „höchstens ein Refresh pro Callback" allein im Adapter kontrollierbar
und dort testbar.

## Nicht-Ziele

Keine Entscheidung anhand unbekanntem `kid`, kein Token- oder JOSE-Parsing,
keine Nutzung der privaten LQ-169-Ergebnisform, kein Adapter, kein
Token-Endpunkt-Aufruf, keine Offline-Verifikation, kein zweiter Refresh, keine
Retry-Schleife, kein stale-while-error, kein Background-Refresh, kein Locking,
kein Multi-URI-Cache, kein persistenter oder verteilter Cache, keine
Portänderung, keine Callback-Route, keine Session-/CSRF-Ausgabe, keine
Composition, kein Production-Wiring, keine neue Dependency und keine CI-,
Container-, Deployment- oder Grype-Änderung.
