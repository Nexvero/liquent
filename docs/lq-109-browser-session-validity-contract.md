# LQ-109 — Browser Session Validity Contract

## Entscheidung

Ein späterer Session-Adapter darf einen `ResolvedBrowserSession`-Kontext nur
für einen serverseitig vorhandenen, nicht widerrufenen und noch nicht
abgelaufenen Eintrag liefern. Alle anderen Fälle werden neutral wie eine
unbekannte Session behandelt.

## Verbindliche Regeln

- Die opake Session-ID ist nur ein Suchschlüssel und enthält keine Identität.
- Ablauf und Widerruf werden serverseitig vor der Auflösung geprüft.
- Zeitangaben sind eindeutig und zeitzonenbehaftet; der Ablaufzeitpunkt selbst
  ist bereits ungültig.
- Ein Lookup verlängert eine Session nicht und verändert keinen Zustand.
- Erst nach erfolgreicher Prüfung dürfen Principal und CSRF-Nachweis an die
  Anwendung gegeben werden.
- Unbekannt, abgelaufen, widerrufen und ungültig bleiben nach außen
  ununterscheidbar (`authentication_required`).

## Rotation

Eine spätere Rotation ersetzt sowohl die opake Session-ID als auch den
gebundenen CSRF-Nachweis. Der alte Eintrag muss dabei unbrauchbar werden. Die
Rotation selbst ist nicht Teil dieses Slices.

## Bewusst nicht enthalten

- keine konkrete Lebensdauer oder Idle-Timeout-Zahl,
- kein Session-Speicher oder Adapter,
- keine Erzeugung, Verlängerung, Rotation oder Widerrufsoperation,
- keine Cookie-Ausgabe oder Login-/Logout-Route,
- keine Freigabe von Preview oder Production,
- kein Release und kein Deployment.

## Nächster Schritt

LQ-110 kann auf dieser Grundlage einen kleinen, rein serverseitigen
Session-Eintrag und dessen pure Gültigkeitsprüfung modellieren. Persistenz und
HTTP bleiben weiterhin getrennt.
