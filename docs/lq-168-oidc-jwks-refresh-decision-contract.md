# LQ-168 — OIDC JWKS Refresh Decision Contract

## 1. Status, Ziel und Systemgrenze

Architekturentscheidung, **nur Vertrag**. Kein Produktionscode, keine interne
Ergebnisform, keine Cache-Methode, keine Portänderung, kein Adapter.

Der spätere Verifikationsadapter darf bei **genau einem** eng definierten
internen Schlüsselmiss **höchstens einen** kontrollierten JWKS-Refresh
ausführen. Dieser Slice legt fest, wann das zulässig ist, wann nicht, und wie
der Grund intern bleibt. Er baut auf LQ-155, LQ-160 §7–§8, LQ-164, LQ-166 und
LQ-167 und **erfüllt** die in LQ-160 §8 vertagte Zusage „bei unbekanntem `kid`
höchstens ein kontrolliertes Refresh"; keiner dieser Verträge wird geändert.

## 2. Unveränderte Außengrenze

```
Erfolg               → ExternalIdentity
belastbare Ablehnung → None
technisch unmöglich  → OidcVerificationUnavailable
```

Der Refreshgrund ist **ausschließlich** eine private Orchestrierungsentscheidung
des Adapters. Er darf **niemals** den öffentlichen Rückgabetyp erweitern, einen
neuen öffentlichen Fehler erzeugen, bis zur Callback-Route gelangen oder in
HTTP-Status, Body, Redirect-Ziel, Cookie, Log, Telemetrie oder Metriklabel
sichtbar werden.

## 3. Wann ein Refresh zulässig ist

Nur wenn **alle acht** Bedingungen gleichzeitig erfüllt sind:

1. Der Authorization Code wurde genau einmal eingelöst.
2. Ein nicht leeres `id_token` kam vom exakt konfigurierten Token-Endpunkt.
3. Der geschützte JOSE-Header wurde innerhalb der LQ-164-Grenzen strukturell
   zuverlässig gelesen.
4. Es gibt **genau einen** nicht leeren String-`kid`.
5. `alg` ist vorhanden, nicht `none`, asymmetrisch und in
   `configuration.allowed_signing_algorithms`.
6. **Keine** tokenkontrollierte Schlüsselquelle (`jku`, `x5u`, `jwk` oder
   ähnlich) ist vorhanden beziehungsweise akzeptiert.
7. Im aktuell kontrolliert geladenen JWKS existiert **kein** Schlüssel mit
   diesem `kid`.
8. Für diesen einen Verifikationsvorgang wurde **noch kein** Refresh versucht.

Nur dieser Zustand heißt intern **„refreshable key miss"**.

## 4. Wann kein Refresh zulässig ist

Kein Refresh bei fehlendem, leerem oder falsch typisiertem `kid`; mehreren
passenden Schlüsseln; vorhandenem `kid` mit unbrauchbarem, inkompatiblem oder
mehrdeutigem Schlüssel; nicht allowlistetem, symmetrischem oder
`none`-Algorithmus; `jku`, `x5u`, eingebettetem `jwk` oder anderer
tokenkontrollierter Schlüsselquelle; falscher Signatur; Issuer-, Audience-,
`azp`-, Zeit-, Nonce- oder Subject-Ablehnung; strukturell unbrauchbarem
JWT/JWS; Provider-Error oder fehlendem ID-Token; Token-, JWKS-, Clock-,
Parser- oder Bibliotheksfehler; und bei jeder bereits erfolgten Refresh-Anfrage
desselben Vorgangs.

Diese Fälle bleiben direkt `None` oder `OidcVerificationUnavailable` nach
bestehendem Vertrag. **Nicht bei jedem `None` wird aktualisiert** — das wäre ein
tokengesteuerter Netzwerk-Amplifier.

## 5. Interne Ergebnisgrenze

Der spätere Implementierungsslice darf eine **private** interne Ergebnisform
einführen, die sinngemäß *verified identity*, *definitive rejection* und
*refreshable key miss* unterscheidet.

Verbindlich: **nicht** Teil von `OidcAuthorizationCodeVerifier`, **nicht** aus
`identity/ports.py` exportiert, **keine** öffentliche Domain-Exception, **kein**
öffentliches Modell, **keine** Änderung des `verify_oidc_id_token(...)`-Vertrags
für bestehende Aufrufer, `repr`-frei falls sie sensible oder identitätsbezogene
Daten trägt, und **niemals** serialisiert, geloggt oder an Transportcode
gegeben.

Bevorzugte Richtung: gemeinsame interne Schlüsselwahl- und Verifikationslogik,
wobei die öffentliche Offline-Funktion ein neutraler Wrapper bleibt. **Kein**
zweiter JOSE-Parser mit abweichenden Regeln und **kein** doppelter
Key-Selection-Algorithmus — zwei auseinanderlaufende Auswahlpfade wären selbst
eine Schwachstelle. Die konkrete Python-Signatur entscheidet LQ-168 **nicht**.

## 6. Refresh-Ablauf und Obergrenzen

