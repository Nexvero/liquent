# LQ-091 — Session Principal

## Ergebnis

`SessionPrincipal` ist der minimale unveränderliche Übergabevertrag zwischen
einer späteren Sessionprüfung und den Anwendungsfällen. Er enthält genau ein
Feld:

- die bereits verifizierte `UserId`.

Die Erzeugung eines Principals bedeutet, dass eine äußere Sicherheitsgrenze die
Identität bereits geprüft hat. Der Principal prüft keine Credentials und trägt
keine Sessiondaten.

## Regeln

- Anwendungsfälle erhalten keine rohen Cookies oder Tokens.
- Der Principal enthält weder Workspace noch Rechte; diese werden weiterhin
  serverseitig über die Membership ermittelt.
- Das Objekt ist nach seiner Erzeugung unveränderlich.
- Ohne verifizierte Identität existiert kein Principal.

## Bewusst nicht enthalten

- keine Session-ID, Ablaufzeit oder Widerrufslogik,
- kein Cookie-, CSRF-, Token- oder Provider-Code,
- kein Login, Logout oder Passwortfluss,
- keine HTTP-Middleware und keine Fehlerabbildung,
- keine Speicherung oder Datenbankmigration,
- keine Freischaltung von Preview oder Produktion,
- kein Release oder Deployment.

## Nächster Schritt

LQ-092 kann die bestehende Research-Autorisierungsanwendung so ergänzen, dass
sie einen `SessionPrincipal` statt einer frei übergebenen `UserId` akzeptiert.
Die eigentliche Sessionprüfung bleibt weiterhin außerhalb dieses Slices.
