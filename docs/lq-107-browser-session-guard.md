# LQ-107 — Browser Session Guard

## Status

- Ein kleiner Guard verbindet die opake `SessionId` mit dem bestehenden
  `BrowserSessionLookup`.
- Ein Treffer liefert den bereits aufgelösten `ResolvedBrowserSession`-Kontext.
- Fehlende und unbekannte Session-IDs erzeugen identisch
  `authentication_required`.
- Eine fehlende ID löst keinen unnötigen Lookup aus.

## Sicherheitsgrenze

Der Fehler enthält weder Session-ID noch Grund oder Speicherdetails. Der Guard
vertraut darauf, dass ein konkreter Lookup-Adapter abgelaufene, widerrufene oder
anderweitig ungültige Einträge als fehlenden Treffer behandelt.

## Bewusst nicht enthalten

- kein konkreter Session-Adapter oder Speicher,
- keine Erzeugung, Rotation, Ablauf- oder Widerrufsimplementierung,
- kein Cookie-Name und keine Cookie-Auswertung,
- keine HTTP-Fehlerabbildung oder Middleware,
- keine Freigabe von Preview oder Production,
- kein Release und kein Deployment.