1. Aktive vertrauenswürdige Konfiguration **genau einmal** lesen.
2. Authorization Code **genau einmal** austauschen.
3. JWKS über den LQ-167-Cache lesen.
4. Offline-Verifikation **einmal** durchführen.
5. **Nur** bei internem `refreshable key miss`: Single-Slot-Eintrag fail-closed
   verwerfen; **exakt einmal** über den LQ-166-Loader von derselben bytegenauen
   `jwks_uri` laden; neuen Slot nur nach vollständigem Erfolg setzen;
   Offline-Verifikation **exakt einmal** mit dem neuen Snapshot wiederholen.
6. Ergebnis nach außen wieder ausschließlich als Erfolg, `None` oder
   `OidcVerificationUnavailable`.

Absolute Obergrenzen **pro Callback**: ein Token-Request; höchstens ein
regulärer JWKS-Load; höchstens ein Refresh; höchstens zwei
Offline-Verifikationen; **keine** dritte Schlüsselabfrage, **keine**
Retry-Schleife, **kein** erneuter Code-Austausch.

## 7. Gleicher Konfigurationssnapshot

Der gesamte Ablauf verwendet exakt denselben zu Beginn gelesenen
`TrustedOidcClientConfiguration`-Snapshot: `issuer`, `client_id`,
`redirect_uri`, `token_endpoint`, `jwks_uri`, `allowed_signing_algorithms` und
`clock_skew`. Zwischen erster Verifikation und Refresh wird die aktive
Konfiguration **nicht erneut gelesen**.

Keine Mischung aus Token-Endpunkt einer Konfiguration, JWKS-URI einer zweiten
und Issuer, Client oder Algorithmen einer dritten. Ändert sich die aktive
Konfiguration parallel, gilt sie erst für einen **neuen** Login-Vorgang.

## 8. Cache-Verhalten beim Refresh

Der kontrollierte Refresh ist **kein** normaler TTL-Hit. Verbindlich: exakt
bytegleiche konfigurierte `jwks_uri`; bestehenden Slot **vor** dem Refresh-Load
verwerfen; bei Lade-, Clock- oder Parserfehler den Cache leer lassen; niemals
stale Schlüssel zurückgeben; **kein** Zurückrollen auf das vorherige Set; der
neue Slot erhält seine TTL erst **nach** erfolgreichem Laden; kein zweiter Slot
und kein Cachewachstum; keine tokengesteuerte Cache-Partition.

Die konkrete spätere Cache-Methode beziehungsweise Signatur bleibt dem
Implementierungsslice vorbehalten. **LQ-168 fügt keine Methode hinzu.**

## 9. Fehlerklassifikation

| Situation | Ergebnis |
|---|---|
| Refresh erfolgreich, zweite Prüfung erfolgreich | `ExternalIdentity` |
| Refresh erfolgreich, `kid` weiterhin unbekannt | `None` |
| Refresh erfolgreich, zweite Prüfung anders belastbar abgelehnt | `None` |
| Refresh technisch unmöglich (Netzwerk, Timeout, Clock, Response, JSON, JWKS-Grundstruktur, interner normaler Fehler) | `Unavailable` |
| Erste Prüfung lehnt aus keinem refreshbaren Grund ab | `None`, **ohne** Netzwerk-Refresh |

Keine Ursache wird nach außen unterschieden.

## 10. Sicherheitsbegründung

Rotation kann ein neues, legitimes `kid` erzeugen, während der TTL-Cache noch
das vorige Set hält; ohne begrenzten Refresh würde ein **legitimer** Login bis
zum TTL-Ablauf fälschlich scheitern. Ein Refresh bei jedem `None` wäre dagegen
ein **angreifergesteuerter Netzwerk-Amplifier**, weil jedes beliebige Token eine
Abfrage auslöste.

Der nicht leere, im vertrauenswürdigen Set fehlende `kid` ist deshalb nur ein
**interner, eng begrenzter Refresh-Hinweis**. Er beweist **keine** Identität und
gewährt **keine** Berechtigung: Ein erfolgreicher Refresh ersetzt ausschließlich
Schlüsselmaterial, die vollständige Signatur- und Claimprüfung nach LQ-155 §7
bleibt zwingend.

## 11. Vertraulichkeit

Niemals in Logs, Telemetrie, Metriklabels oder Fehlerdetails: `kid`, der
Algorithmus aus dem Token, der Tokenheader, das ID-Token, JWKS-Inhalt,
Schlüsselmaterial, Treffer-/Miss-Status, der Refreshgrund sowie URI oder
Konfigurationswerte. Zulässig bleibt **höchstens** eine aggregierte technische
Metrik für die Anzahl kontrollierter Refreshversuche, nicht partitioniert nach
Issuer, URI, `kid`, Algorithmus oder Nutzer — auch sie ist **keine
Anforderung** dieses Slices.

## 12. Bewusst nicht enthalten

Keine Codeänderung, keine interne Ergebnisform, keine Änderung an
`verify_oidc_id_token`, keine Cache-Refresh-Methode, keine Portänderung, kein
Adapter, kein Token- oder JOSE-Parsing, kein Netzwerkaufruf, kein Test-Double,
keine Callback-Route, keine Session-/CSRF-Ausgabe, keine Composition, kein
Production-Wiring, keine neue Dependency, keine CI-, Container-, Deployment-
oder Grype-Änderung, kein Multi-Issuer und kein persistenter Cache.

## 13. Nächster Schritt

Der Implementierungsslice, der die interne Ergebnisform und die gemeinsame
Schlüsselwahl einführt und diesen Ablauf im Adapter umsetzt.
